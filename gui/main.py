import pygame
import sys
import yaml
from OpenGL.GL import *
from OpenGL.GLU import *

from .camera import Camera
from .renderer import Renderer
from ..simulation.simulator import Simulator

class DroneSwarmGUI:
    """Main GUI class for 3D drone swarm visualization."""
    
    def __init__(self, config_path="config.yaml"):
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
            
        self.gui_config = self.config['gui']
        self.width = self.gui_config['window_width']
        self.height = self.gui_config['window_height']
        self.background_color = self.gui_config['background_color']
        
        # Initialize pygame and OpenGL
        pygame.init()
        pygame.display.set_mode((self.width, self.height), pygame.DOUBLEBUF | pygame.OPENGL)
        pygame.display.set_caption("Drone Swarm 3D Simulator")
        
        # Initialize components
        self.camera = Camera([15, 15, 15], [0, 5, 0])
        self.renderer = Renderer(self.width, self.height, self.background_color)
        
        # Initialize simulation
        self.simulator = Simulator(config_path)
        self.simulator.set_state_callback(self.on_simulation_update)
        
        # GUI state
        self.running = True
        self.paused = False
        self.show_targets = True
        self.show_grid = True
        self.show_axes = True
        self.show_connections = True
        
        # Input state
        self.keys_pressed = {}
        self.mouse_dragging = False
        self.last_mouse_pos = (0, 0)
        
        # Current drone states
        self.drone_states = []
        self.sim_info = {}
        
        # Clock for timing
        self.clock = pygame.time.Clock()
        
    def on_simulation_update(self, drone_states, sim_info):
        """Callback for receiving simulation updates."""
        self.drone_states = drone_states
        self.sim_info = sim_info
        
    def handle_events(self):
        """Handle pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                
            elif event.type == pygame.KEYDOWN:
                self.keys_pressed[pygame.key.name(event.key)] = True
                self.handle_key_press(pygame.key.name(event.key))
                
            elif event.type == pygame.KEYUP:
                self.keys_pressed[pygame.key.name(event.key)] = False
                
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button
                    self.mouse_dragging = True
                    self.last_mouse_pos = pygame.mouse.get_pos()
                    
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.mouse_dragging = False
                    
            elif event.type == pygame.MOUSEMOTION:
                if self.mouse_dragging:
                    current_pos = pygame.mouse.get_pos()
                    dx = current_pos[0] - self.last_mouse_pos[0]
                    dy = current_pos[1] - self.last_mouse_pos[1]
                    self.camera.handle_mouse_motion(dx, dy, True)
                    self.last_mouse_pos = current_pos
                    
            elif event.type == pygame.MOUSEWHEEL:
                self.camera.handle_scroll(event.y)
                
            elif event.type == pygame.VIDEORESIZE:
                self.width = event.w
                self.height = event.h
                self.renderer.resize(self.width, self.height)
                
    def handle_key_press(self, key):
        """Handle specific key presses."""
        if key == 'escape':
            self.running = False
        elif key == 'space':
            self.paused = not self.paused
            if self.paused:
                self.simulator.pause()
            else:
                self.simulator.resume()
        elif key == 'r':
            # Reset camera
            self.camera = Camera([15, 15, 15], [0, 5, 0])
        elif key == 't':
            self.show_targets = not self.show_targets
        elif key == 'g':
            self.show_grid = not self.show_grid
        elif key == 'x':
            self.show_axes = not self.show_axes
        elif key == 'c':
            self.show_connections = not self.show_connections
        elif key == '1':
            self.simulator.set_formation('line')
        elif key == '2':
            self.simulator.set_formation('circle')
        elif key == '3':
            self.simulator.set_formation('grid')
        elif key == '4':
            self.simulator.set_formation('v_formation')
        elif key == '0':
            self.simulator.set_formation('idle')
            
    def render(self):
        """Render the 3D scene."""
        # Clear screen
        self.renderer.clear()
        
        # Apply camera
        self.camera.apply_view_matrix()
        
        # Draw grid and axes
        if self.show_grid:
            self.renderer.draw_grid()
        if self.show_axes:
            self.renderer.draw_axes()
            
        # Draw formation connections
        if self.show_connections and self.sim_info.get('current_formation') != 'idle':
            self.renderer.draw_formation_connections(
                self.drone_states, 
                self.sim_info.get('current_formation', '')
            )
            
        # Draw drones
        for drone_state in self.drone_states:
            position = drone_state['position']
            color = drone_state['color']
            settled = drone_state['settled']
            size = self.config['drone']['size']
            
            self.renderer.draw_drone(position, color, size, settled)
            
            # Draw target position
            if self.show_targets:
                target = drone_state['target']
                self.renderer.draw_target(target, color)
                
        # Swap buffers
        pygame.display.flip()
        
    def update(self):
        """Update the GUI state."""
        dt = self.clock.tick(60) / 1000.0  # Convert to seconds
        
        # Handle camera movement
        self.camera.handle_keyboard(self.keys_pressed, dt)
        
    def draw_hud(self):
        """Draw heads-up display with information (optional)."""
        # Note: For simplicity, we're not implementing text rendering here
        # In a full implementation, you could use pygame fonts or OpenGL text rendering
        pass
        
    def run(self):
        """Main GUI loop."""
        print("Starting Drone Swarm 3D GUI...")
        print("Controls:")
        print("  WASD/QE - Move camera")
        print("  Mouse drag - Rotate camera")
        print("  Mouse wheel - Zoom")
        print("  1-4 - Formation patterns (Line, Circle, Grid, V)")
        print("  0 - Idle formation")
        print("  Space - Pause/Resume")
        print("  T - Toggle targets")
        print("  G - Toggle grid")
        print("  X - Toggle axes")
        print("  C - Toggle connections")
        print("  R - Reset camera")
        print("  ESC - Exit")
        
        # Start simulation
        self.simulator.start()
        
        try:
            while self.running:
                self.handle_events()
                self.update()
                self.render()
                
        finally:
            # Clean up
            self.simulator.stop()
            pygame.quit()

def main():
    """Entry point for the GUI application."""
    try:
        gui = DroneSwarmGUI()
        gui.run()
    except Exception as e:
        print(f"Error starting GUI: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()