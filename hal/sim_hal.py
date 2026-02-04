"""Simulator implementation of the DroneHAL interface.

Wraps the simulation Drone class to provide the standard HAL interface.
Currently maps to the kinematic drone model; will be updated as
physics fidelity increases in later phases.
"""

import time
import numpy as np
from hal.drone_hal import DroneHAL
from hal.types import IMUReading, GPSReading, AltitudeReading, BatteryReading, DroneStatus


class SimHAL(DroneHAL):
    """HAL implementation backed by the simulator's Drone object.

    Phase 0: Maps HAL calls to the existing kinematic drone model.
    - get_gps() returns true position (no noise yet)
    - get_imu() returns acceleration derived from velocity changes
    - set_position() maps to set_target()
    - set_velocity() and set_attitude() are stubs until Phase 1 physics

    Future phases will add noise, latency, and realistic sensor models
    behind this same interface.
    """

    def __init__(self, drone):
        """Wrap a simulation Drone object.

        Args:
            drone: A simulation.drone.Drone instance.
        """
        self._drone = drone
        self._prev_velocity = np.zeros(3)
        self._armed = False
        self._airborne = False
        self._mode = "IDLE"

    # ── Sensor reads ─────────────────────────────────────────────

    def get_imu(self) -> IMUReading:
        """Derive IMU from drone state.

        Acceleration is estimated from velocity change since last call.
        Gyro is zero (no rotational model in Phase 0).
        """
        now = time.time()
        # Estimate linear acceleration from velocity delta
        accel = self._drone.velocity - self._prev_velocity
        self._prev_velocity = self._drone.velocity.copy()

        return IMUReading(
            timestamp=now,
            accel=accel.copy(),
            gyro=np.zeros(3),
        )

    def get_gps(self) -> GPSReading:
        """Return true position and velocity (perfect GPS in Phase 0)."""
        now = time.time()
        return GPSReading(
            timestamp=now,
            position=self._drone.position.copy(),
            velocity=self._drone.velocity.copy(),
            accuracy_h=0.0,  # Perfect in sim Phase 0
            accuracy_v=0.0,
            fix_type=3,
        )

    def get_altitude(self) -> AltitudeReading:
        """Return altitude from drone position.

        In the current Y-up coordinate system, Y is altitude.
        This will be updated when NED coordinates are adopted.
        """
        now = time.time()
        alt = float(self._drone.position[1])  # Y-up
        return AltitudeReading(
            timestamp=now,
            altitude_baro=alt,
            altitude_agl=alt,  # No terrain yet, AGL == baro
            altitude_gps=alt,
        )

    def get_battery(self) -> BatteryReading:
        """Map battery_level percentage to BatteryReading."""
        now = time.time()
        pct = self._drone.battery_level
        # Approximate voltage from percentage (4.2V full, 3.3V empty for LiPo)
        voltage = 3.3 + (pct / 100.0) * 0.9
        return BatteryReading(
            timestamp=now,
            voltage=voltage,
            current=0.0,  # No current model yet
            remaining_pct=pct,
        )

    def get_status(self) -> DroneStatus:
        """Return current operational status."""
        now = time.time()
        error_flags = 0
        if self._drone.battery_level <= 5.0:
            error_flags |= 2  # battery_low

        return DroneStatus(
            timestamp=now,
            armed=self._armed,
            mode=self._mode,
            airborne=self._airborne,
            error_flags=error_flags,
        )

    # ── Actuator commands ────────────────────────────────────────

    def set_position(self, x: float, y: float, z: float, yaw: float = 0.0):
        """Map to drone.set_target() in Phase 0.

        Yaw is ignored until Phase 1 adds orientation.
        """
        self._drone.set_target(np.array([x, y, z], dtype=float))
        self._mode = "POSITION"

    def set_velocity(self, vx: float, vy: float, vz: float, yaw_rate: float = 0.0):
        """Stub: velocity control not available until Phase 1.

        In Phase 0, approximates by setting a target position in the
        velocity direction, scaled by a lookahead time.
        """
        lookahead = 2.0  # seconds
        target = self._drone.position + np.array([vx, vy, vz]) * lookahead
        self._drone.set_target(target)
        self._mode = "VELOCITY"

    def set_attitude(self, roll: float, pitch: float, yaw_rate: float, thrust: float):
        """Stub: attitude control not available until Phase 1.

        No-op in the current kinematic model.
        """
        self._mode = "ATTITUDE"

    # ── Lifecycle commands ───────────────────────────────────────

    def arm(self) -> bool:
        """Arm the drone (enable motor commands)."""
        self._armed = True
        self._mode = "HOVER"
        return True

    def disarm(self) -> bool:
        """Disarm the drone."""
        self._armed = False
        self._mode = "IDLE"
        return True

    def takeoff(self, altitude: float) -> bool:
        """Take off to specified altitude.

        In Phase 0, simply sets target to current XZ at requested Y.
        """
        if not self._armed:
            return False
        pos = self._drone.position.copy()
        pos[1] = altitude  # Y-up
        self._drone.set_target(pos)
        self._airborne = True
        self._mode = "TAKEOFF"
        return True

    def land(self) -> bool:
        """Land at current XZ position.

        In Phase 0, sets target Y to 0.
        """
        pos = self._drone.position.copy()
        pos[1] = 0.0  # Ground level
        self._drone.set_target(pos)
        self._mode = "LANDING"
        return True

    # ── Identity ─────────────────────────────────────────────────

    @property
    def drone_id(self) -> int:
        return self._drone.id
