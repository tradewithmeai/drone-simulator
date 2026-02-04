"""Data types for the Hardware Abstraction Layer.

These dataclasses define the sensor and status contracts between
control code and drone hardware. They are identical whether the
backend is a simulator or real hardware.
"""

from dataclasses import dataclass, field
import numpy as np


@dataclass
class IMUReading:
    """Inertial Measurement Unit reading (accelerometer + gyroscope)."""
    timestamp: float                        # seconds since epoch
    accel: np.ndarray = field(default_factory=lambda: np.zeros(3))   # [ax, ay, az] m/s^2
    gyro: np.ndarray = field(default_factory=lambda: np.zeros(3))    # [wx, wy, wz] rad/s


@dataclass
class GPSReading:
    """GPS position and velocity fix."""
    timestamp: float                        # seconds since epoch
    position: np.ndarray = field(default_factory=lambda: np.zeros(3))  # [x, y, z] local frame (meters)
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(3))  # [vx, vy, vz] m/s
    accuracy_h: float = 1.5                 # horizontal accuracy (meters)
    accuracy_v: float = 3.0                 # vertical accuracy (meters)
    fix_type: int = 3                       # 0=no fix, 2=2D, 3=3D


@dataclass
class AltitudeReading:
    """Altitude from barometer and/or rangefinder."""
    timestamp: float                        # seconds since epoch
    altitude_baro: float = 0.0              # barometric altitude (meters above sea level)
    altitude_agl: float = 0.0              # above ground level from rangefinder (meters)
    altitude_gps: float = 0.0              # GPS altitude (meters)


@dataclass
class BatteryReading:
    """Battery state."""
    timestamp: float                        # seconds since epoch
    voltage: float = 0.0                    # volts
    current: float = 0.0                    # amps (instantaneous draw)
    remaining_pct: float = 100.0            # 0-100 percent remaining


@dataclass
class DroneStatus:
    """Overall drone state and health."""
    timestamp: float                        # seconds since epoch
    armed: bool = False                     # motors armed and ready
    mode: str = "IDLE"                      # IDLE, TAKEOFF, HOVER, POSITION, VELOCITY, ATTITUDE, LANDING, CRASHED
    airborne: bool = False                  # currently in the air
    error_flags: int = 0                    # bitmask: 1=motor, 2=battery_low, 4=gps_lost, 8=imu_fault
