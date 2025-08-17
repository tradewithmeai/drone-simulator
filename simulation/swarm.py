import numpy as np
from typing import List, Dict, Any
import math
from .drone import Drone

class Swarm:
    """Manages multiple drones and formation control."""
    
    def __init__(self, num_drones: int, drone_colors: List[List[float]], spacing: float = 3.0):
        self.spacing = spacing
        self.drones = []
        
        # Initialize drones in a grid pattern
        grid_size = int(math.ceil(math.sqrt(num_drones)))
        for i in range(num_drones):
            row = i // grid_size
            col = i % grid_size
            x = (col - grid_size/2) * 2
            y = 0
            z = (row - grid_size/2) * 2
            
            color = drone_colors[i % len(drone_colors)]
            drone = Drone(i, [x, y, z], color)
            self.drones.append(drone)
            
        self.current_formation = "idle"
        
    def update(self, delta_time: float):
        """Update all drones in the swarm."""
        for drone in self.drones:
            drone.update(delta_time)
            
    def set_formation(self, formation_type: str):
        """Set the formation pattern for the swarm."""
        self.current_formation = formation_type
        
        if formation_type == "line":
            self._form_line()
        elif formation_type == "circle":
            self._form_circle()
        elif formation_type == "grid":
            self._form_grid()
        elif formation_type == "v_formation":
            self._form_v()
        elif formation_type == "idle":
            # Keep current positions
            pass
            
    def _form_line(self):
        """Arrange drones in a line formation."""
        center_x = 0
        for i, drone in enumerate(self.drones):
            x = center_x + (i - len(self.drones)/2) * self.spacing
            drone.set_target([x, 5, 0])
            
    def _form_circle(self):
        """Arrange drones in a circle formation."""
        if len(self.drones) == 1:
            self.drones[0].set_target([0, 5, 0])
            return
            
        radius = self.spacing / (2 * math.sin(math.pi / len(self.drones)))
        
        for i, drone in enumerate(self.drones):
            angle = 2 * math.pi * i / len(self.drones)
            x = radius * math.cos(angle)
            z = radius * math.sin(angle)
            drone.set_target([x, 5, z])
            
    def _form_grid(self):
        """Arrange drones in a square grid."""
        grid_size = int(math.ceil(math.sqrt(len(self.drones))))
        
        for i, drone in enumerate(self.drones):
            row = i // grid_size
            col = i % grid_size
            x = (col - grid_size/2) * self.spacing
            z = (row - grid_size/2) * self.spacing
            drone.set_target([x, 5, z])
            
    def _form_v(self):
        """Arrange drones in a V formation."""
        if len(self.drones) % 2 == 0:
            # Even number - use grid formation instead
            self._form_grid()
            return
            
        # Lead drone at center
        self.drones[0].set_target([0, 5, 0])
        
        # Wing drones
        wing_angle = math.radians(40)  # 40 degrees
        
        for i in range(1, len(self.drones)):
            wing_side = 1 if i % 2 == 1 else -1  # Alternate sides
            wing_position = (i + 1) // 2  # Position along wing
            
            x = wing_side * wing_position * self.spacing * math.sin(wing_angle)
            z = -wing_position * self.spacing * math.cos(wing_angle)
            
            self.drones[i].set_target([x, 5, z])
            
    def get_states(self) -> List[Dict[str, Any]]:
        """Get current state of all drones."""
        return [drone.get_state() for drone in self.drones]
        
    def is_formation_complete(self) -> bool:
        """Check if formation is complete (90% of drones settled)."""
        settled_count = sum(1 for drone in self.drones if drone.settled)
        return settled_count >= len(self.drones) * 0.9
        
    def get_formation_progress(self) -> float:
        """Get formation completion progress (0.0 to 1.0)."""
        settled_count = sum(1 for drone in self.drones if drone.settled)
        return settled_count / len(self.drones)