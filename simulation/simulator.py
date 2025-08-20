import time
import threading
import queue
from typing import Dict, Any, Optional, Callable, Tuple
import yaml
from simulation.swarm import Swarm

class Simulator:
    """Main simulation engine that manages the drone swarm."""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.running = False
        self.paused = False
        self.lock = threading.Lock()
        
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
            
        # Initialize swarm with drone settings
        drone_config = self.config['drones']
        gui_config = self.config.get('gui', {})
        
        # Get configuration values
        drone_colors = drone_config['colors']
        up_axis = gui_config.get('up_axis', 'y')
        auto_spawn = gui_config.get('auto_spawn_on_start', True)
        
        # Create empty swarm initially (we'll auto-spawn later if configured)
        initial_count = drone_config['count'] if auto_spawn else 0
        spacing = drone_config['spacing']
        spawn_preset = drone_config['spawn_preset']
        spawn_altitude = drone_config['spawn_altitude']
        seed = drone_config['seed']
        
        self.swarm = Swarm(initial_count, drone_colors, spacing, spawn_preset, spawn_altitude, seed, up_axis)
        
        # Store auto-spawn settings for later use
        self.auto_spawn_config = {
            'enabled': auto_spawn,
            'count': drone_config['count'],
            'preset': spawn_preset,
            'spacing': spacing,
            'altitude': spawn_altitude,
            'seed': seed,
            'up_axis': up_axis
        }
        
        # Auto-spawn tracking
        self.auto_spawn_triggered = False
        
        # Central command queue (thread-safe)
        self._cmd_queue = queue.Queue()
        self._max_dt = 0.1  # Maximum time step to prevent instability
        self._tick_sleep = 1.0 / self.config['simulation']['update_rate']
        
        self.update_rate = self.config['simulation']['update_rate']
        self.dt = 1.0 / self.update_rate
        
        # Callbacks for external updates (e.g., GUI)
        self.state_update_callback: Optional[Callable] = None
        
        # Simulation thread
        self.sim_thread: Optional[threading.Thread] = None
        
    def set_state_callback(self, callback: Callable):
        """Set callback function that receives drone state updates."""
        self.state_update_callback = callback
        
    def start(self):
        """Start the simulation in a separate thread."""
        print("[SIM] start() called")
        if self.running:
            print("[SIM] Already running, returning")
            return
            
        print("[SIM] Starting simulation thread...")
        self.running = True
        
        try:
            self.sim_thread = threading.Thread(target=self._simulation_loop, daemon=False)
            self.sim_thread.start()
            
            # Give thread a moment to start
            import time
            time.sleep(0.1)
            
            if not self.sim_thread.is_alive():
                print("[SIM] ERROR: Thread failed to start!")
            else:
                print("[SIM] Thread started successfully")
                
        except Exception as e:
            print(f"[SIM] CRITICAL ERROR creating/starting thread: {e}")
            import traceback
            traceback.print_exc()
            self.running = False
        
    def stop(self):
        """Stop the simulation."""
        self.running = False
        if self.sim_thread:
            self.sim_thread.join()
            
    def pause(self):
        """Pause the simulation."""
        self.enqueue("PAUSE")
        
    def resume(self):
        """Resume the simulation."""
        self.enqueue("RESUME")
        
    def step_simulation(self):
        """Step the simulation by one tick (useful when paused)."""
        with self.lock:
            self.swarm.update(self.dt)
            
            # Send state update to callback
            if self.state_update_callback:
                states = self.swarm.get_states()
                sim_info = self.get_simulation_info()
                self.state_update_callback(states, sim_info)
        
    def set_formation(self, formation_type: str):
        """Set the formation pattern for the swarm."""
        self.enqueue("SET_FORMATION", {"formation": formation_type})
            
    def respawn_formation(self, preset: str, num_drones: int = None):
        """Queue respawn command to be processed by simulation thread."""
        print(f"[SIM] ===== RESPAWN_FORMATION CALLED =====")
        print(f"[SIM] Called from thread: {threading.get_ident()}")
        print(f"[SIM] Preset: {preset}, num_drones: {num_drones}")
        print(f"[SIM] Simulation running: {self.running}")
        print(f"[SIM] Thread exists: {hasattr(self, 'sim_thread')}")
        if hasattr(self, 'sim_thread'):
            print(f"[SIM] Thread alive: {self.sim_thread.is_alive()}")
        
        config = self.auto_spawn_config
        
        # For manual spawns, use a reasonable default instead of config count (which might be 0 in --no-spawn mode)
        if num_drones is None:
            if config['count'] > 0:
                # Use config count if it's reasonable
                default_count = config['count'] 
            else:
                # Use reasonable default for manual spawns (--no-spawn mode)
                default_count = 5
        else:
            default_count = num_drones
        
        payload = {
            'preset': preset,
            'num_drones': default_count,
            'spacing': config['spacing'],
            'altitude': config['altitude'],
            'seed': config['seed'],
            'up_axis': config['up_axis']
        }
        
        print(f"[SIM] About to enqueue RESPAWN command with payload: {payload}")
        print(f"[SIM] Current queue size before enqueue: {self._cmd_queue.qsize()}")
        self.enqueue("RESPAWN", payload)
        print(f"[SIM] Current queue size after enqueue: {self._cmd_queue.qsize()}")
        print(f"[SIM] ===== RESPAWN_FORMATION COMPLETED =====")
            
    def trigger_auto_spawn(self):
        """Queue auto-spawn command to be processed by simulation thread."""
        if self.auto_spawn_config['enabled']:
            config = self.auto_spawn_config
            
            payload = {
                'count': config['count'],
                'preset': config['preset'],
                'spacing': config['spacing'],
                'altitude': config['altitude'],
                'seed': config['seed'],
                'up_axis': config['up_axis']
            }
            
            print(f"[GUI] Enqueue AUTO_SPAWN {payload}")
            self.enqueue("AUTO_SPAWN", payload)
        else:
            print("Auto-spawn disabled in configuration")
            
    def get_drone_states(self) -> list:
        """Get current state of all drones."""
        with self.lock:
            return self.swarm.get_states()
            
    def get_simulation_info(self) -> Dict[str, Any]:
        """Get general simulation information."""
        with self.lock:
            return {
                'running': self.running,
                'paused': self.paused,
                'current_formation': self.swarm.current_formation,
                'formation_complete': self.swarm.is_formation_complete(),
                'formation_progress': self.swarm.get_formation_progress(),
                'num_drones': len(self.swarm.drones),
                'update_rate': self.update_rate,
                'spawn_preset': self.swarm.spawn_preset
            }
            
    def enqueue(self, cmd: str, payload: Optional[Dict[str, Any]] = None):
        """Enqueue a command for processing by the simulation thread."""
        print(f"[SIM] ===== ENQUEUE CALLED =====")
        print(f"[SIM] Command: {cmd}")
        print(f"[SIM] Payload: {payload}")
        print(f"[SIM] Queue size before put: {self._cmd_queue.qsize()}")
        print(f"[SIM] Thread calling enqueue: {threading.get_ident()}")
        
        self._cmd_queue.put((cmd, payload or {}))
        
        print(f"[SIM] Queue size after put: {self._cmd_queue.qsize()}")
        print(f"[SIM] Command successfully queued: {cmd}")
        print(f"[SIM] ===== ENQUEUE COMPLETED =====")
            
    def _simulation_loop(self):
        """Main simulation loop running in separate thread."""
        print("[SIM] ===== SIMULATION THREAD STARTED =====")
        print(f"[SIM] Thread ID: {threading.get_ident()}")
        print(f"[SIM] Thread name: {threading.current_thread().name}")
        print(f"[SIM] Running flag: {self.running}")
        print("[SIM] Starting main simulation loop...")
        
        last = time.perf_counter()
        loop_count = 0
        
        while self.running:
            try:
                loop_count += 1
                
                # EXTENSIVE DEBUG: Log every single loop iteration for first 10 ticks
                if loop_count <= 10:
                    print(f"[SIM] LOOP TICK {loop_count}: running={self.running}, queue_size={self._cmd_queue.qsize()}")
                
                if loop_count % 300 == 0:  # Log every 5 seconds at 60 FPS
                    print(f"[SIM] Loop running: tick {loop_count}")
                
                # Periodic heartbeat (every second at 60 FPS)
                if loop_count % 60 == 0:
                    print(f"[SIM] Heartbeat: tick {loop_count}, queue_size={self._cmd_queue.qsize()}")
                    
                now = time.perf_counter()
                dt = min(now - last, self._max_dt)
                last = now
                
                # EXTENSIVE DEBUG: Command processing section
                if loop_count <= 10 or self._cmd_queue.qsize() > 0:
                    print(f"[SIM] COMMAND PROCESSING START: tick={loop_count}, queue_size={self._cmd_queue.qsize()}")
                
                cmds_processed = 0
                while cmds_processed < 8:
                    try:
                        cmd, payload = self._cmd_queue.get_nowait()
                        print(f"[SIM] ===== PROCESSING COMMAND: {cmd} =====")
                        print(f"[SIM] Command payload: {payload}")
                        print(f"[SIM] Commands processed this tick: {cmds_processed}")
                    except queue.Empty:
                        if loop_count <= 10:
                            print(f"[SIM] Queue empty at tick {loop_count}")
                        break
                    
                    try:
                        
                        if cmd == "RESPAWN":
                            with self.lock:
                                self.swarm.respawn_formation(
                                    payload.get('preset'),
                                    payload.get('num_drones'),
                                    payload.get('spacing'),
                                    payload.get('altitude'),
                                    payload.get('seed'),
                                    payload.get('up_axis')
                                )
                                # IMMEDIATE STATE PUSH even if paused:
                                if self.state_update_callback:
                                    states = self.swarm.get_states()
                                    info = self.get_simulation_info()
                                    self.state_update_callback(states, info)
                                print(f"[SIM] Respawned {len(self.swarm.drones)} drones via {payload}")
                            
                        elif cmd == "SET_FORMATION":
                            with self.lock:
                                self.swarm.set_formation(payload.get('formation'))
                                
                        elif cmd == "PAUSE":
                            self.paused = True
                            print("[SIM] Paused")
                            
                        elif cmd == "RESUME":
                            self.paused = False
                            print("[SIM] Resumed")
                            
                        elif cmd == "AUTO_SPAWN":
                            with self.lock:
                                self.swarm.auto_spawn(
                                    payload.get('count'),
                                    payload.get('preset'),
                                    payload.get('spacing'),
                                    payload.get('altitude'),
                                    payload.get('seed'),
                                    payload.get('up_axis')
                                )
                                # Immediate state push
                                if self.state_update_callback:
                                    states = self.swarm.get_states()
                                    info = self.get_simulation_info()
                                    self.state_update_callback(states, info)
                                print(f"[SIM] Auto-spawn complete: {len(self.swarm.drones)} drones")
                            
                    except Exception as e:
                        print(f"[SIM][ERROR] Command processing failed: {e}")
                        import traceback
                        traceback.print_exc()
                    finally:
                        cmds_processed += 1
                
                # 2) Physics update ONLY when not paused
                with self.lock:
                    if not self.paused:
                        self.swarm.update(dt)
                    
                    # 3) ALWAYS push state to GUI (paused or not)
                    if self.state_update_callback:
                        states = self.swarm.get_states()
                        info = self.get_simulation_info()
                        self.state_update_callback(states, info)
                        
                        # Debug: log state push status
                        if not states:
                            print("[SIM][WARN] State push has 0 drones")
                        elif cmds_processed > 0:  # Only log if we processed commands
                            print(f"[SIM] State push: N={len(states)}")
                            
                # Sleep to regulate loop
                time.sleep(self._tick_sleep)
                
            except Exception as e:
                print(f"[SIM] CRITICAL ERROR in simulation loop: {e}")
                import traceback
                traceback.print_exc()
                break  # Exit loop on critical error
            
