import numpy as np
from typing import List, Dict, Any
import math
from simulation.drone import Drone
from simulation.spawn import make_positions

class Swarm:
    """Manages multiple drones and formation control."""
    
    def __init__(self, num_drones: int, drone_colors: List[List[float]], spacing: float = 3.0, 
                 spawn_preset: str = "grid", spawn_altitude: float = 5.0, seed: int = 42):
        self.spacing = spacing
        self.spawn_preset = spawn_preset
        self.spawn_altitude = spawn_altitude
        self.spawn_seed = seed
        self.drone_colors = drone_colors
        self.drones = []
        
        # Create initial drones using spawn positions
        self._create_drones(num_drones)
            
        self.current_formation = "idle"
        
    def _create_drones(self, num_drones: int):
        """Create drones at spawn positions."""
        positions = make_positions(num_drones, self.spawn_preset, self.spacing, self.spawn_altitude, self.spawn_seed)
        
        for i in range(num_drones):
            position = positions[i] if i < len(positions) else [0, self.spawn_altitude, 0]
            color = self.drone_colors[i % len(self.drone_colors)]
            drone = Drone(i, position, color)
            self.drones.append(drone)
        
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
    
    def respawn_formation(self, preset: str, num_drones: int = None):
        """Respawn drones in a new formation preset.
        
        Args:
            preset: Formation preset ('v', 'line', 'circle', 'grid', 'random')
            num_drones: Number of drones (None to keep current count)
        """
        if num_drones is None:
            num_drones = len(self.drones)
        
        # Store current formation state to avoid interruption
        old_formation = self.current_formation
        
        # Clear existing drones
        self.drones.clear()
        
        # Update spawn settings
        self.spawn_preset = preset
        
        # Create new drones at spawn positions
        self._create_drones(num_drones)
        
        # Keep formation as idle initially (drones spawn at target positions)
        self.current_formation = "idle"
        
        print(f"Respawned {num_drones} drones in '{preset}' formation")