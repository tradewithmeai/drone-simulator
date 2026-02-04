"""Simulator implementation of the DroneHAL interface.

Wraps the simulation Drone class to provide the standard HAL interface.
Reads from the physics engine state and routes commands through the
flight controller.
"""

import time
import numpy as np
from hal.drone_hal import DroneHAL
from hal.types import IMUReading, GPSReading, AltitudeReading, BatteryReading, DroneStatus


class SimHAL(DroneHAL):
    """HAL implementation backed by the simulator's Drone object.

    Sensor reads come from the physics engine (perfect in Phase 1,
    noise will be added in Phase 2). Actuator commands route through
    the flight controller.
    """

    def __init__(self, drone):
        """Wrap a simulation Drone object.

        Args:
            drone: A simulation.drone.Drone instance.
        """
        self._drone = drone

    # ── Sensor reads ─────────────────────────────────────────────

    def get_imu(self) -> IMUReading:
        """Read IMU from physics engine.

        Accelerometer: linear acceleration + gravity in body frame.
        Gyroscope: angular velocity in body frame.
        """
        now = time.time()
        physics = self._drone.physics

        # True acceleration in world frame, convert to body frame
        R = physics.rotation_matrix
        # IMU measures specific force (acceleration - gravity) in body frame
        # But for simplicity, return world-frame acceleration for now
        accel = physics.acceleration.copy()

        # Angular velocity is already in body frame
        gyro = physics.angular_velocity.copy()

        return IMUReading(
            timestamp=now,
            accel=accel,
            gyro=gyro,
        )

    def get_gps(self) -> GPSReading:
        """Return position and velocity (perfect GPS, no noise yet)."""
        now = time.time()
        physics = self._drone.physics
        return GPSReading(
            timestamp=now,
            position=physics.position.copy(),
            velocity=physics.velocity.copy(),
            accuracy_h=0.0,
            accuracy_v=0.0,
            fix_type=3,
        )

    def get_altitude(self) -> AltitudeReading:
        """Return altitude from physics position (Y-up)."""
        now = time.time()
        alt = float(self._drone.physics.position[1])
        return AltitudeReading(
            timestamp=now,
            altitude_baro=alt,
            altitude_agl=alt,
            altitude_gps=alt,
        )

    def get_battery(self) -> BatteryReading:
        """Map battery level to BatteryReading."""
        now = time.time()
        pct = self._drone.battery_level
        voltage = 3.3 + (pct / 100.0) * 0.9
        # Estimate current from motor power
        power = self._drone.physics.get_power_draw()
        current = power / max(voltage, 0.1)
        return BatteryReading(
            timestamp=now,
            voltage=voltage,
            current=current,
            remaining_pct=pct,
        )

    def get_status(self) -> DroneStatus:
        """Return status from flight controller."""
        now = time.time()
        ctrl = self._drone.controller
        error_flags = 0
        if self._drone.battery_level <= 5.0:
            error_flags |= 2
        if self._drone.crashed:
            error_flags |= 8

        return DroneStatus(
            timestamp=now,
            armed=ctrl.armed,
            mode=ctrl.mode,
            airborne=self._drone.physics.position[1] > 0.1,
            error_flags=error_flags,
        )

    # ── Actuator commands ────────────────────────────────────────

    def set_position(self, x: float, y: float, z: float, yaw: float = 0.0):
        """Command position through the flight controller."""
        self._drone.set_target(np.array([x, y, z], dtype=float))

    def set_velocity(self, vx: float, vy: float, vz: float, yaw_rate: float = 0.0):
        """Command velocity through the flight controller."""
        self._drone.controller.set_velocity(
            np.array([vx, vy, vz], dtype=float), yaw_rate
        )

    def set_attitude(self, roll: float, pitch: float, yaw_rate: float, thrust: float):
        """Command attitude directly through the flight controller."""
        self._drone.controller.set_attitude(roll, pitch, yaw_rate, thrust)

    # ── Lifecycle commands ───────────────────────────────────────

    def arm(self) -> bool:
        """Arm through the flight controller."""
        self._drone.controller.arm()
        return True

    def disarm(self) -> bool:
        """Disarm through the flight controller."""
        self._drone.controller.disarm()
        return True

    def takeoff(self, altitude: float) -> bool:
        """Takeoff through the flight controller."""
        if not self._drone.controller.armed:
            return False
        self._drone.controller.takeoff(altitude)
        return True

    def land(self) -> bool:
        """Land through the flight controller."""
        self._drone.controller.land()
        return True

    # ── Identity ─────────────────────────────────────────────────

    @property
    def drone_id(self) -> int:
        return self._drone.id
