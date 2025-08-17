import math
import numpy as np
from OpenGL.GL import *

class Camera:
    """3D Camera with WASD movement, mouse rotation, and scroll zoom."""
    
    def __init__(self, position=None, target=None):
        self.position = np.array(position or [0, 10, 20], dtype=float)
        self.target = np.array(target or [0, 0, 0], dtype=float)
        self.up = np.array([0, 1, 0], dtype=float)
        
        # Movement settings
        self.move_speed = 10.0
        self.rotation_speed = 0.005
        self.zoom_speed = 1.0
        
        # Mouse control
        self.mouse_sensitivity = 0.005
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        self.mouse_dragging = False
        
        # Spherical coordinates for orbiting
        self.distance = np.linalg.norm(self.position - self.target)
        self.theta = 0  # Horizontal angle
        self.phi = math.pi / 4  # Vertical angle
        
        self._update_position_from_spherical()
        
    def _update_position_from_spherical(self):
        """Update camera position based on spherical coordinates."""
        x = self.target[0] + self.distance * math.sin(self.phi) * math.cos(self.theta)
        y = self.target[1] + self.distance * math.cos(self.phi)
        z = self.target[2] + self.distance * math.sin(self.phi) * math.sin(self.theta)
        self.position = np.array([x, y, z])
        
    def handle_mouse_motion(self, dx, dy, dragging):
        """Handle mouse movement for camera rotation."""
        if dragging:
            self.theta += dx * self.mouse_sensitivity
            self.phi -= dy * self.mouse_sensitivity
            
            # Clamp phi to avoid flipping
            self.phi = max(0.1, min(math.pi - 0.1, self.phi))
            
            self._update_position_from_spherical()
            
    def handle_scroll(self, scroll_y):
        """Handle mouse scroll for zooming."""
        self.distance *= (1.0 - scroll_y * 0.1)
        self.distance = max(1.0, min(100.0, self.distance))
        self._update_position_from_spherical()
        
    def handle_keyboard(self, keys, dt):
        """Handle keyboard input for camera movement."""
        move_speed = self.move_speed * dt
        
        # Calculate camera vectors
        forward = self.target - self.position
        forward = forward / np.linalg.norm(forward)
        right = np.cross(forward, self.up)
        right = right / np.linalg.norm(right)
        
        # Movement
        movement = np.zeros(3)
        
        if keys.get('w', False):
            movement += forward * move_speed
        if keys.get('s', False):
            movement -= forward * move_speed
        if keys.get('a', False):
            movement -= right * move_speed
        if keys.get('d', False):
            movement += right * move_speed
        if keys.get('q', False):
            movement += self.up * move_speed
        if keys.get('e', False):
            movement -= self.up * move_speed
            
        # Apply movement to both position and target
        self.position += movement
        self.target += movement
        
        # Update spherical coordinates
        direction = self.position - self.target
        self.distance = np.linalg.norm(direction)
        if self.distance > 0:
            direction = direction / self.distance
            self.phi = math.acos(np.clip(direction[1], -1, 1))
            self.theta = math.atan2(direction[2], direction[0])
            
    def apply_view_matrix(self):
        """Apply the camera transformation to OpenGL."""
        gluLookAt(
            self.position[0], self.position[1], self.position[2],
            self.target[0], self.target[1], self.target[2],
            self.up[0], self.up[1], self.up[2]
        )