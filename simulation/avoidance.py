"""Artificial Potential Fields obstacle avoidance.

Computes repulsive velocity adjustments from nearby obstacles.
Integrates into the flight controller by modifying velocity setpoints
between the position PID and velocity PID stages.
"""

import numpy as np
from dataclasses import dataclass
from typing import Tuple, Optional


@dataclass
class AvoidanceConfig:
    """Configuration for APF obstacle avoidance."""
    enabled: bool = False
    sensor_range: float = 5.0           # meters — detection range
    safety_margin: float = 0.5          # meters — extra clearance
    repulsion_gain: float = 3.0         # strength of repulsive force
    velocity_limit: float = 2.0         # max avoidance velocity (m/s)


class APFAvoidance:
    """Artificial Potential Fields obstacle avoidance."""

    def __init__(self, config: Optional[AvoidanceConfig] = None):
        self.config = config or AvoidanceConfig()

    def compute_avoidance_velocity(self, position: np.ndarray,
                                   obstacles,
                                   drone_radius: float = 0.3) -> np.ndarray:
        """Compute velocity adjustment to steer away from obstacles.

        Args:
            position: Current drone position [x, y, z].
            obstacles: ObstacleManager instance.
            drone_radius: Drone collision sphere radius.

        Returns:
            Velocity adjustment vector [vx, vy, vz].
        """
        if not self.config.enabled or obstacles is None:
            return np.zeros(3)

        c = self.config
        total = np.zeros(3)

        for box in obstacles.boxes:
            dist, direction = self._distance_to_box(position, box)
            effective = dist - drone_radius - c.safety_margin
            if 0 < effective < c.sensor_range:
                magnitude = c.repulsion_gain / max(effective * effective, 0.01)
                total += direction * magnitude

        for cyl in obstacles.cylinders:
            dist, direction = self._distance_to_cylinder(position, cyl)
            effective = dist - drone_radius - c.safety_margin
            if 0 < effective < c.sensor_range:
                magnitude = c.repulsion_gain / max(effective * effective, 0.01)
                total += direction * magnitude

        mag = np.linalg.norm(total)
        if mag > c.velocity_limit:
            total = total * (c.velocity_limit / mag)

        return total

    @staticmethod
    def _distance_to_box(pos: np.ndarray, box) -> Tuple[float, np.ndarray]:
        """Distance and away-direction from point to box surface."""
        closest = np.clip(pos, box.min_corner, box.max_corner)
        delta = pos - closest
        dist = np.linalg.norm(delta)

        if dist < 1e-8:
            # Inside box — push toward nearest face
            to_min = pos - box.min_corner
            to_max = box.max_corner - pos
            face_dists = np.concatenate([to_min, to_max])
            idx = int(np.argmin(face_dists))
            direction = np.zeros(3)
            axis = idx % 3
            direction[axis] = -1.0 if idx < 3 else 1.0
            return 0.0, direction

        return dist, delta / dist

    @staticmethod
    def _distance_to_cylinder(pos: np.ndarray, cyl) -> Tuple[float, np.ndarray]:
        """Distance and away-direction from point to cylinder surface."""
        dx = pos[0] - cyl.position[0]
        dz = pos[2] - cyl.position[2]
        dist_xz = np.sqrt(dx * dx + dz * dz)

        # Check vertical bounds
        if pos[1] < cyl.y_min:
            if dist_xz <= cyl.radius:
                return cyl.y_min - pos[1], np.array([0.0, -1.0, 0.0])
            edge_dir_x = dx / dist_xz if dist_xz > 1e-8 else 1.0
            edge_dir_z = dz / dist_xz if dist_xz > 1e-8 else 0.0
            edge = np.array([
                cyl.position[0] + cyl.radius * edge_dir_x,
                cyl.y_min,
                cyl.position[2] + cyl.radius * edge_dir_z,
            ])
            delta = pos - edge
            d = np.linalg.norm(delta)
            return (d, delta / d) if d > 1e-8 else (0.0, np.array([0, -1, 0]))

        if pos[1] > cyl.y_max:
            if dist_xz <= cyl.radius:
                return pos[1] - cyl.y_max, np.array([0.0, 1.0, 0.0])
            edge_dir_x = dx / dist_xz if dist_xz > 1e-8 else 1.0
            edge_dir_z = dz / dist_xz if dist_xz > 1e-8 else 0.0
            edge = np.array([
                cyl.position[0] + cyl.radius * edge_dir_x,
                cyl.y_max,
                cyl.position[2] + cyl.radius * edge_dir_z,
            ])
            delta = pos - edge
            d = np.linalg.norm(delta)
            return (d, delta / d) if d > 1e-8 else (0.0, np.array([0, 1, 0]))

        # Within vertical bounds — radial distance in XZ
        if dist_xz < 1e-8:
            return cyl.radius, np.array([1.0, 0.0, 0.0])

        direction = np.array([dx / dist_xz, 0.0, dz / dist_xz])
        if dist_xz < cyl.radius:
            # Inside cylinder
            return cyl.radius - dist_xz, direction
        return dist_xz - cyl.radius, direction
