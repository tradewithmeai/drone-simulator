"""Sensor noise simulation for realistic drone hardware abstraction.

Transforms perfect ground truth from the physics engine into noisy sensor
readings that match real hardware characteristics. Each drone gets an
independent SensorSuite with its own RNG seed for deterministic, reproducible
noise across simulation runs.

Sensor models:
    IMU:         Body-frame specific force + gyro with white noise and bias drift
    GPS:         Rate-limited position/velocity with Gaussian noise
    Barometer:   Altitude with noise and slow drift
    Rangefinder: Accurate AGL with range limit
    Battery:     Voltage/current with ADC noise
"""

import numpy as np
from dataclasses import dataclass
from simulation.physics import QuadrotorPhysics
from hal.types import IMUReading, GPSReading, AltitudeReading, BatteryReading


@dataclass
class SensorConfig:
    """Configuration for sensor noise characteristics.

    Default values approximate consumer-grade drone hardware
    (MPU6000 IMU, u-blox M8 GPS, MS5611 barometer).
    """
    perfect_mode: bool = False

    # IMU — Accelerometer
    accel_noise_std: float = 0.02       # m/s^2 white noise
    accel_bias_drift: float = 0.0001    # m/s^2 per tick random walk step
    accel_bias_max: float = 0.2         # m/s^2 max accumulated bias

    # IMU — Gyroscope
    gyro_noise_std: float = 0.001       # rad/s white noise
    gyro_bias_drift: float = 0.00005    # rad/s per tick random walk step
    gyro_bias_max: float = 0.01         # rad/s max accumulated bias

    # GPS
    gps_update_rate: float = 10.0       # Hz (typical consumer GPS)
    gps_pos_noise_h: float = 1.5        # meters horizontal std dev
    gps_pos_noise_v: float = 3.0        # meters vertical std dev
    gps_vel_noise_std: float = 0.1      # m/s velocity std dev

    # Barometer
    baro_noise_std: float = 0.3         # meters white noise
    baro_bias_drift: float = 0.001      # meters per tick random walk
    baro_bias_max: float = 2.0          # meters max accumulated bias

    # Rangefinder (AGL)
    rangefinder_noise_std: float = 0.02 # meters
    rangefinder_max_range: float = 40.0 # meters (returns -1 beyond this)

    # Battery ADC
    battery_voltage_noise_std: float = 0.01  # volts
    battery_current_noise_std: float = 0.05  # amps

    @property
    def gps_update_period(self) -> float:
        """Seconds between GPS updates."""
        if self.gps_update_rate > 0:
            return 1.0 / self.gps_update_rate
        return 0.1


class SensorSuite:
    """Realistic sensor noise simulation for one drone.

    Holds per-drone state for bias drift, GPS rate limiting, and a seeded
    RNG so noise is deterministic and independent across drones.
    """

    def __init__(self, config: SensorConfig = None, seed: int = None):
        self.config = config or SensorConfig()
        self.rng = np.random.default_rng(seed)

        # IMU bias state (random walk)
        self._accel_bias = np.zeros(3)
        self._gyro_bias = np.zeros(3)

        # GPS rate-limiting state
        self._gps_last_update = -1.0
        self._gps_cached_position = np.zeros(3)
        self._gps_cached_velocity = np.zeros(3)

        # Barometer bias state
        self._baro_bias = 0.0

    def get_imu(self, physics: QuadrotorPhysics, timestamp: float) -> IMUReading:
        """Generate IMU reading in body frame.

        Accelerometer measures specific force (acceleration minus gravity)
        in the body frame. Gyroscope measures angular velocity in body frame.
        """
        c = self.config
        gravity = np.array([0.0, -physics.config.gravity, 0.0])

        # Specific force in world frame: what the IMU senses
        specific_force_world = physics.acceleration - gravity

        # Transform to body frame
        R_T = physics.rotation_matrix.T
        accel_body = R_T @ specific_force_world
        gyro_body = physics.angular_velocity.copy()

        if c.perfect_mode:
            return IMUReading(timestamp=timestamp, accel=accel_body, gyro=gyro_body)

        # White noise
        accel_noisy = accel_body + self._accel_bias + self.rng.normal(0, c.accel_noise_std, 3)
        gyro_noisy = gyro_body + self._gyro_bias + self.rng.normal(0, c.gyro_noise_std, 3)

        # Bias random walk
        self._accel_bias += self.rng.normal(0, c.accel_bias_drift, 3)
        self._accel_bias = np.clip(self._accel_bias, -c.accel_bias_max, c.accel_bias_max)

        self._gyro_bias += self.rng.normal(0, c.gyro_bias_drift, 3)
        self._gyro_bias = np.clip(self._gyro_bias, -c.gyro_bias_max, c.gyro_bias_max)

        return IMUReading(timestamp=timestamp, accel=accel_noisy, gyro=gyro_noisy)

    def get_gps(self, physics: QuadrotorPhysics, timestamp: float) -> GPSReading:
        """Generate GPS reading with rate limiting and noise.

        Returns a stale cached reading between update intervals.
        The timestamp on the reading reflects the actual measurement time
        so consumers can detect stale data.
        """
        c = self.config
        dt = timestamp - self._gps_last_update

        if c.perfect_mode or dt >= c.gps_update_period or self._gps_last_update < 0:
            # New measurement
            self._gps_last_update = timestamp

            if c.perfect_mode:
                self._gps_cached_position = physics.position.copy()
                self._gps_cached_velocity = physics.velocity.copy()
            else:
                # Horizontal and vertical noise (Y-up: index 1 is vertical)
                pos_noise = np.array([
                    self.rng.normal(0, c.gps_pos_noise_h),
                    self.rng.normal(0, c.gps_pos_noise_v),
                    self.rng.normal(0, c.gps_pos_noise_h),
                ])
                self._gps_cached_position = physics.position + pos_noise
                self._gps_cached_velocity = physics.velocity + self.rng.normal(0, c.gps_vel_noise_std, 3)

        return GPSReading(
            timestamp=self._gps_last_update,
            position=self._gps_cached_position.copy(),
            velocity=self._gps_cached_velocity.copy(),
            accuracy_h=c.gps_pos_noise_h,
            accuracy_v=c.gps_pos_noise_v,
            fix_type=3,
        )

    def get_altitude(self, physics: QuadrotorPhysics, timestamp: float) -> AltitudeReading:
        """Generate altitude readings from barometer, rangefinder, and GPS."""
        c = self.config
        true_alt = float(physics.position[1])

        if c.perfect_mode:
            return AltitudeReading(
                timestamp=timestamp,
                altitude_baro=true_alt,
                altitude_agl=true_alt,
                altitude_gps=true_alt,
            )

        # Barometer: noise + slow drift
        baro_alt = true_alt + self._baro_bias + self.rng.normal(0, c.baro_noise_std)
        self._baro_bias += self.rng.normal(0, c.baro_bias_drift)
        self._baro_bias = np.clip(self._baro_bias, -c.baro_bias_max, c.baro_bias_max)

        # Rangefinder (AGL): accurate but range-limited
        if true_alt <= c.rangefinder_max_range:
            agl_alt = true_alt + self.rng.normal(0, c.rangefinder_noise_std)
        else:
            agl_alt = -1.0  # out of range

        # GPS altitude: reuse GPS vertical noise
        gps_reading = self.get_gps(physics, timestamp)
        gps_alt = float(gps_reading.position[1])

        return AltitudeReading(
            timestamp=timestamp,
            altitude_baro=baro_alt,
            altitude_agl=agl_alt,
            altitude_gps=gps_alt,
        )

    def get_battery(self, battery_level: float, voltage: float,
                    current: float, timestamp: float) -> BatteryReading:
        """Add ADC noise to battery readings."""
        c = self.config

        if c.perfect_mode:
            return BatteryReading(
                timestamp=timestamp,
                voltage=voltage,
                current=current,
                remaining_pct=battery_level,
            )

        voltage_noisy = voltage + self.rng.normal(0, c.battery_voltage_noise_std)
        current_noisy = max(0.0, current + self.rng.normal(0, c.battery_current_noise_std))

        return BatteryReading(
            timestamp=timestamp,
            voltage=voltage_noisy,
            current=current_noisy,
            remaining_pct=battery_level,
        )
