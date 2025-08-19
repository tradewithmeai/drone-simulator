import numpy as np
from typing import List, Dict, Any
import math
from simulation.drone import Drone
from simulation.spawn import make_positions
from simulation.coords import map_positions_list

class Swarm:
    """Manages multiple drones and formation control."""
    
    def __init__(self, num_drones: int, drone_colors: List[List[float]], spacing: float = 3.0, 
                 spawn_preset: str = "grid", spawn_altitude: float = 5.0, seed: int = 42, up_axis: str = "y"):
        self.spacing = spacing
        self.spawn_preset = spawn_preset
        self.spawn_altitude = spawn_altitude
        self.spawn_seed = seed
        self.up_axis = up_axis
        self.drone_colors = drone_colors
        self.drones = []
        
        # Create initial drones using spawn positions (only if num_drones > 0)
        if num_drones > 0:
            self._create_drones(num_drones)
            
        self.current_formation = "idle"
        
    def _create_drones(self, num_drones: int):
        """Create drones at spawn positions with coordinate mapping."""
        # Generate spawn positions
        positions = make_positions(num_drones, self.spawn_preset, self.spacing, self.spawn_altitude, self.spawn_seed)
        
        # Apply coordinate mapping based on up_axis
        mapped_positions = map_positions_list(positions, self.up_axis)
        
        # Create drones at mapped positions
        for i in range(num_drones):
            position = mapped_positions[i] if i < len(mapped_positions) else [0, self.spawn_altitude, 0]
            color = self.drone_colors[i % len(self.drone_colors)]
            drone = Drone(i, position, color)
            # Set both position and target to spawned location
            drone.target_position = np.array(position, dtype=float) 
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
    
    def respawn_formation(self, preset: str, num_drones: int = None, spacing: float = None, 
                         altitude: float = None, seed: int = None, up_axis: str = None):
        """Respawn drones in a new formation preset with coordinate mapping and validation.
        
        Args:
            preset: Formation preset ('v', 'line', 'circle', 'grid', 'random')
            num_drones: Number of drones (None to keep current count)
            spacing: Inter-drone spacing (None to keep current)
            altitude: Spawn altitude (None to keep current)
            seed: Random seed (None to keep current)
            up_axis: Coordinate system up-axis (None to keep current)
            
        Raises:
            ValueError: If parameters are invalid
            RuntimeError: If respawn operation fails
        """
        if num_drones is None:
            num_drones = len(self.drones)
        
        # Validate parameters
        if num_drones <= 0:
            raise ValueError(f"Invalid drone count: {num_drones} (must be positive)")
        if num_drones > 50:
            raise ValueError(f"Drone count too large: {num_drones} (maximum 50 for stability)")
            
        if spacing is not None and spacing <= 0:
            raise ValueError(f"Invalid spacing: {spacing} (must be positive)")
        if up_axis is not None and up_axis not in ['x', 'y', 'z']:
            raise ValueError(f"Invalid up_axis: '{up_axis}' (must be 'x', 'y', or 'z')")
            
        valid_presets = ['v', 'line', 'circle', 'grid', 'random']
        if preset not in valid_presets:
            raise ValueError(f"Invalid preset: '{preset}' (must be one of {valid_presets})")
        
        try:
            # Update spawn settings if provided
            if spacing is not None:
                self.spacing = spacing
            if altitude is not None:
                self.spawn_altitude = altitude
            if seed is not None:
                self.spawn_seed = seed
            if up_axis is not None:
                self.up_axis = up_axis
            
            # Clear existing drones safely
            old_count = len(self.drones)
            self.drones.clear()
            
            # Update spawn preset
            self.spawn_preset = preset
            
            # Create new drones at mapped spawn positions
            self._create_drones(num_drones)
            
            # Keep formation as idle initially (drones spawn at target positions)
            self.current_formation = "idle"
            
            print(f"Respawned {num_drones} drones in '{preset}' formation (replaced {old_count}, up_axis: {self.up_axis})")
            
        except Exception as e:
            # Restore a minimal working state on failure
            self.drones.clear()
            self.current_formation = "idle"
            raise RuntimeError(f"Respawn failed, swarm cleared: {e}") from e
    
    def auto_spawn(self, count: int, preset: str, spacing: float, altitude: float, seed: int, up_axis: str):
        """Auto-spawn drones at startup with full configuration and validation.
        
        Args:
            count: Number of drones to spawn
            preset: Formation preset
            spacing: Inter-drone spacing
            altitude: Spawn altitude
            seed: Random seed
            up_axis: Coordinate system up-axis
            
        Raises:
            ValueError: If parameters are invalid
            RuntimeError: If spawn operation fails
        """
        # Validate input parameters
        if count <= 0:
            raise ValueError(f"Invalid drone count: {count} (must be positive)")
        if count > 50:
            raise ValueError(f"Drone count too large: {count} (maximum 50 for stability)")
        if spacing <= 0:
            raise ValueError(f"Invalid spacing: {spacing} (must be positive)")
        if not isinstance(preset, str) or not preset.strip():
            raise ValueError(f"Invalid preset: '{preset}' (must be non-empty string)")
        if up_axis not in ['x', 'y', 'z']:
            raise ValueError(f"Invalid up_axis: '{up_axis}' (must be 'x', 'y', or 'z')")
            
        valid_presets = ['v', 'line', 'circle', 'grid', 'random']
        if preset not in valid_presets:
            raise ValueError(f"Invalid preset: '{preset}' (must be one of {valid_presets})")
            
        print(f"Auto-spawning {count} drones in '{preset}' formation...")
        try:
            self.respawn_formation(preset, count, spacing, altitude, seed, up_axis)
            print(f"Auto-spawn validation passed: {count} drones created successfully")
        except Exception as e:
            raise RuntimeError(f"Auto-spawn failed: {e}") from e