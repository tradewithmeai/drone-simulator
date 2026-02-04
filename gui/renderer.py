import math
import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *

class Renderer:
    """3D renderer for drone swarm visualization."""
    
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
        
    def draw_drone(self, position, color, size=0.5, settled=False, crashed=False):
        """Draw a single drone as a colored sphere."""
        glPushMatrix()
        glTranslatef(position[0], position[1], position[2])

        # Set drone color
        if crashed:
            # Darkened color for crashed drones
            glColor3f(color[0] * 0.3, color[1] * 0.3, color[2] * 0.3)
            size = size * 0.7
        elif settled:
            # Brighter color when settled
            glColor3f(min(1.0, color[0] * 1.2), min(1.0, color[1] * 1.2), min(1.0, color[2] * 1.2))
        else:
            glColor3f(*color)
            
        # Create sphere
        sphere = gluNewQuadric()
        gluSphere(sphere, size, 16, 16)
        gluDeleteQuadric(sphere)
        
        glPopMatrix()
        
    def draw_drone_trail(self, positions, color):
        """Draw trail behind drone (optional feature)."""
        if len(positions) < 2:
            return
            
        glDisable(GL_LIGHTING)
        glColor3f(*color)
        glLineWidth(2.0)
        
        glBegin(GL_LINE_STRIP)
        for pos in positions:
            glVertex3f(pos[0], pos[1], pos[2])
        glEnd()
        
        glEnable(GL_LIGHTING)
        
    def draw_target(self, position, color, size=0.2):
        """Draw target position as a wireframe sphere."""
        glPushMatrix()
        glTranslatef(position[0], position[1], position[2])
        
        glDisable(GL_LIGHTING)
        glColor3f(*color)
        glLineWidth(1.0)
        
        # Draw wireframe sphere
        sphere = gluNewQuadric()
        gluQuadricDrawStyle(sphere, GLU_LINE)
        gluSphere(sphere, size, 8, 8)
        gluDeleteQuadric(sphere)
        
        glEnable(GL_LIGHTING)
        glPopMatrix()
        
    def draw_grid(self, size=50, spacing=5):
        """Draw a grid on the ground plane."""
        glDisable(GL_LIGHTING)
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
        
        glEnable(GL_LIGHTING)
        
    def draw_axes(self, length=10):
        """Draw coordinate axes."""
        glDisable(GL_LIGHTING)
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
        
        glEnable(GL_LIGHTING)
        
    def draw_formation_connections(self, drone_states, formation_type):
        """Draw lines connecting drones in formation."""
        if formation_type == "line" or len(drone_states) < 2:
            return
            
        glDisable(GL_LIGHTING)
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
                
        glEnable(GL_LIGHTING)
        
    def draw_drone_label(self, position, drone_id, color, camera_pos):
        """Draw drone ID label above the drone."""
        # Calculate billboard position (always face camera)
        label_offset = np.array([0, 1.0, 0])  # 1 meter above drone
        label_pos = np.array(position) + label_offset
        
        # Switch to 2D rendering for text
        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)
        
        # Project 3D position to screen coordinates
        modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
        projection = glGetDoublev(GL_PROJECTION_MATRIX)
        viewport = glGetIntegerv(GL_VIEWPORT)
        
        try:
            from OpenGL.GLU import gluProject
            screen_x, screen_y, screen_z = gluProject(
                label_pos[0], label_pos[1], label_pos[2],
                modelview, projection, viewport
            )
            
            # Only draw if in front of camera
            if 0 < screen_z < 1:
                # Set up 2D projection
                glMatrixMode(GL_PROJECTION)
                glPushMatrix()
                glLoadIdentity()
                glOrtho(0, viewport[2], viewport[3], 0, -1, 1)
                
                glMatrixMode(GL_MODELVIEW)
                glPushMatrix()
                glLoadIdentity()
                
                # Draw simple text as lines (basic implementation)
                glColor3f(*color)
                glLineWidth(2.0)
                
                # Draw drone ID number as simple lines
                self._draw_number(int(drone_id), screen_x, screen_y)
                
                # Restore matrices
                glPopMatrix()
                glMatrixMode(GL_PROJECTION)
                glPopMatrix()
                glMatrixMode(GL_MODELVIEW)
                
        except ImportError:
            # Fallback if gluProject not available
            pass
            
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        
    def _draw_number(self, number, x, y):
        """Draw a number using simple line segments."""
        # Very basic number drawing - just draw the number as lines
        # This is a simplified implementation
        digit_width = 8
        digit_height = 12
        
        str_num = str(number)
        start_x = x - (len(str_num) * digit_width) // 2
        
        for i, digit in enumerate(str_num):
            digit_x = start_x + i * digit_width
            self._draw_digit(int(digit), digit_x, y, digit_width, digit_height)
            
    def _draw_digit(self, digit, x, y, width, height):
        """Draw a single digit using line segments."""
        # Simple 7-segment display style digits
        segments = {
            0: [(0,0,1,0), (1,0,1,1), (1,1,0,1), (0,1,0,0), (0,0,0,1), (1,0,1,1)],
            1: [(1,0,1,1)],
            2: [(0,0,1,0), (1,0,1,0.5), (0,0.5,1,0.5), (0,0.5,0,1), (0,1,1,1)],
            3: [(0,0,1,0), (1,0,1,0.5), (0,0.5,1,0.5), (1,0.5,1,1), (0,1,1,1)],
            4: [(0,0,0,0.5), (0,0.5,1,0.5), (1,0,1,1)],
            5: [(0,0,1,0), (0,0,0,0.5), (0,0.5,1,0.5), (1,0.5,1,1), (0,1,1,1)],
            6: [(0,0,1,0), (0,0,0,1), (0,0.5,1,0.5), (1,0.5,1,1), (0,1,1,1)],
            7: [(0,0,1,0), (1,0,1,1)],
            8: [(0,0,1,0), (1,0,1,1), (1,1,0,1), (0,1,0,0), (0,0.5,1,0.5)],
            9: [(0,0,1,0), (1,0,1,0.5), (0,0.5,1,0.5), (0,0,0,0.5), (1,0.5,1,1), (0,1,1,1)]
        }
        
        if digit in segments:
            glBegin(GL_LINES)
            for seg in segments[digit]:
                x1, y1, x2, y2 = seg
                glVertex2f(x + x1 * width, y + y1 * height)
                glVertex2f(x + x2 * width, y + y2 * height)
            glEnd()

    def draw_box(self, position, size, color):
        """Draw an axis-aligned box. Position is center, size is full extents."""
        glPushMatrix()
        glTranslatef(position[0], position[1], position[2])
        glColor3f(*color)

        hx, hy, hz = size[0] / 2.0, size[1] / 2.0, size[2] / 2.0

        glBegin(GL_QUADS)
        # Front (+Z)
        glNormal3f(0, 0, 1)
        glVertex3f(-hx, -hy, hz); glVertex3f(hx, -hy, hz)
        glVertex3f(hx, hy, hz);   glVertex3f(-hx, hy, hz)
        # Back (-Z)
        glNormal3f(0, 0, -1)
        glVertex3f(-hx, -hy, -hz); glVertex3f(-hx, hy, -hz)
        glVertex3f(hx, hy, -hz);   glVertex3f(hx, -hy, -hz)
        # Top (+Y)
        glNormal3f(0, 1, 0)
        glVertex3f(-hx, hy, -hz); glVertex3f(-hx, hy, hz)
        glVertex3f(hx, hy, hz);   glVertex3f(hx, hy, -hz)
        # Bottom (-Y)
        glNormal3f(0, -1, 0)
        glVertex3f(-hx, -hy, -hz); glVertex3f(hx, -hy, -hz)
        glVertex3f(hx, -hy, hz);   glVertex3f(-hx, -hy, hz)
        # Right (+X)
        glNormal3f(1, 0, 0)
        glVertex3f(hx, -hy, -hz); glVertex3f(hx, hy, -hz)
        glVertex3f(hx, hy, hz);   glVertex3f(hx, -hy, hz)
        # Left (-X)
        glNormal3f(-1, 0, 0)
        glVertex3f(-hx, -hy, -hz); glVertex3f(-hx, -hy, hz)
        glVertex3f(-hx, hy, hz);   glVertex3f(-hx, hy, -hz)
        glEnd()

        glPopMatrix()

    def draw_cylinder(self, position, radius, height, color):
        """Draw a vertical cylinder. Position is base center."""
        glPushMatrix()
        glTranslatef(position[0], position[1], position[2])
        # gluCylinder draws along Z; rotate so it goes along +Y
        glRotatef(-90, 1, 0, 0)
        glColor3f(*color)

        quadric = gluNewQuadric()
        gluQuadricNormals(quadric, GLU_SMOOTH)
        gluCylinder(quadric, radius, radius, height, 24, 1)
        # Top cap
        glPushMatrix()
        glTranslatef(0, 0, height)
        gluDisk(quadric, 0, radius, 24, 1)
        glPopMatrix()
        # Bottom cap
        glPushMatrix()
        glRotatef(180, 1, 0, 0)
        gluDisk(quadric, 0, radius, 24, 1)
        glPopMatrix()
        gluDeleteQuadric(quadric)

        glPopMatrix()

    def draw_all_obstacles(self, obstacle_states):
        """Draw all obstacles."""
        for obs in obstacle_states:
            if obs['type'] == 'box':
                self.draw_box(obs['position'], obs['size'], obs['color'])
            elif obs['type'] == 'cylinder':
                self.draw_cylinder(obs['position'], obs['radius'],
                                   obs['height'], obs['color'])