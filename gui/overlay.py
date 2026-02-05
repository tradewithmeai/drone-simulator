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
        
        # Allocate persistent texture to avoid recreation each frame
        self._texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self._texture_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        # Pre-allocate texture storage
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self.width, self.height, 0, 
                     GL_RGBA, GL_UNSIGNED_BYTE, None)
        
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
            "  Home - Frame swarm (center on drones)",
            "  6-9 - Lock camera to drone",
            "",
            "Formations:",
            "  1 - Line    2 - Circle",
            "  3 - Grid    4 - V-formation",
            "  0 - Idle (no formation)",
            "",
            "Spawning:",
            "  Shift+1-5 - Respawn in preset",
            "  (Line, Circle, Grid, V, Random)",
            "",
            "Display:",
            "  T - Targets   G - Grid",
            "  X - Axes      L - Labels",
            "  C/F - Formation connections",
            "",
            "FPV Mode:",
            "  V - Toggle first-person view",
            "  WASD - Fly drone  Mouse - Yaw",
            "  ESC - Exit FPV",
            "",
            "Placement Mode:",
            "  J - Toggle placement mode",
            "  Arrows - Move cursor on ground",
            "  B - Cycle type (box/cylinder)",
            "  +/- - Resize    Enter - Place",
            "  Shift+J - Delete mode",
            "  Left/Right - Select obstacle",
            "  Del - Remove selected obstacle",
            "",
            "Simulation:",
            "  P - Pause/Resume",
            "  O - Step one tick (when paused)",
            "",
            "  H - Toggle this help  ESC - Exit",
        ]
        
        # Semi-transparent background
        overlay_surf = pygame.Surface((400, len(help_text) * 20 + 40), pygame.SRCALPHA)
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
        """Render the overlay to the OpenGL context using persistent texture."""
        # Convert pygame surface to OpenGL texture data
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
        
        # Bind and update persistent texture (do not recreate)
        glBindTexture(GL_TEXTURE_2D, self._texture_id)
        # Update texture data without reallocating
        glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, self.width, self.height,
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
        
        # Clean up (do NOT delete texture - it's persistent)
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
        
        # Reallocate texture for new size
        if hasattr(self, '_texture_id'):
            glDeleteTextures([self._texture_id])
            self._texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self._texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self.width, self.height, 0, 
                        GL_RGBA, GL_UNSIGNED_BYTE, None)
    
    def __del__(self):
        """Clean up persistent texture on deletion."""
        if hasattr(self, '_texture_id'):
            try:
                glDeleteTextures([self._texture_id])
            except:
                pass  # OpenGL context might already be destroyed