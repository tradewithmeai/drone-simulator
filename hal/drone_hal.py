"""Abstract Hardware Abstraction Layer for drone control.

This interface defines what a controller can see (sensors) and do
(actuators). It is identical whether the backend is the simulator
or real hardware (via MAVLink/MAVSDK).

Control code should ONLY interact with drones through this interface.
"""

from abc import ABC, abstractmethod
from hal.types import IMUReading, GPSReading, AltitudeReading, BatteryReading, DroneStatus


class DroneHAL(ABC):
    """Hardware Abstraction Layer - unified interface for sim and real drones.

    Sensor methods return the latest reading from the respective sensor.
    Actuator methods send commands that take effect on the next physics tick.

    Control hierarchy (highest to lowest level):
        set_position  -> flight controller handles everything
        set_velocity  -> flight controller handles attitude + thrust
        set_attitude  -> flight controller handles motor mixing only
    """

    # ── Sensor reads ─────────────────────────────────────────────

    @abstractmethod
    def get_imu(self) -> IMUReading:
        """Accelerometer + gyroscope reading."""
        ...

    @abstractmethod
    def get_gps(self) -> GPSReading:
        """GPS position and velocity in local frame."""
        ...

    @abstractmethod
    def get_altitude(self) -> AltitudeReading:
        """Barometric, rangefinder, and GPS altitude."""
        ...

    @abstractmethod
    def get_battery(self) -> BatteryReading:
        """Battery voltage, current, and remaining percent."""
        ...

    @abstractmethod
    def get_status(self) -> DroneStatus:
        """Armed state, flight mode, and error flags."""
        ...

    # ── Actuator commands ────────────────────────────────────────

    @abstractmethod
    def set_position(self, x: float, y: float, z: float, yaw: float = 0.0):
        """Command a position setpoint in local frame (meters).

        Highest-level command. The flight controller handles velocity,
        attitude, and thrust to reach the target position.
        """
        ...

    @abstractmethod
    def set_velocity(self, vx: float, vy: float, vz: float, yaw_rate: float = 0.0):
        """Command a velocity setpoint in local frame (m/s).

        Mid-level command. The flight controller handles attitude
        and thrust to achieve the desired velocity.
        """
        ...

    @abstractmethod
    def set_attitude(self, roll: float, pitch: float, yaw_rate: float, thrust: float):
        """Command attitude angles (radians) and normalized thrust (0-1).

        Low-level command. Directly sets desired orientation and
        collective thrust. The flight controller handles motor mixing.
        """
        ...

    # ── Lifecycle commands ───────────────────────────────────────

    @abstractmethod
    def arm(self) -> bool:
        """Arm motors. Returns True if successful."""
        ...

    @abstractmethod
    def disarm(self) -> bool:
        """Disarm motors. Returns True if successful."""
        ...

    @abstractmethod
    def takeoff(self, altitude: float) -> bool:
        """Initiate takeoff to specified altitude (meters). Returns True if accepted."""
        ...

    @abstractmethod
    def land(self) -> bool:
        """Initiate landing sequence. Returns True if accepted."""
        ...

    # ── Identity ─────────────────────────────────────────────────

    @property
    @abstractmethod
    def drone_id(self) -> int:
        """Unique identifier for this drone."""
        ...
