import math
import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *

class Camera:
    """3D Camera with WASD movement, mouse rotation, and scroll zoom."""
    
    def __init__(self, position=None, target=None, smooth_interpolation=True, smoothing_factor=0.1):
        self.position = np.array(position or [0, 10, 20], dtype=float)
        self.target = np.array(target or [0, 0, 0], dtype=float)
        self.up = np.array([0, 1, 0], dtype=float)
        
        # Smooth camera movement
        self.smooth_interpolation = smooth_interpolation
        self.smoothing_factor = smoothing_factor
        self.target_position = self.position.copy()
        self.target_target = self.target.copy()
        
        # Drone locking
        self.locked_drone_id = None
        self.drone_states = []
        
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
        self.theta = math.pi / 2  # Horizontal angle (start looking from +Z toward origin)
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
        forward_norm = np.linalg.norm(forward)
        if forward_norm > 0:
            forward = forward / forward_norm
        else:
            forward = np.array([0, 0, -1])  # Default forward direction
            
        right = np.cross(forward, self.up)
        right_norm = np.linalg.norm(right)
        if right_norm > 0:
            right = right / right_norm
        else:
            right = np.array([1, 0, 0])  # Default right direction
        
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
            
    def set_drone_states(self, drone_states):
        """Update drone states for camera locking."""
        self.drone_states = drone_states
        
    def lock_to_drone(self, drone_id):
        """Lock camera to follow a specific drone."""
        if drone_id is None:
            self.locked_drone_id = None
            return
            
        # Check if drone exists
        if any(drone['id'] == drone_id for drone in self.drone_states):
            self.locked_drone_id = drone_id
        else:
            self.locked_drone_id = None
            
    def unlock_camera(self):
        """Unlock camera from drone following."""
        self.locked_drone_id = None
        
    def update_smooth_movement(self, dt):
        """Update smooth camera interpolation."""
        if not self.smooth_interpolation:
            return
            
        # Handle drone locking
        if self.locked_drone_id is not None:
            locked_drone = next((drone for drone in self.drone_states 
                               if drone['id'] == self.locked_drone_id), None)
            if locked_drone:
                drone_pos = np.array(locked_drone['position'])
                # Set target to drone position with slight offset
                self.target_target = drone_pos
                # Keep camera at relative position
                offset = self.position - self.target
                self.target_position = drone_pos + offset
                
        # Smooth interpolation
        self.position += (self.target_position - self.position) * self.smoothing_factor
        self.target += (self.target_target - self.target) * self.smoothing_factor
        
        # Update spherical coordinates based on current position
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

    @staticmethod
    def get_fpv_view(drone_state):
        """Compute FPV camera parameters from drone state.

        Args:
            drone_state: Dict with 'position' and 'orientation' keys.

        Returns:
            (eye, center, up) tuple for gluLookAt.
        """
        pos = np.array(drone_state['position'])
        yaw = drone_state['orientation'][2]  # [roll, pitch, yaw]

        forward = np.array([math.sin(yaw), 0.0, math.cos(yaw)])
        eye = pos + np.array([0.0, 0.5, 0.0]) + forward * 1.5  # above and in front
        center = eye + forward * 5.0
        up = np.array([0.0, 1.0, 0.0])
        return eye, center, up

    @staticmethod
    def apply_fpv_view(drone_state):
        """Apply FPV camera directly to OpenGL."""
        eye, center, up = Camera.get_fpv_view(drone_state)
        gluLookAt(
            eye[0], eye[1], eye[2],
            center[0], center[1], center[2],
            up[0], up[1], up[2],
        )