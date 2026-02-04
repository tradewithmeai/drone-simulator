#!/usr/bin/env python3
"""Tests for the 6-DOF quadrotor physics engine and flight controller.

Covers: quaternion math, free fall, hover, motor thrust, step response,
multi-drone formation tracking, and ground constraint.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from simulation.physics import (
    QuadrotorPhysics, PhysicsConfig,
    quat_to_euler, euler_to_quat, quat_to_rotation_matrix, quat_multiply,
)
from simulation.flight_controller import FlightController, FlightControllerConfig
from simulation.drone import Drone

PASS = 0
FAIL = 0


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        msg = f"  [FAIL] {name}"
        if detail:
            msg += f" — {detail}"
        print(msg)


# ── Quaternion utilities ────────────────────────────────────────

def test_quaternion_euler_roundtrip():
    """euler_to_quat and quat_to_euler should be inverses."""
    print("\n=== Quaternion <-> Euler Roundtrip ===")
    cases = [
        (0.0, 0.0, 0.0),
        (0.3, 0.0, 0.0),      # pure roll
        (0.0, 0.25, 0.0),     # pure pitch
        (0.0, 0.0, 0.5),      # pure yaw
        (0.1, 0.2, 0.3),      # combined
        (-0.15, 0.1, -0.4),   # negative angles
    ]
    for r, p, y in cases:
        q = euler_to_quat(r, p, y)
        e = quat_to_euler(q)
        check(
            f"roundtrip ({r:.2f},{p:.2f},{y:.2f})",
            np.allclose([r, p, y], e, atol=1e-6),
            f"got ({e[0]:.4f},{e[1]:.4f},{e[2]:.4f})",
        )


def test_quaternion_axis_mapping():
    """Verify each Euler angle maps to the correct rotation axis."""
    print("\n=== Quaternion Axis Mapping ===")
    angle = 0.2

    # Roll = Z-axis rotation
    q = euler_to_quat(angle, 0, 0)
    expected_z = np.array([np.cos(angle / 2), 0, 0, np.sin(angle / 2)])
    check("roll ->Z-axis quat", np.allclose(q, expected_z, atol=1e-10))

    # Pitch = X-axis rotation
    q = euler_to_quat(0, angle, 0)
    expected_x = np.array([np.cos(angle / 2), np.sin(angle / 2), 0, 0])
    check("pitch ->X-axis quat", np.allclose(q, expected_x, atol=1e-10))

    # Yaw = Y-axis rotation
    q = euler_to_quat(0, 0, angle)
    expected_y = np.array([np.cos(angle / 2), 0, np.sin(angle / 2), 0])
    check("yaw ->Y-axis quat", np.allclose(q, expected_y, atol=1e-10))


def test_thrust_direction():
    """Positive roll tilts thrust in -X, positive pitch tilts in +Z."""
    print("\n=== Thrust Direction from Tilt ===")
    up = np.array([0.0, 1.0, 0.0])

    q_roll = euler_to_quat(0.2, 0, 0)
    R = quat_to_rotation_matrix(q_roll)
    t = R @ up
    check("+roll ->-X thrust", t[0] < -0.1, f"X={t[0]:.3f}")
    check("+roll ->~0 Z thrust", abs(t[2]) < 0.01, f"Z={t[2]:.3f}")

    q_pitch = euler_to_quat(0, 0.2, 0)
    R = quat_to_rotation_matrix(q_pitch)
    t = R @ up
    check("+pitch ->+Z thrust", t[2] > 0.1, f"Z={t[2]:.3f}")
    check("+pitch ->~0 X thrust", abs(t[0]) < 0.01, f"X={t[0]:.3f}")


def test_identity_quaternion():
    """Identity quaternion should give zero Euler angles."""
    print("\n=== Identity Quaternion ===")
    e = quat_to_euler(np.array([1.0, 0.0, 0.0, 0.0]))
    check("identity ->zero angles", np.allclose(e, 0, atol=1e-10))


# ── Physics engine ──────────────────────────────────────────────

def test_free_fall():
    """Object with no thrust should fall under gravity."""
    print("\n=== Free Fall ===")
    physics = QuadrotorPhysics(PhysicsConfig())
    physics.position = np.array([0.0, 50.0, 0.0])

    dt = 1 / 60
    for _ in range(120):  # 2 seconds
        physics.update(dt)

    # After 2s of free fall: y = 50 - 0.5*9.81*4 ~= 30.38 (with drag)
    check("altitude decreased", physics.position[1] < 40.0, f"y={physics.position[1]:.2f}")
    check("falling downward", physics.velocity[1] < -10.0, f"vy={physics.velocity[1]:.2f}")
    check("no horizontal movement", abs(physics.position[0]) < 0.01)
    check("no horizontal movement Z", abs(physics.position[2]) < 0.01)


def test_ground_constraint():
    """Drone should not fall below Y=0."""
    print("\n=== Ground Constraint ===")
    physics = QuadrotorPhysics(PhysicsConfig())
    physics.position = np.array([0.0, 1.0, 0.0])

    dt = 1 / 60
    for _ in range(600):  # 10 seconds — plenty to hit ground
        physics.update(dt)

    check("position Y >= 0", physics.position[1] >= 0.0, f"y={physics.position[1]:.4f}")
    check("velocity Y >= 0", physics.velocity[1] >= 0.0, f"vy={physics.velocity[1]:.4f}")


def test_hover_rpm():
    """hover_rpm() should produce enough thrust for weight."""
    print("\n=== Hover RPM Calculation ===")
    config = PhysicsConfig()
    physics = QuadrotorPhysics(config)
    rpm = physics.hover_rpm()

    thrust_per_motor = config.motor_thrust_coeff * rpm ** 2
    total_thrust = 4 * thrust_per_motor
    weight = config.mass * config.gravity

    check(
        "4 motors at hover_rpm balance weight",
        abs(total_thrust - weight) < 0.01,
        f"thrust={total_thrust:.3f}N, weight={weight:.3f}N",
    )
    check("hover RPM reasonable", 3000 < rpm < 6000, f"rpm={rpm:.0f}")


def test_motor_dynamics():
    """Motor RPMs should lag behind targets via first-order filter."""
    print("\n=== Motor Dynamics ===")
    physics = QuadrotorPhysics(PhysicsConfig())
    physics.set_motor_rpms(np.array([5000, 5000, 5000, 5000]))

    # After one tick, actual RPMs should be partway toward target
    physics.update(1 / 60)
    check(
        "RPMs move toward target",
        np.all(physics.motor_rpms > 0) and np.all(physics.motor_rpms < 5000),
        f"rpms={physics.motor_rpms.mean():.0f}",
    )

    # After many ticks, should converge
    for _ in range(200):
        physics.update(1 / 60)
    check(
        "RPMs converge to target",
        np.allclose(physics.motor_rpms, 5000, atol=1.0),
        f"rpms={physics.motor_rpms.mean():.1f}",
    )


def test_nan_protection():
    """Physics should recover from NaN state."""
    print("\n=== NaN Protection ===")
    physics = QuadrotorPhysics(PhysicsConfig())
    physics.position = np.array([0.0, 10.0, 0.0])
    physics.velocity = np.array([float('nan'), 0.0, 0.0])

    # First update detects NaN and resets state
    physics.update(1 / 60)
    check("velocity reset from NaN", not np.any(np.isnan(physics.velocity)))
    # After reset, a second update should produce clean state
    physics.update(1 / 60)
    check("position clean after recovery", not np.any(np.isnan(physics.position)))


# ── Flight controller ───────────────────────────────────────────

def test_hover_stability():
    """Drone should maintain altitude when commanded to hover."""
    print("\n=== Hover Stability ===")
    physics = QuadrotorPhysics(PhysicsConfig())
    physics.position = np.array([0.0, 10.0, 0.0])
    ctrl = FlightController(physics, FlightControllerConfig())
    ctrl.arm()
    ctrl.set_position(np.array([0.0, 10.0, 0.0]))

    dt = 1 / 60
    for _ in range(600):  # 10 seconds
        rpms = ctrl.update(dt)
        physics.set_motor_rpms(rpms)
        physics.update(dt)

    alt_error = abs(physics.position[1] - 10.0)
    speed = np.linalg.norm(physics.velocity)
    check("altitude error < 0.01m", alt_error < 0.01, f"error={alt_error:.4f}m")
    check("speed < 0.01 m/s", speed < 0.01, f"speed={speed:.4f}")
    check("no horizontal drift", abs(physics.position[0]) < 0.01)
    check("no horizontal drift Z", abs(physics.position[2]) < 0.01)


def test_position_step_response():
    """Drone should converge to a new position target."""
    print("\n=== Position Step Response ===")
    physics = QuadrotorPhysics(PhysicsConfig())
    physics.position = np.array([0.0, 10.0, 0.0])
    ctrl = FlightController(physics, FlightControllerConfig())
    ctrl.arm()
    ctrl.set_position(np.array([0.0, 10.0, 0.0]))

    dt = 1 / 60
    # Settle first
    for _ in range(120):
        rpms = ctrl.update(dt)
        physics.set_motor_rpms(rpms)
        physics.update(dt)

    # Step to new position
    target = np.array([5.0, 15.0, 3.0])
    ctrl.set_position(target)

    for _ in range(900):  # 15 seconds
        rpms = ctrl.update(dt)
        physics.set_motor_rpms(rpms)
        physics.update(dt)

    error = np.linalg.norm(physics.position - target)
    speed = np.linalg.norm(physics.velocity)
    check("position error < 0.2m", error < 0.2, f"error={error:.3f}m")
    check("speed < 0.1 m/s", speed < 0.1, f"speed={speed:.4f}")
    check("moved in +X direction", physics.position[0] > 4.0, f"x={physics.position[0]:.2f}")
    check("moved in +Z direction", physics.position[2] > 2.0, f"z={physics.position[2]:.2f}")
    check("climbed in +Y", physics.position[1] > 14.0, f"y={physics.position[1]:.2f}")


def test_no_flip():
    """Tilt angles should stay within reasonable bounds during flight."""
    print("\n=== No Flip During Manoeuvre ===")
    physics = QuadrotorPhysics(PhysicsConfig())
    physics.position = np.array([0.0, 10.0, 0.0])
    ctrl = FlightController(physics, FlightControllerConfig())
    ctrl.arm()
    ctrl.set_position(np.array([0.0, 10.0, 0.0]))

    dt = 1 / 60
    for _ in range(60):
        rpms = ctrl.update(dt)
        physics.set_motor_rpms(rpms)
        physics.update(dt)

    # Large step
    ctrl.set_position(np.array([10.0, 20.0, 10.0]))
    max_tilt = 0.0
    for _ in range(600):
        rpms = ctrl.update(dt)
        physics.set_motor_rpms(rpms)
        physics.update(dt)
        euler = quat_to_euler(physics.orientation)
        tilt = max(abs(euler[0]), abs(euler[1]))  # roll, pitch
        max_tilt = max(max_tilt, tilt)

    check(
        "max tilt < 45 degrees",
        max_tilt < np.radians(45),
        f"max_tilt={np.degrees(max_tilt):.1f}deg",
    )


def test_takeoff_and_land():
    """Takeoff and landing modes should work."""
    print("\n=== Takeoff and Landing ===")
    physics = QuadrotorPhysics(PhysicsConfig())
    physics.position = np.array([0.0, 0.0, 0.0])
    ctrl = FlightController(physics, FlightControllerConfig())
    ctrl.arm()
    ctrl.takeoff(10.0)

    dt = 1 / 60
    for _ in range(600):  # 10 seconds
        rpms = ctrl.update(dt)
        physics.set_motor_rpms(rpms)
        physics.update(dt)

    check("reached altitude", physics.position[1] > 8.0, f"y={physics.position[1]:.2f}")
    check("mode is TAKEOFF or POSITION", ctrl.mode in ("TAKEOFF", "POSITION"))

    ctrl.land()
    for _ in range(1200):  # 20 seconds to land
        rpms = ctrl.update(dt)
        physics.set_motor_rpms(rpms)
        physics.update(dt)
        if ctrl.mode == "IDLE":
            break

    check("landed (mode IDLE)", ctrl.mode == "IDLE")
    check("near ground", physics.position[1] < 0.2, f"y={physics.position[1]:.2f}")


# ── Drone integration ───────────────────────────────────────────

def test_multi_drone_formation():
    """Multiple drones should converge to formation targets."""
    print("\n=== Multi-Drone Formation ===")
    drones = []
    for i in range(6):
        d = Drone(i, np.array([i * 3.0, 5.0, 0.0]), [1, 0, 0])
        drones.append(d)

    dt = 1 / 60
    # Settle
    for _ in range(120):
        for d in drones:
            d.update(dt)

    # Circle formation
    radius = 5.0
    for i, d in enumerate(drones):
        angle = 2 * np.pi * i / len(drones)
        target = np.array([radius * np.cos(angle), 10.0, radius * np.sin(angle)])
        d.set_target(target)

    for _ in range(900):  # 15 seconds
        for d in drones:
            d.update(dt)

    errors = [np.linalg.norm(d.physics.position - d.target_position) for d in drones]
    max_error = max(errors)
    close_enough = sum(1 for e in errors if e < 0.5)
    check("all drones within 0.5m", close_enough == 6, f"close={close_enough}/6, max_err={max_error:.3f}m")
    check("max error < 0.5m", max_error < 0.5, f"max_error={max_error:.3f}m")


def test_drone_get_state():
    """get_state() should return all expected keys."""
    print("\n=== Drone get_state() ===")
    d = Drone(0, np.array([0.0, 5.0, 0.0]), [1, 0, 0])
    d.update(1 / 60)
    state = d.get_state()

    required_keys = [
        'id', 'position', 'velocity', 'target', 'color', 'battery',
        'settled', 'orientation', 'angular_velocity', 'motor_rpms',
        'armed', 'mode', 'crashed',
    ]
    for key in required_keys:
        check(f"state has '{key}'", key in state)

    check("position is list of 3", len(state['position']) == 3)
    check("motor_rpms is list of 4", len(state['motor_rpms']) == 4)


def test_battery_drain():
    """Battery should decrease over time when flying."""
    print("\n=== Battery Drain ===")
    d = Drone(0, np.array([0.0, 10.0, 0.0]), [1, 0, 0])
    initial = d.battery_level

    dt = 1 / 60
    for _ in range(6000):  # 100 seconds
        d.update(dt)

    check("battery decreased", d.battery_level < initial, f"{d.battery_level:.2f}%")
    check("battery still positive", d.battery_level > 0)


# ── Run all tests ───────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Physics & Flight Controller Test Suite")
    print("=" * 60)

    test_quaternion_euler_roundtrip()
    test_quaternion_axis_mapping()
    test_thrust_direction()
    test_identity_quaternion()
    test_free_fall()
    test_ground_constraint()
    test_hover_rpm()
    test_motor_dynamics()
    test_nan_protection()
    test_hover_stability()
    test_position_step_response()
    test_no_flip()
    test_takeoff_and_land()
    test_multi_drone_formation()
    test_drone_get_state()
    test_battery_drain()

    print("\n" + "=" * 60)
    print(f"  Results: {PASS} passed, {FAIL} failed")
    print("=" * 60)
    return FAIL == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
