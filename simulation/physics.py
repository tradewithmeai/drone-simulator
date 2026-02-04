"""6-DOF rigid-body quadrotor physics simulation.

Implements a physically accurate quadrotor model with:
- 4 motors producing thrust and torque
- Gravity, linear drag, and optional wind forces
- Quaternion-based orientation (no gimbal lock)
- Euler integration of translational and rotational dynamics

Coordinate system: Y-up (matching the GUI renderer).
- X: right
- Y: up (altitude)
- Z: forward

When the quadrotor is level, thrust points along +Y (up).
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional


# ── Quaternion utilities ─────────────────────────────────────────

def quat_multiply(q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
    """Hamilton product of two quaternions [w, x, y, z]."""
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return np.array([
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
    ])


def quat_to_rotation_matrix(q: np.ndarray) -> np.ndarray:
    """Convert quaternion [w, x, y, z] to 3x3 rotation matrix."""
    w, x, y, z = q
    return np.array([
        [1 - 2*(y*y + z*z),     2*(x*y - w*z),     2*(x*z + w*y)],
        [    2*(x*y + w*z), 1 - 2*(x*x + z*z),     2*(y*z - w*x)],
        [    2*(x*z - w*y),     2*(y*z + w*x), 1 - 2*(x*x + y*y)],
    ])


def quat_integrate(q: np.ndarray, angular_vel: np.ndarray, dt: float) -> np.ndarray:
    """Integrate quaternion given angular velocity (body frame) and timestep.

    Uses first-order quaternion derivative: dq/dt = 0.5 * q * omega_quat
    where omega_quat = [0, wx, wy, wz].
    """
    omega_quat = np.array([0.0, angular_vel[0], angular_vel[1], angular_vel[2]])
    q_dot = 0.5 * quat_multiply(q, omega_quat)
    q_new = q + q_dot * dt
    norm = np.linalg.norm(q_new)
    if norm > 1e-10:
        q_new /= norm
    return q_new


def quat_to_euler(q: np.ndarray) -> np.ndarray:
    """Convert quaternion to Euler angles [roll, pitch, yaw] in radians.

    Uses Y-up convention with intrinsic YXZ rotation order:
    - Roll: rotation around Z axis (forward) — tilts left/right
    - Pitch: rotation around X axis (right) — tilts nose up/down
    - Yaw: rotation around Y axis (up) — heading

    Derived from R = Rz(roll) * Rx(pitch) * Ry(yaw).
    """
    w, x, y, z = q

    # Roll (Z-axis rotation)
    sinr_cosp = 2.0 * (w * z - x * y)
    cosr_cosp = 1.0 - 2.0 * (x * x + z * z)
    roll = np.arctan2(sinr_cosp, cosr_cosp)

    # Pitch (X-axis rotation)
    sinp = 2.0 * (w * x + y * z)
    sinp = np.clip(sinp, -1.0, 1.0)
    pitch = np.arcsin(sinp)

    # Yaw (Y-axis rotation)
    siny_cosp = 2.0 * (w * y - x * z)
    cosy_cosp = 1.0 - 2.0 * (x * x + y * y)
    yaw = np.arctan2(siny_cosp, cosy_cosp)

    return np.array([roll, pitch, yaw])


def euler_to_quat(roll: float, pitch: float, yaw: float) -> np.ndarray:
    """Convert Euler angles [roll, pitch, yaw] to quaternion [w, x, y, z].

    Matches quat_to_euler: intrinsic YXZ rotation order.
    q = q_roll(Z) * q_pitch(X) * q_yaw(Y)
    """
    cr, sr = np.cos(roll / 2), np.sin(roll / 2)
    cp, sp = np.cos(pitch / 2), np.sin(pitch / 2)
    cy, sy = np.cos(yaw / 2), np.sin(yaw / 2)

    return np.array([
        cr * cp * cy - sr * sp * sy,   # w
        cr * sp * cy - sr * cp * sy,   # x
        cr * cp * sy + sr * sp * cy,   # y
        cr * sp * sy + sr * cp * cy,   # z
    ])


@dataclass
class PhysicsConfig:
    """Configuration for quadrotor physics."""
    mass: float = 1.5                   # kg
    arm_length: float = 0.25            # meters (motor to center)
    gravity: float = 9.81               # m/s^2
    drag_coeff: float = 0.1             # linear drag coefficient (N/(m/s))
    angular_drag: float = 0.05          # angular drag coefficient

    # Motor model — tuned for 250mm quadrotor (~3:1 thrust-to-weight ratio)
    # hover at ~55% throttle, max ~45N total thrust
    motor_thrust_coeff: float = 1.9e-7  # thrust = k * rpm^2 (N)
    motor_torque_coeff: float = 5.0e-9  # reaction torque = k * rpm^2 (N*m)
    max_rpm: float = 8000.0
    min_rpm: float = 0.0
    motor_time_constant: float = 0.02   # motor response time (seconds)

    # Inertia (diagonal for symmetric quadrotor)
    inertia_xx: float = 0.02            # kg*m^2 (roll)
    inertia_yy: float = 0.04            # kg*m^2 (yaw - around thrust axis)
    inertia_zz: float = 0.02            # kg*m^2 (pitch)


class QuadrotorPhysics:
    """6-DOF rigid body quadrotor simulation.

    Motor layout (X configuration, viewed from above, Y pointing up):

          Front
        0       1
          \\   /
           \\ /
            X
           / \\
          /   \\
        2       3
          Back

    Motors 0, 3 spin clockwise. Motors 1, 2 spin counter-clockwise.
    """

    def __init__(self, config: Optional[PhysicsConfig] = None):
        self.config = config or PhysicsConfig()
        c = self.config

        # Inertia tensor (diagonal)
        self.inertia = np.diag([c.inertia_xx, c.inertia_yy, c.inertia_zz])
        self.inertia_inv = np.diag([1.0/c.inertia_xx, 1.0/c.inertia_yy, 1.0/c.inertia_zz])

        # Gravity vector (Y-up: gravity pulls down)
        self.gravity_vec = np.array([0.0, -c.gravity, 0.0])

        # State
        self.position = np.zeros(3)                          # [x, y, z] meters
        self.velocity = np.zeros(3)                          # [vx, vy, vz] m/s
        self.orientation = np.array([1.0, 0.0, 0.0, 0.0])   # quaternion [w, x, y, z]
        self.angular_velocity = np.zeros(3)                  # [wx, wy, wz] rad/s (body frame)

        # Motor state (actual RPMs, subject to motor dynamics)
        self.motor_rpms = np.zeros(4)
        self.motor_rpm_targets = np.zeros(4)

        # Computed values (updated each tick)
        self.acceleration = np.zeros(3)                      # world frame linear accel
        self.rotation_matrix = np.eye(3)

    def set_motor_rpms(self, rpms: np.ndarray):
        """Set target RPMs for all 4 motors.

        Actual RPMs lag behind targets based on motor_time_constant.
        """
        c = self.config
        self.motor_rpm_targets = np.clip(rpms, c.min_rpm, c.max_rpm)

    def hover_rpm(self) -> float:
        """Calculate the RPM needed for each motor to hover."""
        c = self.config
        # Total thrust needed = weight
        total_thrust = c.mass * c.gravity
        # Each motor provides 1/4 of total thrust
        per_motor_thrust = total_thrust / 4.0
        # thrust = k * rpm^2  =>  rpm = sqrt(thrust / k)
        return np.sqrt(per_motor_thrust / c.motor_thrust_coeff)

    def update(self, dt: float, wind_force: Optional[np.ndarray] = None):
        """Advance physics by one timestep.

        Args:
            dt: Time step in seconds. Should be small (1/60s or less).
            wind_force: Optional external wind force in world frame [N].
        """
        if dt <= 0:
            return

        c = self.config

        # 1. Motor dynamics — RPMs approach targets with first-order lag
        alpha = min(1.0, dt / c.motor_time_constant) if c.motor_time_constant > 0 else 1.0
        self.motor_rpms += alpha * (self.motor_rpm_targets - self.motor_rpms)
        self.motor_rpms = np.clip(self.motor_rpms, c.min_rpm, c.max_rpm)

        # 2. Compute thrust from each motor (body frame, thrust along +Y)
        thrusts = c.motor_thrust_coeff * self.motor_rpms ** 2
        total_thrust_body = np.array([0.0, np.sum(thrusts), 0.0])

        # 3. Rotation matrix (body → world)
        self.rotation_matrix = quat_to_rotation_matrix(self.orientation)
        R = self.rotation_matrix

        # 4. Forces in world frame
        thrust_world = R @ total_thrust_body
        gravity_force = c.mass * self.gravity_vec
        drag_force = -c.drag_coeff * self.velocity * np.abs(self.velocity)

        wind = wind_force if wind_force is not None else np.zeros(3)

        net_force = thrust_world + gravity_force + drag_force + wind

        # 5. Linear acceleration and integration
        self.acceleration = net_force / c.mass
        self.velocity += self.acceleration * dt
        self.position += self.velocity * dt

        # 6. Ground constraint (Y-up: ground at Y=0)
        if self.position[1] < 0.0:
            self.position[1] = 0.0
            if self.velocity[1] < 0.0:
                self.velocity[1] = 0.0

        # 7. Motor torques (body frame)
        # X-config: motors at 45° angles
        L = c.arm_length * 0.7071  # arm_length * cos(45°)

        # Roll torque (around Z axis in Y-up): differential left/right
        tau_roll = L * (thrusts[0] + thrusts[2] - thrusts[1] - thrusts[3])

        # Pitch torque (around X axis in Y-up): differential front/back
        tau_pitch = L * (thrusts[0] + thrusts[1] - thrusts[2] - thrusts[3])

        # Yaw torque (around Y axis): reaction torques from motor spin
        # Motors 0,3 CW (positive torque), 1,2 CCW (negative torque)
        tau_yaw = c.motor_torque_coeff * (
            self.motor_rpms[0]**2 + self.motor_rpms[3]**2
            - self.motor_rpms[1]**2 - self.motor_rpms[2]**2
        )

        torque = np.array([tau_pitch, tau_yaw, tau_roll])

        # 8. Angular drag
        angular_drag = -c.angular_drag * self.angular_velocity

        # 9. Angular acceleration (body frame): I * alpha = torque - omega x (I * omega)
        gyroscopic = np.cross(self.angular_velocity, self.inertia @ self.angular_velocity)
        angular_accel = self.inertia_inv @ (torque + angular_drag - gyroscopic)

        # 10. Angular velocity and quaternion integration
        self.angular_velocity += angular_accel * dt
        # Clamp angular velocity to prevent runaway
        max_angular_vel = 20.0  # rad/s
        self.angular_velocity = np.clip(self.angular_velocity, -max_angular_vel, max_angular_vel)
        self.orientation = quat_integrate(self.orientation, self.angular_velocity, dt)

        # Renormalize quaternion
        norm = np.linalg.norm(self.orientation)
        if norm > 1e-10:
            self.orientation /= norm
        else:
            # Recovery: reset to identity quaternion
            self.orientation = np.array([1.0, 0.0, 0.0, 0.0])

        # NaN protection — reset state if physics explodes
        if (np.any(np.isnan(self.position)) or np.any(np.isnan(self.velocity))
                or np.any(np.isnan(self.orientation))):
            self.velocity = np.zeros(3)
            self.angular_velocity = np.zeros(3)
            self.orientation = np.array([1.0, 0.0, 0.0, 0.0])
            self.motor_rpms = np.zeros(4)
            self.motor_rpm_targets = np.zeros(4)

    def get_euler_angles(self) -> np.ndarray:
        """Get current orientation as Euler angles [roll, pitch, yaw]."""
        return quat_to_euler(self.orientation)

    def get_up_vector(self) -> np.ndarray:
        """Get the drone's up direction in world frame."""
        return self.rotation_matrix @ np.array([0.0, 1.0, 0.0])

    def get_forward_vector(self) -> np.ndarray:
        """Get the drone's forward direction in world frame."""
        return self.rotation_matrix @ np.array([0.0, 0.0, 1.0])

    def is_on_ground(self) -> bool:
        """Check if the drone is on or very near the ground."""
        return self.position[1] < 0.05

    def get_speed(self) -> float:
        """Get scalar speed."""
        return float(np.linalg.norm(self.velocity))

    def get_power_draw(self) -> float:
        """Estimate power draw from motor RPMs (watts).

        Simple model: power proportional to thrust * angular_velocity.
        P = k * rpm^3 (approximation for propeller power).
        """
        c = self.config
        power_coeff = c.motor_thrust_coeff * 1e-3  # rough scaling
        return float(np.sum(power_coeff * np.abs(self.motor_rpms) ** 3))
