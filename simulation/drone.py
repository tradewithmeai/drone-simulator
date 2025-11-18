import numpy as np
from typing import Tuple, List
import time

class Drone:
    """Individual drone with physics simulation and movement control."""

    def __init__(self, drone_id: int, position: np.ndarray, color: List[float], role: str = "hider"):
        self.id = drone_id
        self.position = np.array(position, dtype=float)
        self.velocity = np.zeros(3, dtype=float)
        self.target_position = self.position.copy()
        self.color = color
        self.max_speed = 10.0
        self.max_acceleration = 5.0
        self.proportional_gain = 1.2
        self.convergence_threshold = 0.1
        self.settled = False
        self.battery_level = 100.0

        # Hide-and-seek game attributes
        self.role = role  # "seeker" or "hider"
        self.detected = False  # Has this drone been detected by a seeker?
        self.caught = False  # Has this hider been caught?
        self.detection_time = None  # When was this drone first detected
        self.behavior_state = "idle"  # Current AI state: idle, patrol, search, chase, hide, flee
        self.last_target_update = 0.0  # Time of last target update (for AI behavior)
        
    def update(self, delta_time: float):
        """Update drone physics and movement."""
        if self.battery_level <= 0:
            return
            
        # Calculate desired movement
        direction = self.target_position - self.position
        distance = np.linalg.norm(direction)
        
        if distance < self.convergence_threshold:
            # Snap to target when close
            self.position = self.target_position.copy()
            self.velocity = np.zeros(3)
            self.settled = True
            return
            
        # Proportional control with speed limits
        direction_normalized = direction / distance if distance > 0 else np.zeros(3)
        desired_speed = min(self.max_speed, self.proportional_gain * distance)
        desired_velocity = direction_normalized * desired_speed
        
        # Apply acceleration constraints
        velocity_change = desired_velocity - self.velocity
        acceleration_magnitude = np.linalg.norm(velocity_change) / delta_time
        
        if acceleration_magnitude > self.max_acceleration:
            # Limit acceleration
            acceleration_direction = velocity_change / np.linalg.norm(velocity_change)
            max_velocity_change = acceleration_direction * self.max_acceleration * delta_time
            self.velocity += max_velocity_change
        else:
            self.velocity = desired_velocity
            
        # Update position
        self.position += self.velocity * delta_time
        
        # Update battery (simple drain based on movement)
        speed = np.linalg.norm(self.velocity)
        self.battery_level -= speed * 0.01 * delta_time
        self.battery_level = max(0, self.battery_level)
        
        self.settled = distance < self.convergence_threshold
        
    def set_target(self, target: np.ndarray):
        """Set new target position for the drone."""
        self.target_position = np.array(target, dtype=float)
        self.settled = False
        
    def get_state(self) -> dict:
        """Get current drone state for GUI updates."""
        return {
            'id': self.id,
            'position': self.position.tolist(),
            'velocity': self.velocity.tolist(),
            'target': self.target_position.tolist(),
            'color': self.color,
            'battery': self.battery_level,
            'settled': self.settled,
            'role': self.role,
            'detected': self.detected,
            'caught': self.caught,
            'behavior_state': self.behavior_state
        }