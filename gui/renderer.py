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
        
    def draw_drone(self, position, color, size=0.5, settled=False):
        """Draw a single drone as a colored sphere."""
        glPushMatrix()
        glTranslatef(position[0], position[1], position[2])
        
        # Set drone color
        if settled:
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
                
        glEnable(GL_LIGHTING)