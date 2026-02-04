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
        
    def draw_all_drones(self, drone_states, size=0.5):
        """Draw all drones as quad-prop models with lighting enabled."""
        for drone_state in drone_states:
            position = drone_state['position']
            color = drone_state['color']
            settled = drone_state['settled']
            crashed = drone_state.get('crashed', False)
            orientation = drone_state.get('orientation', [0, 0, 0])
            self._draw_quad_drone(position, orientation, color, size, settled, crashed)

    def _draw_quad_drone(self, position, orientation, color, size, settled, crashed):
        """Draw a single drone as a quad-prop model with body, arms, motors, and direction."""
        scale = size * (0.7 if crashed else 1.0)

        # Color selection
        if crashed:
            r, g, b = color[0] * 0.3, color[1] * 0.3, color[2] * 0.3
        elif settled:
            r, g, b = min(1.0, color[0] * 1.2), min(1.0, color[1] * 1.2), min(1.0, color[2] * 1.2)
        else:
            r, g, b = color[0], color[1], color[2]

        roll, pitch, yaw = orientation

        glPushMatrix()
        glTranslatef(position[0], position[1], position[2])

        # Apply orientation (yaw, pitch, roll — applied in reverse order)
        glRotatef(math.degrees(yaw), 0, 1, 0)
        glRotatef(math.degrees(pitch), 1, 0, 0)
        glRotatef(math.degrees(roll), 0, 0, 1)

        # --- Body: flat box ---
        bx = scale * 0.35
        by = scale * 0.07
        bz = scale * 0.35
        glColor3f(r, g, b)
        glBegin(GL_QUADS)
        # Top
        glNormal3f(0, 1, 0)
        glVertex3f(-bx, by, -bz); glVertex3f(-bx, by, bz)
        glVertex3f(bx, by, bz); glVertex3f(bx, by, -bz)
        # Bottom
        glNormal3f(0, -1, 0)
        glVertex3f(-bx, -by, -bz); glVertex3f(bx, -by, -bz)
        glVertex3f(bx, -by, bz); glVertex3f(-bx, -by, bz)
        # Front (+Z)
        glNormal3f(0, 0, 1)
        glVertex3f(-bx, -by, bz); glVertex3f(bx, -by, bz)
        glVertex3f(bx, by, bz); glVertex3f(-bx, by, bz)
        # Back (-Z)
        glNormal3f(0, 0, -1)
        glVertex3f(-bx, -by, -bz); glVertex3f(-bx, by, -bz)
        glVertex3f(bx, by, -bz); glVertex3f(bx, -by, -bz)
        # Right (+X)
        glNormal3f(1, 0, 0)
        glVertex3f(bx, -by, -bz); glVertex3f(bx, by, -bz)
        glVertex3f(bx, by, bz); glVertex3f(bx, -by, bz)
        # Left (-X)
        glNormal3f(-1, 0, 0)
        glVertex3f(-bx, -by, -bz); glVertex3f(-bx, -by, bz)
        glVertex3f(-bx, by, bz); glVertex3f(-bx, by, -bz)
        glEnd()

        # --- Arms: 4 lines in X pattern (45 degree diagonals) ---
        arm_len = scale * 0.7
        arm_y = by  # arm height at top of body
        glDisable(GL_LIGHTING)
        glColor3f(r * 0.7, g * 0.7, b * 0.7)
        glLineWidth(3.0)
        glBegin(GL_LINES)
        for dx, dz in [(1, 1), (1, -1), (-1, -1), (-1, 1)]:
            glVertex3f(0, arm_y, 0)
            glVertex3f(dx * arm_len, arm_y, dz * arm_len)
        glEnd()

        # --- Motor discs at arm tips ---
        motor_r = scale * 0.12
        quadric = gluNewQuadric()
        glColor3f(min(1.0, r + 0.3), min(1.0, g + 0.3), min(1.0, b + 0.3))
        for dx, dz in [(1, 1), (1, -1), (-1, -1), (-1, 1)]:
            glPushMatrix()
            glTranslatef(dx * arm_len, arm_y + 0.01, dz * arm_len)
            glRotatef(-90, 1, 0, 0)  # face upward
            gluDisk(quadric, 0, motor_r, 12, 1)
            glPopMatrix()
        gluDeleteQuadric(quadric)

        # --- Direction indicator: bright line pointing forward (+Z local) ---
        glColor3f(1.0, 1.0, 1.0)  # white nose line
        glLineWidth(4.0)
        glBegin(GL_LINES)
        glVertex3f(0, by + 0.02, bz)
        glVertex3f(0, by + 0.02, bz + scale * 0.5)
        glEnd()
        # Small arrowhead
        glBegin(GL_TRIANGLES)
        arrow_tip = bz + scale * 0.55
        arrow_base = bz + scale * 0.4
        glVertex3f(0, by + 0.02, arrow_tip)
        glVertex3f(-scale * 0.08, by + 0.02, arrow_base)
        glVertex3f(scale * 0.08, by + 0.02, arrow_base)
        glEnd()

        glEnable(GL_LIGHTING)
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
        """Draw coordinate axes with labels."""
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

        # Draw axis labels at endpoints using small 3D line segments
        label_size = 0.6
        offset = length + 0.5

        glLineWidth(2.0)

        # X label (red) — draw "X" as two crossed lines
        glColor3f(1.0, 0.0, 0.0)
        glBegin(GL_LINES)
        glVertex3f(offset - label_size * 0.3, label_size * 0.3, 0)
        glVertex3f(offset + label_size * 0.3, -label_size * 0.3, 0)
        glVertex3f(offset - label_size * 0.3, -label_size * 0.3, 0)
        glVertex3f(offset + label_size * 0.3, label_size * 0.3, 0)
        glEnd()

        # Y label (green) — draw "Y" as V top + vertical stem
        glColor3f(0.0, 1.0, 0.0)
        glBegin(GL_LINES)
        glVertex3f(-label_size * 0.3, offset + label_size * 0.3, 0)
        glVertex3f(0, offset, 0)
        glVertex3f(label_size * 0.3, offset + label_size * 0.3, 0)
        glVertex3f(0, offset, 0)
        glVertex3f(0, offset, 0)
        glVertex3f(0, offset - label_size * 0.3, 0)
        glEnd()

        # Z label (blue) — draw "Z" as top + diagonal + bottom
        glColor3f(0.0, 0.0, 1.0)
        glBegin(GL_LINES)
        glVertex3f(0, label_size * 0.3, offset - label_size * 0.3)
        glVertex3f(0, label_size * 0.3, offset + label_size * 0.3)
        glVertex3f(0, label_size * 0.3, offset + label_size * 0.3)
        glVertex3f(0, -label_size * 0.3, offset - label_size * 0.3)
        glVertex3f(0, -label_size * 0.3, offset - label_size * 0.3)
        glVertex3f(0, -label_size * 0.3, offset + label_size * 0.3)
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

    def draw_all_obstacles(self, obstacle_states, highlight_idx=-1):
        """Draw all obstacles, optionally highlighting one."""
        for i, obs in enumerate(obstacle_states):
            if obs['type'] == 'box':
                self.draw_box(obs['position'], obs['size'], obs['color'])
            elif obs['type'] == 'cylinder':
                self.draw_cylinder(obs['position'], obs['radius'],
                                   obs['height'], obs['color'])
            # Highlight selected obstacle in delete mode
            if i == highlight_idx:
                self._draw_obstacle_highlight(obs)

    def _draw_obstacle_highlight(self, obs):
        """Draw bright wireframe outline around an obstacle."""
        glDisable(GL_LIGHTING)
        glColor3f(1.0, 1.0, 0.0)  # yellow highlight
        glLineWidth(2.0)

        if obs['type'] == 'box':
            pos = obs['position']
            size = obs['size']
            hx = size[0] / 2.0 + 0.1
            hy = size[1] / 2.0 + 0.1
            hz = size[2] / 2.0 + 0.1
            glPushMatrix()
            glTranslatef(pos[0], pos[1], pos[2])
            glBegin(GL_LINE_LOOP)
            glVertex3f(-hx, -hy, -hz); glVertex3f(hx, -hy, -hz)
            glVertex3f(hx, -hy, hz); glVertex3f(-hx, -hy, hz)
            glEnd()
            glBegin(GL_LINE_LOOP)
            glVertex3f(-hx, hy, -hz); glVertex3f(hx, hy, -hz)
            glVertex3f(hx, hy, hz); glVertex3f(-hx, hy, hz)
            glEnd()
            glBegin(GL_LINES)
            for x, z in [(-hx, -hz), (hx, -hz), (hx, hz), (-hx, hz)]:
                glVertex3f(x, -hy, z); glVertex3f(x, hy, z)
            glEnd()
            glPopMatrix()
        elif obs['type'] == 'cylinder':
            pos = obs['position']
            r = obs['radius'] + 0.1
            h = obs['height'] + 0.1
            glPushMatrix()
            glTranslatef(pos[0], pos[1], pos[2])
            for cy in [0, h]:
                glBegin(GL_LINE_LOOP)
                for j in range(24):
                    angle = 2.0 * math.pi * j / 24
                    glVertex3f(r * math.cos(angle), cy, r * math.sin(angle))
                glEnd()
            glBegin(GL_LINES)
            for j in range(0, 24, 6):
                angle = 2.0 * math.pi * j / 24
                x, z = r * math.cos(angle), r * math.sin(angle)
                glVertex3f(x, 0, z); glVertex3f(x, h, z)
            glEnd()
            glPopMatrix()

        glEnable(GL_LIGHTING)

    def draw_placement_cursor(self, cursor_xz, obstacle_type, size):
        """Draw a semi-transparent wireframe preview at the placement cursor."""
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        cx, cz = cursor_xz

        # Crosshair on ground
        glColor4f(0.0, 1.0, 0.0, 0.8)
        glLineWidth(2.0)
        glBegin(GL_LINES)
        glVertex3f(cx - 2, 0.01, cz); glVertex3f(cx + 2, 0.01, cz)
        glVertex3f(cx, 0.01, cz - 2); glVertex3f(cx, 0.01, cz + 2)
        glEnd()

        # Wireframe preview
        glColor4f(0.0, 1.0, 0.5, 0.5)
        glLineWidth(1.5)

        if obstacle_type == 'box':
            hx, hy, hz = size[0] / 2.0, size[1] / 2.0, size[2] / 2.0
            y_center = hy  # sitting on ground
            glPushMatrix()
            glTranslatef(cx, y_center, cz)
            glBegin(GL_LINE_LOOP)
            glVertex3f(-hx, -hy, -hz); glVertex3f(hx, -hy, -hz)
            glVertex3f(hx, -hy, hz); glVertex3f(-hx, -hy, hz)
            glEnd()
            glBegin(GL_LINE_LOOP)
            glVertex3f(-hx, hy, -hz); glVertex3f(hx, hy, -hz)
            glVertex3f(hx, hy, hz); glVertex3f(-hx, hy, hz)
            glEnd()
            glBegin(GL_LINES)
            for x, z in [(-hx, -hz), (hx, -hz), (hx, hz), (-hx, hz)]:
                glVertex3f(x, -hy, z); glVertex3f(x, hy, z)
            glEnd()
            glPopMatrix()
        elif obstacle_type == 'cylinder':
            radius, height = size[0], size[1]
            glPushMatrix()
            glTranslatef(cx, 0, cz)
            for cy in [0, height]:
                glBegin(GL_LINE_LOOP)
                for j in range(24):
                    angle = 2.0 * math.pi * j / 24
                    glVertex3f(radius * math.cos(angle), cy, radius * math.sin(angle))
                glEnd()
            glBegin(GL_LINES)
            for j in range(0, 24, 6):
                angle = 2.0 * math.pi * j / 24
                x, z = radius * math.cos(angle), radius * math.sin(angle)
                glVertex3f(x, 0, z); glVertex3f(x, height, z)
            glEnd()
            glPopMatrix()

        glDisable(GL_BLEND)
        glEnable(GL_LIGHTING)