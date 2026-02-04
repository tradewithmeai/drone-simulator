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
        """Read IMU with realistic noise (body-frame specific force + gyro)."""
        return self._drone.sensors.get_imu(self._drone.physics, time.time())

    def get_gps(self) -> GPSReading:
        """Read GPS with rate limiting and position/velocity noise."""
        return self._drone.sensors.get_gps(self._drone.physics, time.time())

    def get_altitude(self) -> AltitudeReading:
        """Read altitude from barometer, rangefinder, and GPS."""
        return self._drone.sensors.get_altitude(self._drone.physics, time.time())

    def get_battery(self) -> BatteryReading:
        """Read battery with ADC noise."""
        pct = self._drone.battery_level
        voltage = 3.3 + (pct / 100.0) * 0.9
        power = self._drone.physics.get_power_draw()
        current = power / max(voltage, 0.1)
        return self._drone.sensors.get_battery(pct, voltage, current, time.time())

    def get_ground_truth(self) -> dict:
        """Get perfect ground truth state for debugging and analysis.

        Returns physics engine state with no noise applied.
        """
        physics = self._drone.physics
        return {
            'position': physics.position.copy(),
            'velocity': physics.velocity.copy(),
            'acceleration': physics.acceleration.copy(),
            'orientation': physics.orientation.copy(),
            'angular_velocity': physics.angular_velocity.copy(),
            'euler_angles': physics.get_euler_angles().copy(),
            'motor_rpms': physics.motor_rpms.copy(),
            'battery_level': self._drone.battery_level,
            'crashed': self._drone.crashed,
        }

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
