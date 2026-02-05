import pygame
import sys
import yaml
import time
import threading
import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *

from gui.camera import Camera
try:
    from gui.renderer_optimized import Renderer
except ImportError:
    from gui.renderer import Renderer  # Fallback to original
from gui.overlay import TextOverlay
from gui.gamepad import GamepadManager
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

        # Obstacle state
        self.show_obstacles = True
        self.obstacle_type = 'box'  # current placement type: 'box' or 'cylinder'
        self.obstacle_states = []
        
        # Timing
        self.clock = pygame.time.Clock()
        self.start_time = time.time()
        self.frame_count = 0
        self.fps = 0.0
        self.last_fps_update = time.time()
        
        # Gamepad controller
        gamepad_config = self.config.get('gamepad', {})
        self.gamepad = GamepadManager(gamepad_config)
        self._formation_cycle_index = 0
        self._formation_list = ['line', 'circle', 'grid', 'v_formation', 'idle']

        # Placement mode state
        self.placement_mode = False
        self.placement_delete_mode = False
        self.placement_cursor = [0.0, 0.0]  # X, Z on ground
        self.placement_type = 'box'  # 'box' or 'cylinder'
        self.placement_box_size = [4.0, 4.0, 4.0]
        self.placement_cyl_size = [2.0, 8.0]  # radius, height
        self.placement_selected_idx = -1
        self.placement_cursor_speed = 2.0

        # FPV mode state
        self.fpv_mode = False
        self.fpv_drone_id = None
        self.fpv_yaw_accumulator = 0.0  # accumulated yaw from mouse input
        self.fpv_speed = self.gui_config.get('fpv_speed', 5.0)
        self.fpv_yaw_rate = self.gui_config.get('fpv_yaw_rate', 2.0)

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
        self.obstacle_states = sim_info.get('obstacles', [])
    
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
                if self.fpv_mode:
                    # In FPV: mouse X controls yaw
                    dx = event.rel[0]
                    self.fpv_yaw_accumulator -= dx * 0.003
                elif self.mouse_dragging:
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

            elif event.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
                self.gamepad.check_hotplug(time.time(), force=True)
                
    def handle_key_press(self, key, shift_pressed=False):
        """Handle specific key presses."""
        if key == 'v':
            self._toggle_fpv()
            return
        # J key: toggle placement mode
        if key == 'j' and not self.fpv_mode:
            if shift_pressed and self.placement_mode:
                # Shift+J: toggle delete sub-mode
                self.placement_delete_mode = not self.placement_delete_mode
                if self.placement_delete_mode:
                    self.placement_selected_idx = 0 if self.obstacle_states else -1
                    print("[PLACEMENT] Delete mode ON — Left/Right to select, Del to remove")
                else:
                    self.placement_selected_idx = -1
                    print("[PLACEMENT] Delete mode OFF")
            else:
                self.placement_mode = not self.placement_mode
                self.placement_delete_mode = False
                self.placement_selected_idx = -1
                if self.placement_mode:
                    print("[PLACEMENT] Placement mode ON — Arrows=Move  B=Type  Enter=Place  J=Exit")
                else:
                    print("[PLACEMENT] Placement mode OFF")
            return

        # In placement mode, handle placement-specific keys (but let H through for help)
        if self.placement_mode and key != 'h':
            self._handle_placement_key(key, shift_pressed)
            return

        # In FPV mode, only process ESC (other keys used for flight control)
        if self.fpv_mode and key != 'escape':
            return
        if key == 'escape':
            if self.fpv_mode:
                self._exit_fpv()
                return
            print("\n[EXIT] User requested exit, shutting down...")
            self.running = False
            return
        if key == 'q' and not self.fpv_mode:
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
        # Obstacle controls
        elif key == 'b':
            self.obstacle_type = 'cylinder' if self.obstacle_type == 'box' else 'box'
            print(f"[GUI] Obstacle type: {self.obstacle_type}")
        elif key == 'n':
            target = list(self.camera.target)
            if self.obstacle_type == 'box':
                self.simulator.add_box_obstacle(target, [4.0, 4.0, 4.0])
                print(f"[GUI] Placed box at {target}")
            else:
                self.simulator.add_cylinder_obstacle(target, 2.0, 8.0)
                print(f"[GUI] Placed cylinder at {target}")
        elif key == 'm':
            if shift_pressed:
                self.simulator.clear_all_obstacles()
                print("[GUI] Cleared all obstacles")
            else:
                self.simulator.remove_last_obstacle()
                print("[GUI] Removed last obstacle")
        elif key == 'k':
            self.show_obstacles = not self.show_obstacles
            
    def render(self):
        """Render the 3D scene."""
        # Clear screen
        self.renderer.clear()

        # Apply camera (FPV or orbit)
        if self.fpv_mode:
            drone_state = self._get_fpv_drone_state()
            if drone_state:
                from gui.camera import Camera
                Camera.apply_fpv_view(drone_state)
            else:
                self.camera.apply_view_matrix()
        else:
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
                self.renderer.draw_all_drones(self.drone_states, self.config['drones']['size'], self.camera.locked_drone_id)

            # Draw obstacles (lit) with optional highlight
            if self.show_obstacles and self.obstacle_states:
                highlight = self.placement_selected_idx if self.placement_delete_mode else -1
                self.renderer.draw_all_obstacles(self.obstacle_states, highlight)

            # Draw placement cursor
            if self.placement_mode and not self.placement_delete_mode:
                if self.placement_type == 'box':
                    cursor_size = self.placement_box_size
                else:
                    cursor_size = self.placement_cyl_size
                self.renderer.draw_placement_cursor(
                    self.placement_cursor, self.placement_type, cursor_size)

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
                
            # Draw drones (batched quad-prop model)
            if self.drone_states:
                self.renderer.draw_all_drones(self.drone_states, self.config['drones']['size'], self.camera.locked_drone_id)

            # Draw targets
            for drone_state in self.drone_states:
                if self.show_targets:
                    target = drone_state['target']
                    color = drone_state['color']
                    self.renderer.draw_target(target, color)

                # Draw drone labels
                if self.show_labels:
                    position = drone_state['position']
                    drone_id = drone_state['id']
                    color = drone_state['color']
                    self.renderer.draw_drone_label(position, drone_id, color, self.camera.position)

            # Draw obstacles (fallback renderer)
            if self.show_obstacles and self.obstacle_states:
                highlight = self.placement_selected_idx if self.placement_delete_mode else -1
                self.renderer.draw_all_obstacles(self.obstacle_states, highlight)

            # Draw placement cursor
            if self.placement_mode and not self.placement_delete_mode:
                if self.placement_type == 'box':
                    cursor_size = self.placement_box_size
                else:
                    cursor_size = self.placement_cyl_size
                self.renderer.draw_placement_cursor(
                    self.placement_cursor, self.placement_type, cursor_size)

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
        
        # Poll gamepad
        self.gamepad.poll(time.time())

        # FPV mode: send velocity commands based on keyboard + gamepad input
        if self.fpv_mode:
            self._update_fpv_input()
        else:
            # Normal camera movement and smooth interpolation
            self.camera.handle_keyboard(self.keys_pressed, dt)
            self.camera.update_smooth_movement(dt)

        # Gamepad continuous input (sticks, triggers)
        if self.gamepad.connected:
            self._process_gamepad_buttons()
            if not self.fpv_mode:
                if self.placement_mode:
                    self._update_gamepad_placement(dt)
                else:
                    self._update_gamepad_normal(dt)
        
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
        
    def _handle_placement_key(self, key, shift_pressed):
        """Handle keys while in placement mode."""
        speed = self.placement_cursor_speed

        if self.placement_delete_mode:
            # Delete sub-mode: scroll and remove
            if key == 'right' and self.obstacle_states:
                self.placement_selected_idx = (self.placement_selected_idx + 1) % len(self.obstacle_states)
            elif key == 'left' and self.obstacle_states:
                self.placement_selected_idx = (self.placement_selected_idx - 1) % len(self.obstacle_states)
            elif key in ('delete', 'backspace') and 0 <= self.placement_selected_idx < len(self.obstacle_states):
                print(f"[PLACEMENT] Removing obstacle {self.placement_selected_idx}")
                self.simulator.remove_obstacle_by_index(self.placement_selected_idx)
                if self.placement_selected_idx >= len(self.obstacle_states) - 1:
                    self.placement_selected_idx = max(0, len(self.obstacle_states) - 2)
            elif key == 'escape':
                self.placement_delete_mode = False
                self.placement_selected_idx = -1
            return

        # Normal placement mode (cursor[0]=X, cursor[1]=Z)
        if key == 'up':
            self.placement_cursor[1] += speed  # +Z = away from default camera
        elif key == 'down':
            self.placement_cursor[1] -= speed
        elif key == 'left':
            self.placement_cursor[0] += speed
        elif key == 'right':
            self.placement_cursor[0] -= speed
        elif key == 'b':
            self.placement_type = 'cylinder' if self.placement_type == 'box' else 'box'
            print(f"[PLACEMENT] Type: {self.placement_type}")
        elif key == 'return':
            cx, cz = self.placement_cursor
            if self.placement_type == 'box':
                sz = self.placement_box_size
                pos = [cx, sz[1] / 2.0, cz]  # center Y at half height
                self.simulator.add_box_obstacle(pos, sz)
                print(f"[PLACEMENT] Placed box at ({cx:.1f}, {cz:.1f})")
            else:
                r, h = self.placement_cyl_size
                pos = [cx, 0.0, cz]  # base on ground
                self.simulator.add_cylinder_obstacle(pos, r, h)
                print(f"[PLACEMENT] Placed cylinder at ({cx:.1f}, {cz:.1f})")
        elif key in ('=', 'plus', ']'):  # increase size
            if self.placement_type == 'box':
                self.placement_box_size = [s + 1.0 for s in self.placement_box_size]
                print(f"[PLACEMENT] Box size: {self.placement_box_size}")
            else:
                self.placement_cyl_size[0] += 0.5
                self.placement_cyl_size[1] += 2.0
                print(f"[PLACEMENT] Cylinder: r={self.placement_cyl_size[0]:.1f} h={self.placement_cyl_size[1]:.1f}")
        elif key in ('-', 'minus', '['):  # decrease size
            if self.placement_type == 'box':
                self.placement_box_size = [max(1.0, s - 1.0) for s in self.placement_box_size]
                print(f"[PLACEMENT] Box size: {self.placement_box_size}")
            else:
                self.placement_cyl_size[0] = max(0.5, self.placement_cyl_size[0] - 0.5)
                self.placement_cyl_size[1] = max(2.0, self.placement_cyl_size[1] - 2.0)
                print(f"[PLACEMENT] Cylinder: r={self.placement_cyl_size[0]:.1f} h={self.placement_cyl_size[1]:.1f}")
        elif key == 'escape':
            self.placement_mode = False
            self.placement_delete_mode = False
            print("[PLACEMENT] Placement mode OFF")

    def _toggle_fpv(self):
        """Toggle FPV mode on the currently locked drone."""
        if self.fpv_mode:
            self._exit_fpv()
            return

        # Need a locked drone to enter FPV
        if self.camera.locked_drone_id is None:
            print("[FPV] Lock camera to a drone first (keys 6-9), then press V")
            return

        drone_id = self.camera.locked_drone_id
        # Verify drone exists
        drone_state = next((d for d in self.drone_states if d['id'] == drone_id), None)
        if drone_state is None:
            print(f"[FPV] Drone {drone_id} not found")
            return

        self.fpv_mode = True
        self.fpv_drone_id = drone_id
        self.fpv_yaw_accumulator = drone_state['orientation'][2]
        pygame.event.set_grab(True)
        pygame.mouse.set_visible(False)
        print(f"[FPV] Entered FPV mode on Drone {drone_id} — WASD to fly, Mouse to look, V/ESC to exit")

    def _exit_fpv(self):
        """Exit FPV mode and return drone to position hold."""
        if not self.fpv_mode:
            return
        print(f"[FPV] Exiting FPV mode on Drone {self.fpv_drone_id}")
        self.simulator.set_drone_position_hold(self.fpv_drone_id)
        self.fpv_mode = False
        self.fpv_drone_id = None
        pygame.event.set_grab(False)
        pygame.mouse.set_visible(True)

    def _update_fpv_input(self):
        """Process keyboard input and send velocity commands in FPV mode."""
        import math
        drone_state = self._get_fpv_drone_state()
        if drone_state is None:
            self._exit_fpv()
            return

        yaw = self.fpv_yaw_accumulator
        speed = self.fpv_speed

        # Forward/back and strafe relative to drone yaw
        forward = 0.0
        strafe = 0.0
        vertical = 0.0

        if self.keys_pressed.get('w', False):
            forward += 1.0
        if self.keys_pressed.get('s', False):
            forward -= 1.0
        if self.keys_pressed.get('d', False):
            strafe -= 1.0
        if self.keys_pressed.get('a', False):
            strafe += 1.0
        if self.keys_pressed.get('e', False):
            vertical += 1.0
        if self.keys_pressed.get('q', False):
            vertical -= 1.0

        # Add gamepad contribution
        if self.gamepad.connected:
            gp = self.gamepad
            forward += -gp.left_stick[1]   # stick Y inverted (up = -1)
            strafe += -gp.left_stick[0]
            vertical += gp.right_trigger - gp.left_trigger
            dt = self.clock.get_time() / 1000.0 if self.clock.get_time() > 0 else 1/60
            self.fpv_yaw_accumulator -= gp.right_stick[0] * gp.fpv_yaw_sensitivity * self.fpv_yaw_rate * dt

        # Rotate velocity by yaw to get world-frame XZ
        sin_yaw = math.sin(yaw)
        cos_yaw = math.cos(yaw)
        vx = (forward * sin_yaw + strafe * cos_yaw) * speed
        vz = (forward * cos_yaw - strafe * sin_yaw) * speed
        vy = vertical * speed

        # Yaw rate from mouse delta (accumulator is handled in event loop)
        # We compute rate from difference between accumulator and drone's current yaw
        current_yaw = drone_state['orientation'][2]
        yaw_error = self.fpv_yaw_accumulator - current_yaw
        # Wrap to [-pi, pi]
        while yaw_error > math.pi:
            yaw_error -= 2 * math.pi
        while yaw_error < -math.pi:
            yaw_error += 2 * math.pi
        yaw_rate = yaw_error * self.fpv_yaw_rate

        self.simulator.set_drone_velocity(self.fpv_drone_id, vx, vy, vz, yaw_rate)

    def _get_fpv_drone_state(self):
        """Get the current state of the FPV drone."""
        if self.fpv_drone_id is None:
            return None
        return next((d for d in self.drone_states if d['id'] == self.fpv_drone_id), None)

    def _update_gamepad_normal(self, dt):
        """Process gamepad sticks/triggers for camera control in normal mode."""
        import math
        gp = self.gamepad

        # Left stick -> camera pan (same vectors as WASD)
        lx, ly = gp.left_stick
        if abs(lx) > 0 or abs(ly) > 0:
            move_speed = self.camera.move_speed * dt
            forward = self.camera.target - self.camera.position
            forward_norm = np.linalg.norm(forward)
            if forward_norm > 0:
                forward = forward / forward_norm
            else:
                forward = np.array([0, 0, -1])
            right = np.cross(forward, self.camera.up)
            right_norm = np.linalg.norm(right)
            if right_norm > 0:
                right = right / right_norm
            else:
                right = np.array([1, 0, 0])
            movement = (-forward * ly + right * lx) * move_speed
            self.camera.position += movement
            self.camera.target += movement

        # Right stick -> camera orbit
        rx, ry = gp.right_stick
        if abs(rx) > 0 or abs(ry) > 0:
            orbit_speed = gp.camera_orbit_speed * dt
            self.camera.theta += rx * orbit_speed
            self.camera.phi -= ry * orbit_speed
            self.camera.phi = max(0.1, min(math.pi - 0.1, self.camera.phi))
            self.camera._update_position_from_spherical()

        # Triggers -> zoom
        zoom = gp.right_trigger - gp.left_trigger
        if abs(zoom) > 0:
            self.camera.distance *= (1.0 - zoom * gp.camera_zoom_speed)
            self.camera.distance = max(1.0, min(100.0, self.camera.distance))
            self.camera._update_position_from_spherical()

    def _update_gamepad_placement(self, dt):
        """Process gamepad left stick for placement cursor movement."""
        gp = self.gamepad
        lx, ly = gp.left_stick
        if abs(lx) > 0 or abs(ly) > 0:
            speed = self.placement_cursor_speed * dt * 30
            self.placement_cursor[0] -= lx * speed
            self.placement_cursor[1] -= ly * speed

    def _process_gamepad_buttons(self):
        """Handle one-shot gamepad button presses and D-pad actions."""
        gp = self.gamepad
        if not gp.connected:
            return

        # Context-aware B button (exit current mode)
        if gp.buttons_pressed.get(GamepadManager.BTN_B):
            if self.fpv_mode:
                self._exit_fpv()
            elif self.placement_mode:
                if self.placement_delete_mode:
                    self.placement_delete_mode = False
                    self.placement_selected_idx = -1
                else:
                    self.placement_mode = False
                    self.placement_delete_mode = False

        # Start -> toggle FPV
        if gp.buttons_pressed.get(GamepadManager.BTN_START):
            self._toggle_fpv()

        # Skip remaining buttons if in FPV mode
        if self.fpv_mode:
            return

        if self.placement_mode:
            # Placement-specific button actions
            if gp.buttons_pressed.get(GamepadManager.BTN_A):
                if self.placement_delete_mode:
                    self._handle_placement_key('delete', False)
                else:
                    self._handle_placement_key('return', False)
            if gp.buttons_pressed.get(GamepadManager.BTN_X):
                self._handle_placement_key('b', False)
            if gp.buttons_pressed.get(GamepadManager.BTN_Y):
                # Toggle delete sub-mode
                self.handle_key_press('j', True)
            if gp.buttons_pressed.get(GamepadManager.BTN_RB):
                self._handle_placement_key('=', False)
            if gp.buttons_pressed.get(GamepadManager.BTN_LB):
                self._handle_placement_key('-', False)
            # D-pad for obstacle selection in delete mode
            dx, dy = gp.dpad
            if self.placement_delete_mode:
                if dx > 0 and hasattr(self, '_gp_dpad_prev_x') and self._gp_dpad_prev_x <= 0:
                    self._handle_placement_key('right', False)
                elif dx < 0 and hasattr(self, '_gp_dpad_prev_x') and self._gp_dpad_prev_x >= 0:
                    self._handle_placement_key('left', False)
            self._gp_dpad_prev_x = dx
            return

        # Normal mode button actions
        if gp.buttons_pressed.get(GamepadManager.BTN_A):
            self.handle_key_press('p', False)  # pause
        if gp.buttons_pressed.get(GamepadManager.BTN_X):
            self.handle_key_press('h', False)  # help
        if gp.buttons_pressed.get(GamepadManager.BTN_Y):
            self.handle_key_press('home', False)  # frame swarm
        if gp.buttons_pressed.get(GamepadManager.BTN_BACK):
            self.handle_key_press('l', False)  # labels
        if gp.buttons_pressed.get(GamepadManager.BTN_L3):
            self.handle_key_press('r', False)  # reset camera
        if gp.buttons_pressed.get(GamepadManager.BTN_R3):
            self.handle_key_press('g', False)  # grid

        # LB/RB -> cycle drone lock
        if gp.buttons_pressed.get(GamepadManager.BTN_RB):
            self._gamepad_cycle_drone_lock(1)
        if gp.buttons_pressed.get(GamepadManager.BTN_LB):
            self._gamepad_cycle_drone_lock(-1)

        # D-pad left/right -> cycle formations
        dx, dy = gp.dpad
        if not hasattr(self, '_gp_dpad_prev'):
            self._gp_dpad_prev = (0, 0)
        if dx > 0 and self._gp_dpad_prev[0] <= 0:
            self._formation_cycle_index = (self._formation_cycle_index + 1) % len(self._formation_list)
            formation = self._formation_list[self._formation_cycle_index]
            self.simulator.set_formation(formation)
            print(f"[GAMEPAD] Formation: {formation}")
        elif dx < 0 and self._gp_dpad_prev[0] >= 0:
            self._formation_cycle_index = (self._formation_cycle_index - 1) % len(self._formation_list)
            formation = self._formation_list[self._formation_cycle_index]
            self.simulator.set_formation(formation)
            print(f"[GAMEPAD] Formation: {formation}")
        self._gp_dpad_prev = (dx, dy)

    def _gamepad_cycle_drone_lock(self, direction):
        """Cycle camera lock to next/previous drone."""
        if not self.drone_states:
            return
        max_id = len(self.drone_states) - 1
        current = self.camera.locked_drone_id
        if current is None:
            new_id = 0 if direction > 0 else max_id
        else:
            new_id = current + direction
            if new_id < 0 or new_id > max_id:
                self.camera.unlock_camera()
                return
        self.camera.lock_to_drone(new_id)

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
            
        # Draw FPV overlay
        if self.fpv_mode:
            drone_state = self._get_fpv_drone_state()
            if drone_state:
                import math
                speed = sum(v**2 for v in drone_state['velocity'])**0.5
                alt = drone_state['position'][1]
                yaw_deg = math.degrees(drone_state['orientation'][2])
                self.overlay.draw_text(f"FPV - Drone {self.fpv_drone_id}", 10, 190, (0, 255, 0))
                self.overlay.draw_text(f"Speed: {speed:.1f} m/s  Alt: {alt:.1f} m  Yaw: {yaw_deg:.0f} deg", 10, 210, (0, 255, 0))
                self.overlay.draw_text("WASD=Fly  QE=Up/Down  Mouse=Yaw  V/ESC=Exit", 10, 230, (200, 200, 200))

        # Draw placement mode overlay
        if self.placement_mode:
            y_start = 190 if not self.fpv_mode else 250
            if self.placement_delete_mode:
                self.overlay.draw_text("DELETE MODE", 10, y_start, (255, 80, 80))
                n = len(self.obstacle_states)
                sel = self.placement_selected_idx
                self.overlay.draw_text(f"Selected: {sel + 1}/{n}" if n > 0 else "No obstacles", 10, y_start + 20, (255, 200, 200))
                self.overlay.draw_text("Left/Right=Select  Del=Remove  Shift+J=Back  J=Exit", 10, y_start + 40, (200, 200, 200))
            else:
                cx, cz = self.placement_cursor
                self.overlay.draw_text("PLACEMENT MODE", 10, y_start, (0, 255, 100))
                if self.placement_type == 'box':
                    sz = self.placement_box_size
                    self.overlay.draw_text(f"Type: Box ({sz[0]:.0f}x{sz[1]:.0f}x{sz[2]:.0f})  Pos: ({cx:.1f}, {cz:.1f})", 10, y_start + 20, (200, 255, 200))
                else:
                    r, h = self.placement_cyl_size
                    self.overlay.draw_text(f"Type: Cylinder (r={r:.1f} h={h:.1f})  Pos: ({cx:.1f}, {cz:.1f})", 10, y_start + 20, (200, 255, 200))
                self.overlay.draw_text("Arrows=Move  B=Type  Enter=Place  +/-=Size  Shift+J=Delete  J=Exit", 10, y_start + 40, (200, 200, 200))

        # Gamepad connection indicator (top-right area)
        if self.gamepad.connected:
            self.overlay.draw_text("Gamepad: Connected", self.width - 200, 10, (0, 255, 0))
        elif self.gamepad.enabled:
            self.overlay.draw_text("Gamepad: Not connected", self.width - 220, 10, (128, 128, 128))

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