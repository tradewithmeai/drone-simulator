#!/usr/bin/env python3
"""Tests for the sensor noise simulation system.

Covers: perfect mode, IMU body-frame transform, GPS rate limiting,
GPS noise characteristics, barometer drift, rangefinder range limit,
battery noise, deterministic seeding, and HAL integration.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import numpy as np
from simulation.physics import QuadrotorPhysics, PhysicsConfig
from simulation.sensors import SensorSuite, SensorConfig
from simulation.drone import Drone
from simulation.simulator import Simulator

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


def make_hovering_physics(altitude=10.0):
    """Create a physics object settled at a given altitude."""
    physics = QuadrotorPhysics(PhysicsConfig())
    physics.position = np.array([5.0, altitude, -3.0])
    physics.velocity = np.array([0.5, -0.1, 0.3])
    # Run one tick to populate acceleration and rotation_matrix
    physics.set_motor_rpms(np.full(4, physics.hover_rpm()))
    physics.update(1 / 60)
    return physics


# ── Perfect mode ────────────────────────────────────────────────

def test_perfect_mode_gps():
    """GPS should return exact ground truth in perfect mode."""
    print("\n=== Perfect Mode: GPS ===")
    physics = make_hovering_physics()
    suite = SensorSuite(SensorConfig(perfect_mode=True), seed=0)

    for i in range(10):
        gps = suite.get_gps(physics, 1.0 + i * 0.01)
        check(
            f"GPS pos matches truth (read {i})",
            np.allclose(gps.position, physics.position),
        )
        check(
            f"GPS vel matches truth (read {i})",
            np.allclose(gps.velocity, physics.velocity),
        )


def test_perfect_mode_altitude():
    """All altitude readings should match truth in perfect mode."""
    print("\n=== Perfect Mode: Altitude ===")
    physics = make_hovering_physics(15.0)
    suite = SensorSuite(SensorConfig(perfect_mode=True), seed=0)

    alt = suite.get_altitude(physics, 1.0)
    true_alt = physics.position[1]
    check("baro matches truth", abs(alt.altitude_baro - true_alt) < 1e-6)
    check("AGL matches truth", abs(alt.altitude_agl - true_alt) < 1e-6)
    check("GPS alt matches truth", abs(alt.altitude_gps - true_alt) < 1e-6)


def test_perfect_mode_battery():
    """Battery should return exact values in perfect mode."""
    print("\n=== Perfect Mode: Battery ===")
    suite = SensorSuite(SensorConfig(perfect_mode=True), seed=0)

    bat = suite.get_battery(75.0, 3.9, 5.5, 1.0)
    check("voltage exact", bat.voltage == 3.9)
    check("current exact", bat.current == 5.5)
    check("remaining exact", bat.remaining_pct == 75.0)


# ── IMU ─────────────────────────────────────────────────────────

def test_imu_body_frame():
    """IMU accel should be in body frame (gravity along body Y when level)."""
    print("\n=== IMU Body Frame Transform ===")
    physics = QuadrotorPhysics(PhysicsConfig())
    physics.position = np.array([0.0, 10.0, 0.0])
    # Settle at hover RPM so motor lag resolves and forces stabilise
    hover_rpm = physics.hover_rpm()
    for _ in range(120):
        physics.set_motor_rpms(np.full(4, hover_rpm))
        physics.update(1 / 60)

    suite = SensorSuite(SensorConfig(perfect_mode=True), seed=0)
    imu = suite.get_imu(physics, 1.0)

    # Specific force when hovering should be approximately [0, +g, 0] in body frame
    check(
        "body accel Y ~= +9.81",
        abs(imu.accel[1] - 9.81) < 1.0,
        f"accel_y={imu.accel[1]:.2f}",
    )
    check(
        "body accel X ~= 0",
        abs(imu.accel[0]) < 1.0,
        f"accel_x={imu.accel[0]:.2f}",
    )
    check(
        "body accel Z ~= 0",
        abs(imu.accel[2]) < 1.0,
        f"accel_z={imu.accel[2]:.2f}",
    )


def test_imu_noise():
    """IMU should have measurable noise when not in perfect mode."""
    print("\n=== IMU Noise ===")
    physics = make_hovering_physics()
    config = SensorConfig(perfect_mode=False, accel_noise_std=0.05, gyro_noise_std=0.01)
    suite = SensorSuite(config, seed=42)

    accels = []
    gyros = []
    for i in range(500):
        imu = suite.get_imu(physics, 1.0 + i * (1 / 60))
        accels.append(imu.accel.copy())
        gyros.append(imu.gyro.copy())

    accel_std = np.std(np.array(accels), axis=0)
    gyro_std = np.std(np.array(gyros), axis=0)

    check(
        "accel noise std ~= 0.05",
        np.all(accel_std > 0.02) and np.all(accel_std < 0.15),
        f"std={accel_std}",
    )
    check(
        "gyro noise std ~= 0.01",
        np.all(gyro_std > 0.005) and np.all(gyro_std < 0.05),
        f"std={gyro_std}",
    )


def test_imu_bias_drift():
    """IMU bias should accumulate over time."""
    print("\n=== IMU Bias Drift ===")
    config = SensorConfig(
        perfect_mode=False,
        accel_bias_drift=0.01,
        accel_bias_max=1.0,
        gyro_bias_drift=0.005,
        gyro_bias_max=0.5,
    )
    suite = SensorSuite(config, seed=0)
    physics = make_hovering_physics()

    for i in range(6000):  # 100 seconds at 60Hz
        suite.get_imu(physics, i / 60)

    accel_bias = np.abs(suite._accel_bias)
    gyro_bias = np.abs(suite._gyro_bias)

    check("accel bias accumulated", np.any(accel_bias > 0.1), f"bias={suite._accel_bias}")
    check("gyro bias accumulated", np.any(gyro_bias > 0.05), f"bias={suite._gyro_bias}")
    check(
        "accel bias within max",
        np.all(accel_bias <= config.accel_bias_max),
    )
    check(
        "gyro bias within max",
        np.all(gyro_bias <= config.gyro_bias_max),
    )


# ── GPS ─────────────────────────────────────────────────────────

def test_gps_rate_limiting():
    """GPS should update at the configured rate, not every tick."""
    print("\n=== GPS Rate Limiting ===")
    config = SensorConfig(perfect_mode=False, gps_update_rate=5.0)
    suite = SensorSuite(config, seed=7)
    physics = make_hovering_physics()

    timestamps = set()
    for i in range(120):  # 2 seconds at 60Hz
        t = 10.0 + i * (1 / 60)
        gps = suite.get_gps(physics, t)
        timestamps.add(gps.timestamp)

    check(
        "~10 unique timestamps at 5Hz over 2s",
        8 <= len(timestamps) <= 12,
        f"got {len(timestamps)}",
    )


def test_gps_stale_readings():
    """Between updates, GPS should return the same cached position."""
    print("\n=== GPS Stale Readings ===")
    config = SensorConfig(perfect_mode=False, gps_update_rate=1.0)  # 1Hz
    suite = SensorSuite(config, seed=0)
    physics = make_hovering_physics()

    # First reading at t=0
    gps0 = suite.get_gps(physics, 0.0)
    pos0 = gps0.position.copy()

    # Readings at t=0.1 through t=0.9 should be identical (cached)
    for i in range(1, 10):
        gps = suite.get_gps(physics, i * 0.1)
        check(
            f"stale at t={i*0.1:.1f}s",
            np.array_equal(gps.position, pos0),
        )

    # Reading at t=1.0 should be a new measurement
    gps1 = suite.get_gps(physics, 1.0)
    check(
        "new reading at t=1.0s",
        gps1.timestamp == 1.0,
        f"timestamp={gps1.timestamp}",
    )


def test_gps_noise_magnitude():
    """GPS position noise should approximately match configured std dev."""
    print("\n=== GPS Noise Magnitude ===")
    config = SensorConfig(
        perfect_mode=False,
        gps_update_rate=100.0,  # high rate so every read is fresh
        gps_pos_noise_h=2.0,
        gps_pos_noise_v=4.0,
    )
    suite = SensorSuite(config, seed=42)
    physics = make_hovering_physics()

    positions = []
    for i in range(500):
        gps = suite.get_gps(physics, i * 0.01)
        positions.append(gps.position.copy())

    arr = np.array(positions)
    std_x = np.std(arr[:, 0])
    std_y = np.std(arr[:, 1])
    std_z = np.std(arr[:, 2])

    check("X noise std ~= 2.0", 1.0 < std_x < 3.5, f"std_x={std_x:.2f}")
    check("Y noise std ~= 4.0", 2.0 < std_y < 6.5, f"std_y={std_y:.2f}")
    check("Z noise std ~= 2.0", 1.0 < std_z < 3.5, f"std_z={std_z:.2f}")


# ── Barometer ───────────────────────────────────────────────────

def test_baro_noise_and_drift():
    """Barometer should have noise and slow bias drift."""
    print("\n=== Barometer Noise and Drift ===")
    config = SensorConfig(
        perfect_mode=False,
        baro_noise_std=0.5,
        baro_bias_drift=0.005,
        baro_bias_max=3.0,
    )
    suite = SensorSuite(config, seed=0)
    physics = make_hovering_physics(20.0)

    readings = []
    for i in range(1000):
        alt = suite.get_altitude(physics, i / 60)
        readings.append(alt.altitude_baro)

    arr = np.array(readings)
    noise_std = np.std(arr)
    mean_error = abs(np.mean(arr) - physics.position[1])

    check("baro has noise", noise_std > 0.2, f"std={noise_std:.3f}")
    check("bias drifts from truth", suite._baro_bias != 0.0, f"bias={suite._baro_bias:.4f}")
    check("bias within max", abs(suite._baro_bias) <= config.baro_bias_max)


# ── Rangefinder ─────────────────────────────────────────────────

def test_rangefinder_range_limit():
    """Rangefinder should return -1 beyond max range."""
    print("\n=== Rangefinder Range Limit ===")
    config = SensorConfig(perfect_mode=False, rangefinder_max_range=20.0)
    suite = SensorSuite(config, seed=0)

    # Within range
    physics_low = make_hovering_physics(15.0)
    alt = suite.get_altitude(physics_low, 1.0)
    check("within range: AGL > 0", alt.altitude_agl > 0, f"agl={alt.altitude_agl:.2f}")
    check(
        "within range: AGL ~= 15m",
        abs(alt.altitude_agl - 15.0) < 2.0,
        f"agl={alt.altitude_agl:.2f}",
    )

    # Beyond range
    physics_high = make_hovering_physics(25.0)
    alt = suite.get_altitude(physics_high, 2.0)
    check("beyond range: AGL == -1", alt.altitude_agl == -1.0, f"agl={alt.altitude_agl}")


# ── Battery ─────────────────────────────────────────────────────

def test_battery_noise():
    """Battery voltage and current should have small noise."""
    print("\n=== Battery Noise ===")
    config = SensorConfig(
        perfect_mode=False,
        battery_voltage_noise_std=0.02,
        battery_current_noise_std=0.1,
    )
    suite = SensorSuite(config, seed=42)

    voltages = []
    currents = []
    for i in range(200):
        bat = suite.get_battery(80.0, 4.0, 3.0, i * 0.01)
        voltages.append(bat.voltage)
        currents.append(bat.current)

    v_std = np.std(voltages)
    c_std = np.std(currents)

    check("voltage noise ~= 0.02V", 0.01 < v_std < 0.05, f"std={v_std:.4f}")
    check("current noise ~= 0.1A", 0.05 < c_std < 0.2, f"std={c_std:.4f}")
    check("current always >= 0", all(c >= 0 for c in currents))


# ── Deterministic seeding ───────────────────────────────────────

def test_deterministic_seeding():
    """Same seed should produce identical noise sequences."""
    print("\n=== Deterministic Seeding ===")
    physics = make_hovering_physics()
    config = SensorConfig(perfect_mode=False)

    suite1 = SensorSuite(config, seed=123)
    suite2 = SensorSuite(config, seed=123)

    readings1 = []
    readings2 = []
    for i in range(50):
        t = i / 60
        readings1.append(suite1.get_imu(physics, t).accel.copy())
        readings2.append(suite2.get_imu(physics, t).accel.copy())

    check(
        "same seed ->identical IMU",
        all(np.array_equal(a, b) for a, b in zip(readings1, readings2)),
    )

    # Different seeds should differ
    suite3 = SensorSuite(config, seed=456)
    readings3 = []
    for i in range(50):
        readings3.append(suite3.get_imu(physics, i / 60).accel.copy())

    check(
        "different seed ->different IMU",
        not all(np.array_equal(a, b) for a, b in zip(readings1, readings3)),
    )


def test_per_drone_independence():
    """Different drones should have independent noise."""
    print("\n=== Per-Drone Independence ===")
    d0 = Drone(0, np.array([0.0, 10.0, 0.0]), [1, 0, 0])
    d1 = Drone(1, np.array([5.0, 10.0, 0.0]), [0, 1, 0])

    d0.update(1 / 60)
    d1.update(1 / 60)

    imu0 = d0.sensors.get_imu(d0.physics, 1.0)
    imu1 = d1.sensors.get_imu(d1.physics, 1.0)

    check(
        "drone 0 and 1 have different IMU noise",
        not np.array_equal(imu0.accel, imu1.accel),
    )


# ── HAL integration ─────────────────────────────────────────────

def test_hal_integration():
    """Sensor reads through HAL should work end-to-end."""
    print("\n=== HAL Integration ===")
    sim = Simulator("config.yaml")
    sim.start()
    time.sleep(2)

    hal = sim.get_hal(0)
    gt = hal.get_ground_truth()

    imu = hal.get_imu()
    gps = hal.get_gps()
    alt = hal.get_altitude()
    bat = hal.get_battery()
    status = hal.get_status()

    check("IMU returns 3D accel", len(imu.accel) == 3)
    check("IMU returns 3D gyro", len(imu.gyro) == 3)
    check("GPS returns 3D position", len(gps.position) == 3)
    check("GPS has accuracy fields", gps.accuracy_h > 0)
    check("altitude has all fields", alt.altitude_baro != 0)
    check("battery has voltage", bat.voltage > 0)
    check("status has mode", len(status.mode) > 0)

    check("ground truth has position", 'position' in gt)
    check("ground truth has velocity", 'velocity' in gt)
    check("ground truth has euler_angles", 'euler_angles' in gt)

    # Ground truth should differ from noisy GPS (unless perfect mode)
    if not sim.sensor_config.perfect_mode:
        gps_error = np.linalg.norm(gps.position - gt['position'])
        check("GPS != ground truth", gps_error > 0.01, f"error={gps_error:.3f}m")

    sim.stop()


# ── Run all tests ───────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Sensor Noise Simulation Test Suite")
    print("=" * 60)

    test_perfect_mode_gps()
    test_perfect_mode_altitude()
    test_perfect_mode_battery()
    test_imu_body_frame()
    test_imu_noise()
    test_imu_bias_drift()
    test_gps_rate_limiting()
    test_gps_stale_readings()
    test_gps_noise_magnitude()
    test_baro_noise_and_drift()
    test_rangefinder_range_limit()
    test_battery_noise()
    test_deterministic_seeding()
    test_per_drone_independence()
    test_hal_integration()

    print("\n" + "=" * 60)
    print(f"  Results: {PASS} passed, {FAIL} failed")
    print("=" * 60)
    return FAIL == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
