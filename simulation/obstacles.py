"""Static obstacle system for the drone simulator.

Supports axis-aligned boxes and vertical cylinders. Provides collision
detection against spheres (drone hitboxes) with penetration depth and
collision normal for physics response.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any, Optional


@dataclass
class Box:
    """Axis-aligned box obstacle.

    Attributes:
        position: Center of the box [x, y, z].
        half_size: Half-extents [dx, dy, dz] (half of full width/height/depth).
        color: RGB color [0-1].
    """
    position: np.ndarray
    half_size: np.ndarray
    color: List[float]

    @property
    def min_corner(self) -> np.ndarray:
        return self.position - self.half_size

    @property
    def max_corner(self) -> np.ndarray:
        return self.position + self.half_size


@dataclass
class Cylinder:
    """Vertical cylinder obstacle (Y-up).

    Attributes:
        position: Base center [x, y, z] (bottom of the cylinder).
        radius: Cylinder radius in meters.
        height: Cylinder height in meters (extends upward along +Y).
        color: RGB color [0-1].
    """
    position: np.ndarray
    radius: float
    height: float
    color: List[float]

    @property
    def y_min(self) -> float:
        return float(self.position[1])

    @property
    def y_max(self) -> float:
        return float(self.position[1] + self.height)


class ObstacleManager:
    """Manages static obstacles and their collision detection."""

    def __init__(self):
        self.boxes: List[Box] = []
        self.cylinders: List[Cylinder] = []
        # Track insertion order for remove_last
        self._order: List[Tuple[str, int]] = []  # ('box', idx) or ('cyl', idx)

    def add_box(self, position, size, color=None):
        """Add an axis-aligned box obstacle.

        Args:
            position: Center position [x, y, z].
            size: Full extents [width, height, depth].
            color: RGB color (default grey).
        """
        box = Box(
            position=np.array(position, dtype=float),
            half_size=np.array(size, dtype=float) / 2.0,
            color=color or [0.5, 0.5, 0.5],
        )
        self.boxes.append(box)
        self._order.append(('box', len(self.boxes) - 1))

    def add_cylinder(self, position, radius, height, color=None):
        """Add a vertical cylinder obstacle.

        Args:
            position: Base center [x, y, z].
            radius: Cylinder radius in meters.
            height: Cylinder height in meters.
            color: RGB color (default brown).
        """
        cyl = Cylinder(
            position=np.array(position, dtype=float),
            radius=float(radius),
            height=float(height),
            color=color or [0.6, 0.3, 0.1],
        )
        self.cylinders.append(cyl)
        self._order.append(('cyl', len(self.cylinders) - 1))

    def remove_last(self):
        """Remove the most recently added obstacle."""
        if not self._order:
            return
        kind, idx = self._order.pop()
        if kind == 'box' and idx < len(self.boxes):
            self.boxes.pop(idx)
        elif kind == 'cyl' and idx < len(self.cylinders):
            self.cylinders.pop(idx)

    def clear_all(self):
        """Remove all obstacles."""
        self.boxes.clear()
        self.cylinders.clear()
        self._order.clear()

    def load_scene(self, scene_list: List[Dict[str, Any]]):
        """Load obstacles from a list of config dicts.

        Args:
            scene_list: List of obstacle definitions, each with 'type' key
                        and shape-specific parameters.
        """
        self.clear_all()
        for obs in scene_list:
            if obs['type'] == 'box':
                self.add_box(obs['position'], obs['size'],
                             obs.get('color'))
            elif obs['type'] == 'cylinder':
                self.add_cylinder(obs['position'], obs['radius'],
                                  obs['height'], obs.get('color'))

    def get_states(self) -> List[Dict[str, Any]]:
        """Serialize all obstacles for GUI rendering.

        Returns:
            List of dicts with 'type' and shape-specific fields.
        """
        states = []
        for box in self.boxes:
            states.append({
                'type': 'box',
                'position': box.position.tolist(),
                'size': (box.half_size * 2.0).tolist(),
                'color': box.color,
            })
        for cyl in self.cylinders:
            states.append({
                'type': 'cylinder',
                'position': cyl.position.tolist(),
                'radius': cyl.radius,
                'height': cyl.height,
                'color': cyl.color,
            })
        return states

    def check_collision(self, sphere_pos: np.ndarray,
                        sphere_radius: float
                        ) -> Tuple[bool, np.ndarray, float]:
        """Check if a sphere collides with any obstacle.

        Args:
            sphere_pos: Sphere center [x, y, z].
            sphere_radius: Sphere radius in meters.

        Returns:
            (collided, normal, penetration) where normal points away from
            the obstacle surface and penetration is the overlap distance.
            Returns (False, zero_vec, 0.0) on miss.
        """
        for box in self.boxes:
            hit, normal, pen = self._sphere_box(sphere_pos, sphere_radius, box)
            if hit:
                return True, normal, pen

        for cyl in self.cylinders:
            hit, normal, pen = self._sphere_cylinder(sphere_pos, sphere_radius, cyl)
            if hit:
                return True, normal, pen

        return False, np.zeros(3), 0.0

    # ------------------------------------------------------------------
    # Collision primitives
    # ------------------------------------------------------------------

    @staticmethod
    def _sphere_box(pos: np.ndarray, radius: float,
                    box: Box) -> Tuple[bool, np.ndarray, float]:
        """Sphere vs axis-aligned box collision.

        Finds the closest point on the box to the sphere center. If the
        distance is less than the sphere radius, a collision is reported.
        """
        closest = np.clip(pos, box.min_corner, box.max_corner)
        delta = pos - closest
        dist_sq = np.dot(delta, delta)

        if dist_sq < radius * radius:
            dist = np.sqrt(dist_sq)
            if dist < 1e-8:
                # Sphere center is inside the box — push out along nearest face
                to_min = pos - box.min_corner
                to_max = box.max_corner - pos
                face_dists = np.concatenate([to_min, to_max])
                face_idx = int(np.argmin(face_dists))
                normal = np.zeros(3)
                axis = face_idx % 3
                sign = 1.0 if face_idx >= 3 else -1.0
                normal[axis] = sign
                penetration = radius + float(face_dists[face_idx])
            else:
                normal = delta / dist
                penetration = radius - dist
            return True, normal, penetration

        return False, np.zeros(3), 0.0

    @staticmethod
    def _sphere_cylinder(pos: np.ndarray, radius: float,
                         cyl: Cylinder) -> Tuple[bool, np.ndarray, float]:
        """Sphere vs vertical cylinder collision.

        Checks vertical overlap first, then does a 2D circle-circle test
        in the XZ plane.
        """
        # Vertical bounds check
        if pos[1] + radius < cyl.y_min or pos[1] - radius > cyl.y_max:
            return False, np.zeros(3), 0.0

        # 2D distance in XZ plane from cylinder axis
        dx = pos[0] - cyl.position[0]
        dz = pos[2] - cyl.position[2]
        dist_xz = np.sqrt(dx * dx + dz * dz)

        combined = cyl.radius + radius
        if dist_xz < combined:
            if dist_xz < 1e-8:
                # On the cylinder axis — pick arbitrary horizontal normal
                normal = np.array([1.0, 0.0, 0.0])
            else:
                normal = np.array([dx / dist_xz, 0.0, dz / dist_xz])
            penetration = combined - dist_xz
            return True, normal, penetration

        return False, np.zeros(3), 0.0
