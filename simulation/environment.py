"""
Environment module for hide-and-seek game.
Manages obstacles and collision detection.
"""
import numpy as np
import random
from typing import List, Tuple


class Box:
    """Represents a box-shaped obstacle in 3D space."""

    def __init__(self, position: np.ndarray, size: np.ndarray):
        """
        Initialize a box obstacle.

        Args:
            position: Center position [x, y, z]
            size: Box dimensions [width, height, depth]
        """
        self.position = np.array(position, dtype=float)
        self.size = np.array(size, dtype=float)
        self.half_size = self.size / 2.0

    def get_bounds(self) -> Tuple[np.ndarray, np.ndarray]:
        """Get axis-aligned bounding box min/max corners."""
        min_corner = self.position - self.half_size
        max_corner = self.position + self.half_size
        return min_corner, max_corner

    def contains_point(self, point: np.ndarray) -> bool:
        """Check if a point is inside the box."""
        min_corner, max_corner = self.get_bounds()
        return np.all(point >= min_corner) and np.all(point <= max_corner)

    def distance_to_point(self, point: np.ndarray) -> float:
        """
        Calculate minimum distance from point to box surface.
        Negative if inside the box.
        """
        min_corner, max_corner = self.get_bounds()

        # Find closest point on box to the given point
        closest = np.clip(point, min_corner, max_corner)

        # Distance to closest point
        distance = np.linalg.norm(point - closest)

        # If inside, return negative distance
        if self.contains_point(point):
            return -distance
        return distance

    def intersects_sphere(self, center: np.ndarray, radius: float) -> bool:
        """Check if a sphere intersects with the box."""
        return self.distance_to_point(center) < radius


class Environment:
    """Manages the game environment including obstacles."""

    def __init__(self, play_area_size: float = 50.0, num_obstacles: int = 8, seed: int = None):
        """
        Initialize the environment.

        Args:
            play_area_size: Size of the square play area
            num_obstacles: Number of obstacles to generate
            seed: Random seed for reproducible obstacle placement
        """
        self.play_area_size = play_area_size
        self.obstacles: List[Box] = []
        self.seed = seed

        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        self._generate_obstacles(num_obstacles)

    def _generate_obstacles(self, num_obstacles: int):
        """Generate random box obstacles in the play area."""
        half_area = self.play_area_size / 2.0

        for i in range(num_obstacles):
            # Random position within play area (not too close to edges)
            margin = 5.0
            x = random.uniform(-half_area + margin, half_area - margin)
            z = random.uniform(-half_area + margin, half_area - margin)

            # Random height (boxes on ground)
            height = random.uniform(3.0, 8.0)
            y = height / 2.0  # Center Y at half height

            position = np.array([x, y, z])

            # Random size
            width = random.uniform(2.0, 5.0)
            depth = random.uniform(2.0, 5.0)
            size = np.array([width, height, depth])

            obstacle = Box(position, size)
            self.obstacles.append(obstacle)

    def check_collision(self, position: np.ndarray, radius: float = 0.5) -> bool:
        """
        Check if a sphere collides with any obstacle.

        Args:
            position: Sphere center position
            radius: Sphere radius (default is drone radius)

        Returns:
            True if collision detected
        """
        for obstacle in self.obstacles:
            if obstacle.intersects_sphere(position, radius):
                return True
        return False

    def is_in_play_area(self, position: np.ndarray) -> bool:
        """Check if position is within the play area boundaries."""
        half_area = self.play_area_size / 2.0
        x, y, z = position

        return (abs(x) <= half_area and
                abs(z) <= half_area and
                y >= 0 and y <= 20.0)  # Height limit

    def get_random_position(self, min_clearance: float = 2.0, max_attempts: int = 100) -> np.ndarray:
        """
        Get a random position that doesn't collide with obstacles.

        Args:
            min_clearance: Minimum distance from obstacles
            max_attempts: Maximum number of attempts before giving up

        Returns:
            Valid random position [x, y, z]
        """
        half_area = self.play_area_size / 2.0

        for _ in range(max_attempts):
            # Random position
            x = random.uniform(-half_area + 5, half_area - 5)
            z = random.uniform(-half_area + 5, half_area - 5)
            y = random.uniform(2.0, 10.0)

            position = np.array([x, y, z])

            # Check if valid (no collisions with clearance)
            if not self.check_collision(position, min_clearance):
                return position

        # Fallback: return position even if not ideal
        return np.array([0.0, 5.0, 0.0])

    def find_hiding_spots(self, num_spots: int = 10) -> List[np.ndarray]:
        """
        Find good hiding positions near obstacles.

        Args:
            num_spots: Number of hiding spots to find

        Returns:
            List of hiding spot positions
        """
        hiding_spots = []

        for obstacle in self.obstacles:
            # Generate positions around each obstacle
            angles = np.linspace(0, 2 * np.pi, 4, endpoint=False)

            for angle in angles:
                # Position offset from obstacle center
                offset_distance = (obstacle.half_size[0] + obstacle.half_size[2]) / 2.0 + 1.5

                x = obstacle.position[0] + offset_distance * np.cos(angle)
                z = obstacle.position[2] + offset_distance * np.sin(angle)
                y = obstacle.position[1]  # Same height as obstacle center

                position = np.array([x, y, z])

                # Verify position is valid
                if self.is_in_play_area(position) and not self.check_collision(position, 0.5):
                    hiding_spots.append(position)

                    if len(hiding_spots) >= num_spots:
                        return hiding_spots

        # If not enough spots found, add random positions
        while len(hiding_spots) < num_spots:
            hiding_spots.append(self.get_random_position(min_clearance=1.0))

        return hiding_spots

    def get_obstacles(self) -> List[Box]:
        """Get list of all obstacles."""
        return self.obstacles

    def is_line_of_sight_clear(self, pos1: np.ndarray, pos2: np.ndarray, num_samples: int = 20) -> bool:
        """
        Check if there's a clear line of sight between two positions.
        Uses sampling along the line to detect obstacle intersection.

        Args:
            pos1: Start position
            pos2: End position
            num_samples: Number of points to sample along the line

        Returns:
            True if line of sight is clear
        """
        # Sample points along the line
        for i in range(num_samples):
            t = i / (num_samples - 1)
            sample_point = pos1 + t * (pos2 - pos1)

            # Check if sample point is inside any obstacle
            if self.check_collision(sample_point, radius=0.1):
                return False

        return True
