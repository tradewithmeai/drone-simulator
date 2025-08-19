import math
import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *

class Renderer:
    """Optimized 3D renderer for drone swarm visualization with reduced GL state changes."""
    
    def __init__(self, width, height, background_color):
        self.width = width
        self.height = height
        self.background_color = background_color
        
        # OpenGL setup
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        
        # Set background color
        glClearColor(*background_color, 1.0)
        
        # Set up lighting
        light_pos = [10.0, 10.0, 10.0, 1.0]
        light_ambient = [0.3, 0.3, 0.3, 1.0]
        light_diffuse = [0.8, 0.8, 0.8, 1.0]
        
        glLightfv(GL_LIGHT0, GL_POSITION, light_pos)
        glLightfv(GL_LIGHT0, GL_AMBIENT, light_ambient)
        glLightfv(GL_LIGHT0, GL_DIFFUSE, light_diffuse)
        
        # Set up projection matrix
        self.setup_projection()
        
    def setup_projection(self):
        """Set up the projection matrix."""
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, self.width / self.height, 0.1, 1000.0)
        glMatrixMode(GL_MODELVIEW)
        
    def resize(self, width, height):
        """Handle window resize."""
        self.width = width
        self.height = height
        glViewport(0, 0, width, height)
        self.setup_projection()
        
    def clear(self):
        """Clear the screen."""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
    def begin_unlit_section(self):
        """Begin a section where lighting is disabled (optimize state changes)."""
        glDisable(GL_LIGHTING)
        
    def end_unlit_section(self):
        """End unlit section and re-enable lighting."""
        glEnable(GL_LIGHTING)
        
    def draw_all_drones(self, drone_states, size=0.5):
        """Draw all drones in a single batch with lighting enabled."""
        # Keep lighting enabled for all drones
        for drone_state in drone_states:
            position = drone_state['position']
            color = drone_state['color']
            settled = drone_state['settled']
            
            glPushMatrix()
            glTranslatef(position[0], position[1], position[2])
            
            # Set drone color
            if settled:
                # Brighter color when settled
                glColor3f(min(1.0, color[0] * 1.2), 
                         min(1.0, color[1] * 1.2), 
                         min(1.0, color[2] * 1.2))
            else:
                glColor3f(*color)
                
            # Create sphere
            sphere = gluNewQuadric()
            gluSphere(sphere, size, 16, 16)
            gluDeleteQuadric(sphere)
            
            glPopMatrix()
    
    def draw_all_targets(self, drone_states, size=0.2):
        """Draw all target positions in a single batch without lighting."""
        for drone_state in drone_states:
            position = drone_state['target']
            color = drone_state['color']
            
            glPushMatrix()
            glTranslatef(position[0], position[1], position[2])
            
            glColor3f(*color)
            glLineWidth(1.0)
            
            # Draw wireframe sphere
            sphere = gluNewQuadric()
            gluQuadricDrawStyle(sphere, GLU_LINE)
            gluSphere(sphere, size, 8, 8)
            gluDeleteQuadric(sphere)
            
            glPopMatrix()
        
    def draw_grid(self, size=50, spacing=5):
        """Draw a grid on the ground plane (unlit)."""
        glColor3f(0.3, 0.3, 0.3)
        glLineWidth(1.0)
        
        glBegin(GL_LINES)
        for i in range(-size//2, size//2 + 1, spacing):
            # Horizontal lines
            glVertex3f(-size//2, 0, i)
            glVertex3f(size//2, 0, i)
            # Vertical lines
            glVertex3f(i, 0, -size//2)
            glVertex3f(i, 0, size//2)
        glEnd()
        
    def draw_axes(self, length=10):
        """Draw coordinate axes (unlit)."""
        glLineWidth(3.0)
        
        glBegin(GL_LINES)
        # X axis (red)
        glColor3f(1.0, 0.0, 0.0)
        glVertex3f(0, 0, 0)
        glVertex3f(length, 0, 0)
        
        # Y axis (green)
        glColor3f(0.0, 1.0, 0.0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, length, 0)
        
        # Z axis (blue)
        glColor3f(0.0, 0.0, 1.0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, length)
        glEnd()
        
    def draw_formation_connections(self, drone_states, formation_type):
        """Draw lines connecting drones in formation (unlit)."""
        if formation_type == "line" or len(drone_states) < 2:
            return
            
        glColor3f(0.5, 0.5, 0.5)
        glLineWidth(1.0)
        
        positions = [drone['position'] for drone in drone_states]
        
        if formation_type == "circle":
            # Connect adjacent drones in circle
            glBegin(GL_LINE_LOOP)
            for pos in positions:
                glVertex3f(pos[0], pos[1], pos[2])
            glEnd()
            
        elif formation_type == "v_formation":
            # Connect to lead drone
            if len(positions) > 0:
                lead_pos = positions[0]
                glBegin(GL_LINES)
                for pos in positions[1:]:
                    glVertex3f(lead_pos[0], lead_pos[1], lead_pos[2])
                    glVertex3f(pos[0], pos[1], pos[2])
                glEnd()
                
        elif formation_type == "grid":
            # Connect drones in grid pattern
            grid_size = int(len(drone_states) ** 0.5)
            if grid_size * grid_size == len(drone_states):
                glBegin(GL_LINES)
                for i in range(len(positions)):
                    row, col = divmod(i, grid_size)
                    
                    # Connect to right neighbor
                    if col < grid_size - 1:
                        right_idx = i + 1
                        if right_idx < len(positions):
                            glVertex3f(positions[i][0], positions[i][1], positions[i][2])
                            glVertex3f(positions[right_idx][0], positions[right_idx][1], positions[right_idx][2])
                    
                    # Connect to bottom neighbor
                    if row < grid_size - 1:
                        bottom_idx = i + grid_size
                        if bottom_idx < len(positions):
                            glVertex3f(positions[i][0], positions[i][1], positions[i][2])
                            glVertex3f(positions[bottom_idx][0], positions[bottom_idx][1], positions[bottom_idx][2])
                glEnd()
    
    def draw_all_labels(self, drone_states, camera_pos):
        """Draw all drone labels in a batch (unlit, no depth test)."""
        glDisable(GL_DEPTH_TEST)
        
        # Get matrices once for all labels
        modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
        projection = glGetDoublev(GL_PROJECTION_MATRIX)
        viewport = glGetIntegerv(GL_VIEWPORT)
        
        # Set up 2D projection once
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, viewport[2], viewport[3], 0, -1, 1)
        
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        for drone_state in drone_states:
            position = drone_state['position']
            drone_id = drone_state['id']
            color = drone_state['color']
            
            # Calculate label position
            label_offset = np.array([0, 1.0, 0])  # 1 meter above drone
            label_pos = np.array(position) + label_offset
            
            try:
                from OpenGL.GLU import gluProject
                screen_x, screen_y, screen_z = gluProject(
                    label_pos[0], label_pos[1], label_pos[2],
                    modelview, projection, viewport
                )
                
                # Only draw if in front of camera
                if 0 < screen_z < 1:
                    glColor3f(*color)
                    glLineWidth(2.0)
                    # Draw drone ID number as simple lines
                    self._draw_number(int(drone_id), screen_x, screen_y)
                    
            except Exception:
                pass  # Skip label if projection fails
        
        # Restore matrices once
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        
        glEnable(GL_DEPTH_TEST)
        
    def _draw_number(self, num, x, y):
        """Draw a simple number at screen position."""
        # Basic number rendering with line segments
        # Simplified for performance
        digit_str = str(num)
        offset = 0
        
        for digit_char in digit_str:
            digit = int(digit_char)
            
            # Draw simplified digit (just a few lines)
            glBegin(GL_LINES)
            if digit == 0:
                # Draw O shape
                glVertex2f(x + offset, y)
                glVertex2f(x + offset + 5, y)
                glVertex2f(x + offset, y)
                glVertex2f(x + offset, y + 10)
                glVertex2f(x + offset + 5, y)
                glVertex2f(x + offset + 5, y + 10)
                glVertex2f(x + offset, y + 10)
                glVertex2f(x + offset + 5, y + 10)
            elif digit == 1:
                # Draw vertical line
                glVertex2f(x + offset + 2, y)
                glVertex2f(x + offset + 2, y + 10)
            # Add more digits as needed
            glEnd()
            
            offset += 8  # Space between digits