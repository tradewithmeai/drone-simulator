"""Environment model for the drone simulation.

Provides wind forces and atmospheric conditions.
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class WindConfig:
    """Wind model configuration."""
    enabled: bool = False
    base_velocity: np.ndarray = None    # constant wind [vx, vy, vz] m/s
    gust_magnitude: float = 2.0         # max gust strength (m/s)
    gust_frequency: float = 0.1         # how often gusts change (Hz)

    def __post_init__(self):
        if self.base_velocity is None:
            self.base_velocity = np.zeros(3)
        self.base_velocity = np.array(self.base_velocity, dtype=float)


class Environment:
    """Simulation environment providing wind and atmospheric effects."""

    def __init__(self, wind_config: Optional[WindConfig] = None):
        self.wind = wind_config or WindConfig()
        self._gust = np.zeros(3)
        self._gust_timer = 0.0
        self._gust_target = np.zeros(3)

    def get_wind_force(self, time: float, drag_coeff: float = 0.1) -> np.ndarray:
        """Get wind force vector at the current time.

        The wind force is computed as drag from relative wind velocity.
        For simplicity, this returns the wind velocity as a force
        scaled by the drag coefficient.

        Args:
            time: Current simulation time in seconds.
            drag_coeff: Drag coefficient of the object.

        Returns:
            Wind force vector [fx, fy, fz] in Newtons.
        """
        if not self.wind.enabled:
            return np.zeros(3)

        wind_vel = self.wind.base_velocity.copy()

        # Add gusts (smooth random changes)
        if self.wind.gust_magnitude > 0:
            self._gust_timer += 1.0 / 60.0  # approximate dt
            if self._gust_timer >= 1.0 / max(self.wind.gust_frequency, 0.01):
                self._gust_timer = 0.0
                self._gust_target = np.random.uniform(
                    -self.wind.gust_magnitude,
                    self.wind.gust_magnitude,
                    3
                )
                # Wind is primarily horizontal
                self._gust_target[1] *= 0.2

            # Smooth interpolation toward gust target
            alpha = 0.05
            self._gust += alpha * (self._gust_target - self._gust)
            wind_vel += self._gust

        # Wind force = drag_coeff * wind_velocity^2 * sign(wind_velocity)
        force = drag_coeff * wind_vel * np.abs(wind_vel)
        return force

    def update(self, dt: float):
        """Update environment state.

        Args:
            dt: Time step in seconds.
        """
        # Update gust timer with actual dt
        if self.wind.enabled and self.wind.gust_magnitude > 0:
            self._gust_timer += dt
            if self._gust_timer >= 1.0 / max(self.wind.gust_frequency, 0.01):
                self._gust_timer = 0.0
                self._gust_target = np.random.uniform(
                    -self.wind.gust_magnitude,
                    self.wind.gust_magnitude,
                    3
                )
                self._gust_target[1] *= 0.2

            alpha = min(1.0, dt * 2.0)
            self._gust += alpha * (self._gust_target - self._gust)
