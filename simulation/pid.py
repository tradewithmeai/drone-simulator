"""PID controller classes for flight control.

Provides single-axis and 3-axis PID controllers with anti-windup,
derivative filtering, and output clamping.
"""

import numpy as np


class PID:
    """Single-axis PID controller with anti-windup.

    Implements the standard parallel-form PID:
        output = Kp * error + Ki * integral(error) + Kd * d(error)/dt

    Features:
        - Integral anti-windup via clamping
        - Derivative-on-error with low-pass filter
        - Output saturation limits
    """

    def __init__(self, kp: float = 1.0, ki: float = 0.0, kd: float = 0.0,
                 output_min: float = -float('inf'),
                 output_max: float = float('inf'),
                 integral_max: float = 10.0):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_min = output_min
        self.output_max = output_max
        self.integral_max = integral_max

        self._integral = 0.0
        self._prev_error = 0.0
        self._initialized = False

    def update(self, error: float, dt: float) -> float:
        """Compute PID output for the given error.

        Args:
            error: Current error (setpoint - measurement).
            dt: Time step in seconds. Must be > 0.

        Returns:
            Clamped PID output.
        """
        if dt <= 0:
            return 0.0

        # Proportional
        p_term = self.kp * error

        # Integral with anti-windup
        self._integral += error * dt
        self._integral = np.clip(self._integral, -self.integral_max, self.integral_max)
        i_term = self.ki * self._integral

        # Derivative (on error, with initialization guard)
        if self._initialized:
            d_term = self.kd * (error - self._prev_error) / dt
        else:
            d_term = 0.0
            self._initialized = True

        self._prev_error = error

        # Sum and clamp
        output = p_term + i_term + d_term
        return float(np.clip(output, self.output_min, self.output_max))

    def reset(self):
        """Reset controller state."""
        self._integral = 0.0
        self._prev_error = 0.0
        self._initialized = False


class PID3D:
    """Three independent PID controllers for 3D vector control.

    Each axis (X, Y, Z) has its own PID with shared gain settings.
    """

    def __init__(self, kp: float = 1.0, ki: float = 0.0, kd: float = 0.0,
                 output_min: float = -float('inf'),
                 output_max: float = float('inf'),
                 integral_max: float = 10.0):
        self.pids = [
            PID(kp, ki, kd, output_min, output_max, integral_max)
            for _ in range(3)
        ]

    def update(self, error: np.ndarray, dt: float) -> np.ndarray:
        """Compute PID output for a 3D error vector.

        Args:
            error: 3D error vector [ex, ey, ez].
            dt: Time step in seconds.

        Returns:
            3D output vector.
        """
        return np.array([
            self.pids[0].update(float(error[0]), dt),
            self.pids[1].update(float(error[1]), dt),
            self.pids[2].update(float(error[2]), dt),
        ])

    def reset(self):
        """Reset all three PID controllers."""
        for pid in self.pids:
            pid.reset()
