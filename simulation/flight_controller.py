"""Cascaded PID flight controller for quadrotor drones.

Control architecture:
    Horizontal: Position PID → Velocity PID → Desired tilt angles
    Vertical:   Altitude PD → Vertical velocity P → Thrust
    Attitude:   Attitude PID → Rate PID → Motor torque commands
    Mixing:     Thrust + Torques → 4 motor RPMs
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional
from simulation.pid import PID, PID3D
from simulation.physics import QuadrotorPhysics, PhysicsConfig, quat_to_euler


@dataclass
class FlightControllerConfig:
    """Tuning parameters for the flight controller."""
    # Position → Velocity (outer loop, slow)
    pos_kp: float = 0.8
    pos_ki: float = 0.0
    pos_kd: float = 0.2
    max_velocity: float = 8.0       # m/s

    # Velocity → Desired tilt (horizontal only)
    vel_kp: float = 1.2
    vel_ki: float = 0.05
    vel_kd: float = 0.02
    max_tilt_angle: float = 0.35    # radians (~20 degrees)

    # Altitude control (direct PD, not cascaded)
    alt_kp: float = 1.0             # position → velocity
    alt_kd: float = 0.6             # damping on vertical velocity
    alt_ki: float = 0.1             # slow integral for steady-state
    max_vertical_vel: float = 5.0   # m/s vertical speed limit
    max_thrust_adjust: float = 0.25 # max deviation from hover thrust

    # Attitude → Angular rate (fast inner loop)
    att_kp: float = 5.0
    att_ki: float = 0.0
    att_kd: float = 0.2
    max_rate: float = 4.0           # rad/s

    # Angular rate → Motor torques (fastest loop)
    rate_kp: float = 0.3
    rate_ki: float = 0.02
    rate_kd: float = 0.0


class FlightController:
    """Flight controller for a quadrotor.

    Modes:
        IDLE     - Motors off
        HOVER    - Maintain current position
        POSITION - Track position setpoint
        VELOCITY - Track velocity setpoint
        ATTITUDE - Direct attitude + thrust control
        TAKEOFF  - Climbing to target altitude
        LANDING  - Descending to ground
    """

    def __init__(self, physics: QuadrotorPhysics,
                 config: Optional[FlightControllerConfig] = None):
        self.physics = physics
        self.config = config or FlightControllerConfig()
        c = self.config

        # Horizontal position → velocity PID (XZ only)
        self.pos_pid_x = PID(kp=c.pos_kp, ki=c.pos_ki, kd=c.pos_kd,
                             output_min=-c.max_velocity, output_max=c.max_velocity)
        self.pos_pid_z = PID(kp=c.pos_kp, ki=c.pos_ki, kd=c.pos_kd,
                             output_min=-c.max_velocity, output_max=c.max_velocity)

        # Horizontal velocity → tilt PID (XZ only)
        self.vel_pid_x = PID(kp=c.vel_kp, ki=c.vel_ki, kd=c.vel_kd,
                             output_min=-c.max_tilt_angle, output_max=c.max_tilt_angle)
        self.vel_pid_z = PID(kp=c.vel_kp, ki=c.vel_ki, kd=c.vel_kd,
                             output_min=-c.max_tilt_angle, output_max=c.max_tilt_angle)

        # Altitude: simple PID (position error → thrust adjustment)
        self.alt_pid = PID(kp=c.alt_kp, ki=c.alt_ki, kd=c.alt_kd,
                           output_min=-c.max_thrust_adjust,
                           output_max=c.max_thrust_adjust,
                           integral_max=2.0)

        # Attitude → angular rate PIDs
        self.att_pid = PID3D(kp=c.att_kp, ki=c.att_ki, kd=c.att_kd,
                             output_min=-c.max_rate, output_max=c.max_rate)

        # Rate → motor torque PIDs
        self.rate_pid = PID3D(kp=c.rate_kp, ki=c.rate_ki, kd=c.rate_kd,
                              integral_max=2.0)

        # Flight state
        self.mode = "IDLE"
        self.armed = False

        # Setpoints
        self.position_setpoint = np.zeros(3)
        self.velocity_setpoint = np.zeros(3)
        self.attitude_setpoint = np.zeros(3)   # [roll, pitch, yaw]
        self.thrust_setpoint = 0.0
        self.yaw_rate_setpoint = 0.0

        # Hover thrust (normalized RPM fraction)
        self._hover_thrust = self._compute_hover_thrust()

    def _compute_hover_thrust(self) -> float:
        """Compute normalized thrust for hover (0-1 range).

        Returns hover_rpm / max_rpm since the motor mixer maps
        thrust linearly to RPM.
        """
        pc = self.physics.config
        hover_rpm = self.physics.hover_rpm()
        if pc.max_rpm > 0:
            return hover_rpm / pc.max_rpm
        return 0.5

    def set_position(self, pos: np.ndarray, yaw: float = 0.0):
        """Command position setpoint."""
        self.position_setpoint = np.array(pos, dtype=float)
        self.yaw_rate_setpoint = 0.0
        if self.mode not in ("TAKEOFF", "LANDING"):
            self.mode = "POSITION"

    def set_velocity(self, vel: np.ndarray, yaw_rate: float = 0.0):
        """Command velocity setpoint."""
        self.velocity_setpoint = np.array(vel, dtype=float)
        self.yaw_rate_setpoint = yaw_rate
        if self.mode not in ("TAKEOFF", "LANDING"):
            self.mode = "VELOCITY"

    def set_attitude(self, roll: float, pitch: float, yaw_rate: float, thrust: float):
        """Command attitude + thrust directly."""
        self.attitude_setpoint = np.array([roll, pitch, 0.0])
        self.yaw_rate_setpoint = yaw_rate
        self.thrust_setpoint = np.clip(thrust, 0.0, 1.0)
        if self.mode not in ("TAKEOFF", "LANDING"):
            self.mode = "ATTITUDE"

    def arm(self):
        self.armed = True
        if self.mode == "IDLE":
            self.mode = "HOVER"
        self._reset_pids()

    def disarm(self):
        self.armed = False
        self.mode = "IDLE"

    def takeoff(self, altitude: float):
        if not self.armed:
            return
        self.position_setpoint = self.physics.position.copy()
        self.position_setpoint[1] = altitude
        self.mode = "TAKEOFF"
        self._reset_pids()

    def land(self):
        if not self.armed:
            return
        self.position_setpoint = self.physics.position.copy()
        self.position_setpoint[1] = 0.0
        self.mode = "LANDING"

    def update(self, dt: float) -> np.ndarray:
        """Run one control cycle. Returns 4 motor RPMs."""
        if not self.armed or self.mode == "IDLE" or dt <= 0:
            return np.zeros(4)

        pc = self.physics.config
        current_euler = quat_to_euler(self.physics.orientation)
        current_pos = self.physics.position
        current_vel = self.physics.velocity

        # ── Altitude control (direct PD, no cascade) ──
        if self.mode in ("POSITION", "HOVER", "TAKEOFF", "LANDING"):
            alt_error = self.position_setpoint[1] - current_pos[1]

            # PID on altitude error, output is thrust adjustment
            # The derivative term acts on altitude rate (damping)
            thrust_adjust = self.alt_pid.update(alt_error, dt)
            self.thrust_setpoint = np.clip(
                self._hover_thrust + thrust_adjust, 0.05, 0.95
            )

            # Landing completion check
            if self.mode == "LANDING" and current_pos[1] < 0.1 and abs(current_vel[1]) < 0.1:
                self.mode = "IDLE"
                self.armed = False
                return np.zeros(4)

        elif self.mode == "VELOCITY":
            # Velocity mode: use velocity Y component for altitude
            vz_error = self.velocity_setpoint[1] - current_vel[1]
            thrust_adjust = 0.15 * vz_error  # Simple proportional
            self.thrust_setpoint = np.clip(
                self._hover_thrust + thrust_adjust, 0.05, 0.95
            )

        # ── Horizontal control ──
        desired_roll = 0.0
        desired_pitch = 0.0

        if self.mode in ("POSITION", "HOVER", "TAKEOFF", "LANDING"):
            # Position → Velocity (horizontal only)
            vel_sp_x = self.pos_pid_x.update(
                self.position_setpoint[0] - current_pos[0], dt)
            vel_sp_z = self.pos_pid_z.update(
                self.position_setpoint[2] - current_pos[2], dt)

            # Velocity → Tilt angle (horizontal only)
            # Positive roll (Z-axis) tilts thrust in -X, so negate for +X movement
            # Positive pitch (X-axis) tilts thrust in +Z, so no negation needed
            desired_roll = -self.vel_pid_x.update(vel_sp_x - current_vel[0], dt)
            desired_pitch = self.vel_pid_z.update(vel_sp_z - current_vel[2], dt)

        elif self.mode == "VELOCITY":
            desired_roll = -self.vel_pid_x.update(
                self.velocity_setpoint[0] - current_vel[0], dt)
            desired_pitch = self.vel_pid_z.update(
                self.velocity_setpoint[2] - current_vel[2], dt)

        if self.mode != "ATTITUDE":
            self.attitude_setpoint = np.array([desired_roll, desired_pitch, 0.0])

        # ── Attitude → Angular rate ──
        att_error = self.attitude_setpoint - np.array([
            current_euler[0], current_euler[1], 0.0
        ])
        att_error = (att_error + np.pi) % (2 * np.pi) - np.pi
        rate_setpoint = self.att_pid.update(att_error, dt)
        rate_setpoint[2] = self.yaw_rate_setpoint

        # ── Rate → Motor torques ──
        # Map angular velocity from physics axes [wx,wy,wz]=[pitch,yaw,roll]
        # to controller order [roll, pitch, yaw]
        current_rates = np.array([
            self.physics.angular_velocity[2],   # roll rate (wz)
            self.physics.angular_velocity[0],   # pitch rate (wx)
            self.physics.angular_velocity[1],   # yaw rate (wy)
        ])
        rate_error = rate_setpoint - current_rates
        torque_cmd = self.rate_pid.update(rate_error, dt)

        # ── Motor mixing ──
        return self._mix_motors(self.thrust_setpoint, torque_cmd)

    def _mix_motors(self, thrust: float, torque: np.ndarray) -> np.ndarray:
        """Convert thrust + torque to 4 motor RPMs."""
        pc = self.physics.config
        max_rpm = pc.max_rpm
        base_rpm = thrust * max_rpm

        scale = max_rpm * 0.08
        roll_diff = torque[0] * scale
        pitch_diff = torque[1] * scale
        yaw_diff = torque[2] * scale

        rpms = np.array([
            base_rpm + roll_diff + pitch_diff + yaw_diff,
            base_rpm - roll_diff + pitch_diff - yaw_diff,
            base_rpm + roll_diff - pitch_diff - yaw_diff,
            base_rpm - roll_diff - pitch_diff + yaw_diff,
        ])
        return np.clip(rpms, pc.min_rpm, pc.max_rpm)

    def _reset_pids(self):
        self.pos_pid_x.reset()
        self.pos_pid_z.reset()
        self.vel_pid_x.reset()
        self.vel_pid_z.reset()
        self.alt_pid.reset()
        self.att_pid.reset()
        self.rate_pid.reset()
