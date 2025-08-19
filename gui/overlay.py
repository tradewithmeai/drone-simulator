import pygame
import time
from OpenGL.GL import *

class TextOverlay:
    """Text overlay system for displaying HUD information."""
    
    def __init__(self, width, height, font_size=16, color=(255, 255, 255)):
        pygame.font.init()
        self.width = width
        self.height = height
        self.font = pygame.font.Font(None, font_size)
        self.color = color
        self.start_time = time.time()
        
        # Create surface for text rendering
        self.surface = pygame.Surface((width, height), pygame.SRCALPHA)
        
    def clear(self):
        """Clear the overlay surface."""
        self.surface.fill((0, 0, 0, 0))  # Transparent
        
    def draw_text(self, text, x, y, color=None):
        """Draw text at specified position."""
        if color is None:
            color = self.color
            
        text_surface = self.font.render(text, True, color)
        self.surface.blit(text_surface, (x, y))
        
    def draw_fps(self, fps, x=10, y=10):
        """Draw FPS counter."""
        self.draw_text(f"FPS: {fps:.1f}", x, y)
        
    def draw_sim_time(self, elapsed_time, x=10, y=30):
        """Draw simulation time."""
        sim_minutes = elapsed_time / 60.0
        self.draw_text(f"Sim Time: {sim_minutes:.1f}m", x, y)
        
    def draw_formation_type(self, formation, x=10, y=50):
        """Draw current formation type."""
        self.draw_text(f"Formation: {formation.title()}", x, y)
        
    def draw_drone_count(self, count, settled, x=10, y=70):
        """Draw drone status."""
        self.draw_text(f"Drones: {settled}/{count} settled", x, y)
        
    def draw_camera_info(self, camera, x=10, y=90):
        """Draw camera information."""
        pos = camera.position
        self.draw_text(f"Camera: ({pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f})", x, y)
        
    def draw_help_overlay(self):
        """Draw help overlay with all controls."""
        help_text = [
            "DRONE SWARM SIMULATOR - CONTROLS",
            "",
            "Camera:",
            "  WASD/QE - Move camera",
            "  Mouse drag - Rotate camera", 
            "  Mouse wheel - Zoom",
            "  R - Reset camera",
            "  1-9 - Lock camera to drone",
            "",
            "Formations:",
            "  1 - Line formation",
            "  2 - Circle formation",
            "  3 - Grid formation", 
            "  4 - V-formation",
            "  0 - Idle (no formation)",
            "",
            "Display:",
            "  T - Toggle targets",
            "  G - Toggle grid",
            "  X - Toggle axes",
            "  C - Toggle connections",
            "  L - Toggle drone labels",
            "  F - Toggle formation lines",
            "",
            "Simulation:",
            "  P - Pause/Resume",
            "  O - Step one tick (when paused)",
            "",
            "Other:",
            "  H - Toggle this help",
            "  ESC - Exit",
        ]
        
        # Semi-transparent background
        overlay_surf = pygame.Surface((400, 600), pygame.SRCALPHA)
        overlay_surf.fill((0, 0, 0, 180))
        self.surface.blit(overlay_surf, (self.width - 450, 50))
        
        # Draw help text
        y_offset = 70
        for line in help_text:
            if line == "DRONE SWARM SIMULATOR - CONTROLS":
                color = (255, 255, 0)  # Yellow for title
            elif line == "" or line.endswith(":"):
                color = (200, 200, 200)  # Light gray for headers
            else:
                color = (255, 255, 255)  # White for normal text
                
            self.draw_text(line, self.width - 440, y_offset, color)
            y_offset += 20
            
    def render_to_screen(self):
        """Render the overlay to the OpenGL context."""
        # Convert pygame surface to OpenGL texture (flip vertically for OpenGL)
        texture_data = pygame.image.tostring(self.surface, "RGBA", False)
        
        # Save current OpenGL state
        glPushAttrib(GL_ALL_ATTRIB_BITS)
        
        # Set up for 2D rendering
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        # Set up orthographic projection
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.width, self.height, 0, -1, 1)
        
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        # Create and bind texture
        texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self.width, self.height, 0, 
                     GL_RGBA, GL_UNSIGNED_BYTE, texture_data)
        
        # Draw textured quad
        glEnable(GL_TEXTURE_2D)
        glColor4f(1.0, 1.0, 1.0, 1.0)
        
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(0, 0)
        glTexCoord2f(1, 0); glVertex2f(self.width, 0)
        glTexCoord2f(1, 1); glVertex2f(self.width, self.height)
        glTexCoord2f(0, 1); glVertex2f(0, self.height)
        glEnd()
        
        # Clean up
        glDeleteTextures([texture_id])
        glDisable(GL_TEXTURE_2D)
        
        # Restore matrices
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        
        # Restore OpenGL state
        glPopAttrib()
        
    def resize(self, width, height):
        """Handle window resize."""
        self.width = width
        self.height = height
        self.surface = pygame.Surface((width, height), pygame.SRCALPHA)