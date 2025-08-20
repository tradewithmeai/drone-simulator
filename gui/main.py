import pygame
import sys
import yaml
import time
import threading
from OpenGL.GL import *
from OpenGL.GLU import *

from gui.camera import Camera
try:
    from gui.renderer_optimized import Renderer
except ImportError:
    from gui.renderer import Renderer  # Fallback to original
from gui.overlay import TextOverlay
from simulation.simulator import Simulator

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
        pygame.display.set_mode((self.width, self.height), pygame.DOUBLEBUF | pygame.OPENGL | pygame.RESIZABLE)
        pygame.display.set_caption("Drone Swarm 3D Simulator")
        
        # Initialize components
        smooth_camera = self.gui_config.get('smooth_camera', True)
        smoothing_factor = self.gui_config.get('camera_smoothing', 0.1)
        self.camera = Camera([15, 15, 15], [0, 5, 0], smooth_camera, smoothing_factor)
        self.renderer = Renderer(self.width, self.height, self.background_color)
        # Convert HUD color from 0-1 range to 0-255 range for pygame
        hud_color_01 = self.gui_config.get('hud_color', [1.0, 1.0, 1.0])
        hud_color_255 = tuple(int(c * 255) for c in hud_color_01)
        self.overlay = TextOverlay(self.width, self.height, 
                                 self.gui_config.get('hud_font_size', 16),
                                 hud_color_255)
        
        # Initialize simulation
        self.simulator = Simulator(config_path)
        self.simulator.set_state_callback(self.on_simulation_update)
        
        # Store up_axis for camera framing
        self.up_axis = self.gui_config.get('up_axis', 'y')
        
        # GUI state
        self.running = True
        self.paused = False
        self.show_targets = True
        self.show_grid = True
        self.show_axes = True
        self.show_connections = self.gui_config.get('show_formation_lines', True)
        self.show_labels = self.gui_config.get('show_labels', False)
        self.show_fps = self.gui_config.get('show_fps', True)
        self.show_sim_time = self.gui_config.get('show_sim_time', True)
        self.show_formation_type = self.gui_config.get('show_formation_type', True)
        self.show_help = self.gui_config.get('show_help', False)
        self.enable_overlay = self.gui_config.get('enable_overlay', True)
        
        # Input state
        self.keys_pressed = {}
        self.mouse_dragging = False
        self.last_mouse_pos = (0, 0)
        
        # Current drone states
        self.drone_states = []
        self.sim_info = {}
        
        # Timing
        self.clock = pygame.time.Clock()
        self.start_time = time.time()
        self.frame_count = 0
        self.fps = 0.0
        self.last_fps_update = time.time()
        
        # Auto-spawn flag
        self.auto_spawn_triggered = False
        
        # Diagnostic logging
        self.last_diagnostic_log = time.time()
        self.diagnostic_interval = 5.0  # Log every 5 seconds
        
        # Watchdog for monitoring simulation thread
        self._watchdog_next = time.time() + 1.0
        
        # CRITICAL: Start simulator thread immediately after initialization
        self._ensure_simulator_started()
        
    def on_simulation_update(self, drone_states, sim_info):
        """Callback for receiving simulation updates."""
        self.drone_states = drone_states
        self.sim_info = sim_info
    
    def _ensure_simulator_started(self):
        """Ensure simulator thread is started - can be called multiple times safely."""
        print("[GUI] Ensuring simulator thread is started...")
        if not self.simulator.is_alive():
            print("[GUI] Starting simulator thread...")
            self.simulator.start()
            
            # Verify thread actually started
            import time
            time.sleep(0.1)  # Give thread time to start
            
            if self.simulator.is_alive():
                print(f"[GUI] SUCCESS: Simulator thread started (id={self.simulator._thread.ident})")
            else:
                print("[GUI] ERROR: Simulator thread failed to start!")
                raise RuntimeError("Simulator thread startup failed")
        else:
            print("[GUI] SUCCESS: Simulator thread already running")

    def _watchdog_tick(self):
        """Monitor simulation thread health - log every second."""
        if time.time() < self._watchdog_next:
            return
        self._watchdog_next = time.time() + 1.0
        
        alive = self.simulator.is_alive()
        last = self.simulator.last_tick_time()
        age = time.time() - last if last else -1
        queue_size = self.simulator.queue_size()
        
        print(f"[WATCHDOG] sim_alive={alive} last_tick_age={age:0.2f}s queue_size={queue_size}")
        
        # Update camera with drone states for locking
        self.camera.set_drone_states(self.drone_states)
        
    def handle_events(self):
        """Handle pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                
            elif event.type == pygame.KEYDOWN:
                key_name = pygame.key.name(event.key)
                self.keys_pressed[key_name] = True
                
                # Check for Shift modifier
                shift_pressed = bool(event.mod & pygame.KMOD_SHIFT)
                self.handle_key_press(key_name, shift_pressed)
                
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
                self.overlay.resize(self.width, self.height)
                
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 3:  # Right mouse button
                    # Future: implement drone selection
                    pass
                
    def handle_key_press(self, key, shift_pressed=False):
        """Handle specific key presses."""
        if key == 'escape' or key == 'q':
            print("\n[EXIT] User requested exit, shutting down...")
            self.running = False
        elif key == 'p':  # P for pause (instead of space)
            self.paused = not self.paused
            if self.paused:
                self.simulator.pause()
            else:
                self.simulator.resume()
        elif key == 'o':  # O for step simulation
            if self.paused:
                self.simulator.step_simulation()
        elif key == 'h':  # H for help
            self.show_help = not self.show_help
        elif key == 'f9':  # F9 for thread diagnostics
            print("===== THREAD DIAGNOSTICS (F9) =====")
            print(f"Simulator alive: {self.simulator.is_alive()}")
            last = self.simulator.last_tick_time()
            age = time.time() - last if last else -1
            print(f"Last tick age: {age:0.2f}s")
            print(f"Queue size: {self.simulator.queue_size()}")
            print(f"Drones: {len(self.drone_states)}")
            print("=====================================")
        elif key == 'r':
            # Reset camera
            smooth_camera = self.gui_config.get('smooth_camera', True)
            smoothing_factor = self.gui_config.get('camera_smoothing', 0.1)
            self.camera = Camera([15, 15, 15], [0, 5, 0], smooth_camera, smoothing_factor)
        elif key == 'home':
            # Frame swarm - center camera on all drones
            self.frame_swarm()
        elif key == 't':
            self.show_targets = not self.show_targets
        elif key == 'g':
            self.show_grid = not self.show_grid
        elif key == 'x':
            self.show_axes = not self.show_axes
        elif key == 'c':
            self.show_connections = not self.show_connections
        elif key == 'l':  # L for labels
            self.show_labels = not self.show_labels
        elif key == 'f':  # F for formation lines
            self.show_connections = not self.show_connections
        elif key == '1':
            if shift_pressed:
                print("[GUI] Enqueue RESPAWN line")
                self.simulator.respawn_formation('line')
            else:
                self.simulator.set_formation('line')
        elif key == '2':
            if shift_pressed:
                print("Shift+2 pressed - requesting circle formation spawn")
                self.simulator.respawn_formation('circle')
            else:
                self.simulator.set_formation('circle')
        elif key == '3':
            if shift_pressed:
                print("Shift+3 pressed - requesting grid formation spawn")
                self.simulator.respawn_formation('grid')
            else:
                self.simulator.set_formation('grid')
        elif key == '4':
            if shift_pressed:
                print("Shift+4 pressed - requesting v formation spawn")
                self.simulator.respawn_formation('v')
            else:
                self.simulator.set_formation('v_formation')
        elif key == '5':
            if shift_pressed:
                print("Shift+5 pressed - requesting random formation spawn")
                self.simulator.respawn_formation('random')
        elif key == '0':
            self.simulator.set_formation('idle')
        # Drone locking (6-9 keys for drone IDs, avoiding conflict with formation keys)
        elif key in '6789':
            drone_id = int(key) - 1
            if drone_id < len(self.drone_states):
                if self.camera.locked_drone_id == drone_id:
                    self.camera.unlock_camera()
                else:
                    self.camera.lock_to_drone(drone_id)
            
    def render(self):
        """Render the 3D scene."""
        # Clear screen
        self.renderer.clear()
        
        # Apply camera
        self.camera.apply_view_matrix()
        
        # Batch render unlit elements (grid, axes, connections, targets)
        if hasattr(self.renderer, 'begin_unlit_section'):
            # Using optimized renderer with batched state changes
            self.renderer.begin_unlit_section()
            
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
                
            # Draw all targets
            if self.show_targets:
                self.renderer.draw_all_targets(self.drone_states)
                
            self.renderer.end_unlit_section()
            
            # Draw all drones with lighting enabled (batched)
            if self.drone_states:
                self.renderer.draw_all_drones(self.drone_states, self.config['drones']['size'])
            
            # Draw all labels (batched, no depth test)
            if self.show_labels and self.drone_states:
                self.renderer.begin_unlit_section()
                self.renderer.draw_all_labels(self.drone_states, self.camera.position)
                self.renderer.end_unlit_section()
        else:
            # Fallback to original renderer
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
                size = self.config['drones']['size']
                drone_id = drone_state['id']
                
                self.renderer.draw_drone(position, color, size, settled)
                
                # Draw target position
                if self.show_targets:
                    target = drone_state['target']
                    self.renderer.draw_target(target, color)
                    
                # Draw drone labels
                if self.show_labels:
                    self.renderer.draw_drone_label(position, drone_id, color, self.camera.position)
                
        # Draw overlays with error handling
        if self.enable_overlay:
            try:
                self.draw_overlays()
            except Exception as e:
                print(f"[OVERLAY-OFF] HUD crashed, disabling overlay: {e}")
                self.enable_overlay = False
                
        # Swap buffers
        pygame.display.flip()
        
    def update(self):
        """Update the GUI state."""
        dt = self.clock.tick(60) / 1000.0  # Convert to seconds
        
        # Update FPS counter
        self.frame_count += 1
        current_time = time.time()
        if current_time - self.last_fps_update >= 1.0:  # Update every second
            self.fps = self.frame_count / (current_time - self.last_fps_update)
            self.frame_count = 0
            self.last_fps_update = current_time
        
        # Handle camera movement and smooth interpolation
        self.camera.handle_keyboard(self.keys_pressed, dt)
        self.camera.update_smooth_movement(dt)
        
        # Diagnostic logging every N seconds
        current_time = time.time()
        if current_time - self.last_diagnostic_log >= self.diagnostic_interval:
            self.last_diagnostic_log = current_time
            self._log_diagnostics()
        
                        
    def _log_diagnostics(self):
        """Log diagnostic information for debugging."""
        print(f"[DIAGNOSTIC] Time: {time.time() - self.start_time:.1f}s | "
              f"FPS: {self.fps:.1f} | "
              f"Drones: {len(self.drone_states)} | "
              f"Camera: ({self.camera.position[0]:.1f}, {self.camera.position[1]:.1f}, {self.camera.position[2]:.1f}) | "
              f"Overlay: {self.enable_overlay} | "
              f"Formation: {self.sim_info.get('current_formation', 'none')}")
        
        # Log any critical issues
        if self.fps < 10 and self.fps > 0:
            print(f"[WARNING] Low FPS detected: {self.fps:.1f}")
        if not self.drone_states:
            print("[WARNING] No drone states received")
        if not self.enable_overlay:
            print("[INFO] Overlay disabled (likely due to error)")
    
    def frame_swarm(self):
        """Frame camera to show all drones."""
        if not self.drone_states:
            print("No drones to frame")
            return
            
        # Import coordinate utilities
        from simulation.coords import get_bounding_box, calculate_camera_distance
        
        # Get drone positions
        positions = [state['position'] for state in self.drone_states]
        
        # Calculate bounding box and centroid
        min_pos, max_pos, centroid = get_bounding_box(positions)
        distance = calculate_camera_distance(min_pos, max_pos, 20.0)
        
        print(f"Framing swarm: centroid={centroid}, distance={distance:.1f}")
        
        # Update camera to look at centroid from appropriate distance
        # Position camera at distance from centroid
        cam_offset = [distance * 0.6, distance * 0.6, distance * 0.6]
        new_camera_pos = [
            centroid[0] + cam_offset[0],
            centroid[1] + cam_offset[1], 
            centroid[2] + cam_offset[2]
        ]
        
        # Update camera position and target
        smooth_camera = self.gui_config.get('smooth_camera', True)
        smoothing_factor = self.gui_config.get('camera_smoothing', 0.1)
        self.camera = Camera(new_camera_pos, centroid, smooth_camera, smoothing_factor)
        
    def draw_overlays(self):
        """Draw all GUI overlays."""
        self.overlay.clear()
        
        # Draw FPS counter
        if self.show_fps:
            self.overlay.draw_fps(self.fps)
            
        # Draw simulation time
        if self.show_sim_time:
            elapsed = time.time() - self.start_time
            self.overlay.draw_sim_time(elapsed)
            
        # Draw formation type and spawn preset
        if self.show_formation_type:
            formation = self.sim_info.get('current_formation', 'idle')
            spawn_preset = self.sim_info.get('spawn_preset', 'unknown')
            self.overlay.draw_formation_type(formation)
            self.overlay.draw_text(f"Spawn: {spawn_preset}", 10, 90, self.overlay.color)
            
        # Draw drone count and status
        if self.drone_states:
            settled_count = sum(1 for drone in self.drone_states if drone['settled'])
            self.overlay.draw_drone_count(len(self.drone_states), settled_count)
        else:
            # Show "No drones" if none exist
            self.overlay.draw_text("Drones: 0", 10, 110, self.overlay.color)
            
        # Draw up-axis info
        self.overlay.draw_text(f"Up-axis: {self.up_axis.upper()}", 10, 130, self.overlay.color)
            
        # Draw camera info if locked to drone
        if self.camera.locked_drone_id is not None:
            self.overlay.draw_text(f"Camera locked to Drone {self.camera.locked_drone_id}", 10, 150, (255, 255, 0))
            
        # Draw pause indicator
        if self.paused:
            self.overlay.draw_text("PAUSED - Press P to resume, O to step", 10, 170, (255, 255, 0))
            
        # Draw help overlay
        if self.show_help:
            self.overlay.draw_help_overlay()
            
        # Render overlay to screen
        self.overlay.render_to_screen()
        
    def run(self):
        """Main GUI loop."""
        print("[DEBUG] GUI run() method called")
        print("Starting Drone Swarm 3D GUI...")
        print("[DEBUG] About to print controls...")
        print("Controls:")
        print("  WASD/QE - Move camera")
        print("  Mouse drag - Rotate camera")
        print("  Mouse wheel - Zoom")
        print("  1-4 - Formation patterns (Line, Circle, Grid, V)")
        print("  5 - (unused)")
        print("  0 - Idle formation")
        print("  Shift+1-5 - Respawn in preset formations (Line, Circle, Grid, V, Random)")
        print("  P - Pause/Resume")
        print("  O - Step simulation (when paused)")
        print("  H - Toggle help overlay")
        print("  T - Toggle targets")
        print("  G - Toggle grid")
        print("  X - Toggle axes")
        print("  C/F - Toggle formation connections")
        print("  L - Toggle drone labels")
        print("  R - Reset camera")
        print("  Home - Frame swarm (center camera on all drones)")
        print("  6-9 (hold) - Lock camera to drone")
        print("  ESC/Q - Exit application")
        print("")
        print("GUI Enhancements:")
        print("  - FPS counter and simulation time display")
        print("  - Drone ID labels above each drone")
        print("  - Enhanced formation visualization")
        print("  - Smooth camera interpolation")
        print("  - Interactive pause/step controls")
        print("  - Comprehensive help overlay (press H)")
        
        print("[DEBUG] Controls printed, about to start simulation...")
        
        # CRITICAL: Guarantee simulation thread starts BEFORE GUI loop
        self._ensure_simulator_started()
        
        print("[DEBUG] About to enter main GUI loop...")
        
        try:
            while self.running:
                self.handle_events()
                
                # Monitor simulation thread health
                self._watchdog_tick()
                
                self.update()  # Always update to maintain frame timing
                self.render()
                
        finally:
            # Clean up
            print("[EXIT] Stopping simulation...")
            if hasattr(self, 'simulator') and self.simulator:
                self.simulator.stop()
            print("[EXIT] Cleaning up GUI resources...")
            try:
                pygame.quit()
            except:
                pass  # Ignore pygame cleanup errors
            print("[EXIT] Shutdown complete.")

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