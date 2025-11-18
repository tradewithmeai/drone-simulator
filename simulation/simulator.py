import time
import threading
import queue
from typing import Dict, Any, Optional, Callable, Tuple
import yaml
import numpy as np
from simulation.swarm import Swarm
from simulation.environment import Environment
from simulation.game import HideAndSeekGame, SimpleAI

class Simulator:
    """Main simulation engine that manages the drone swarm."""
    
    def __init__(self, config_path: str = "config.yaml"):
        self._running = False
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
        
        # Thread management - simplified and safe
        self._thread: Optional[threading.Thread] = None
        self._last_tick_ts = 0.0

        # Initialize game environment if enabled
        self.game_enabled = self.config.get('game', {}).get('enabled', False)
        self.environment = None
        self.game = None
        self.ai = None

        if self.game_enabled:
            game_config = self.config['game']
            env_config = game_config['environment']

            # Create environment with obstacles
            self.environment = Environment(
                play_area_size=env_config['play_area_size'],
                num_obstacles=env_config['num_obstacles'],
                seed=env_config['obstacle_seed']
            )

            # Create game manager
            self.game = HideAndSeekGame(
                environment=self.environment,
                detection_radius=game_config['detection_radius'],
                catch_radius=game_config['catch_radius'],
                game_duration=game_config['game_duration']
            )

            # Create AI controller
            self.ai = SimpleAI(self.environment)

            print(f"[SIM] Hide-and-seek game mode enabled with {env_config['num_obstacles']} obstacles")
        
    def set_state_callback(self, callback: Callable):
        """Set callback function that receives drone state updates."""
        self.state_update_callback = callback
        
    def start(self):
        """Start the simulation thread - safe to call multiple times."""
        if self._thread and self._thread.is_alive():
            print("[SIM] start() called but thread already running")
            return
            
        self._running = True
        self._thread = threading.Thread(target=self._simulation_loop, name="SimThread", daemon=True)
        self._thread.start()
        
        # Give thread a moment to start
        time.sleep(0.05)
        print(f"[SIM] thread started: alive={self._thread.is_alive()}, id={self._thread.ident}")
        
    def stop(self):
        """Stop the simulation."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            print("[SIM] Thread stopped")
    
    def is_alive(self) -> bool:
        """Check if simulation thread is running."""
        return bool(self._thread) and self._thread.is_alive()
    
    def last_tick_time(self) -> float:
        """Get timestamp of last simulation tick."""
        return self._last_tick_ts
    
    def queue_size(self) -> int:
        """Get current command queue size."""
        return self._cmd_queue.qsize()
            
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

    def start_game(self):
        """Start a new hide-and-seek game round."""
        if self.game_enabled:
            self.enqueue("START_GAME")
        else:
            print("[SIM] Game mode not enabled in config")
            
    def respawn_formation(self, preset: str, num_drones: int = None):
        """Queue respawn command to be processed by simulation thread."""
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
        
        self.enqueue("RESPAWN", payload)
            
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
            info = {
                'running': self._running,
                'paused': self.paused,
                'current_formation': self.swarm.current_formation,
                'formation_complete': self.swarm.is_formation_complete(),
                'formation_progress': self.swarm.get_formation_progress(),
                'num_drones': len(self.swarm.drones),
                'update_rate': self.update_rate,
                'spawn_preset': self.swarm.spawn_preset,
                'game_enabled': self.game_enabled
            }

            # Add game status if enabled
            if self.game_enabled and self.game:
                info['game_status'] = self.game.update(self.swarm.drones)
            else:
                info['game_status'] = None

            return info
            
    def enqueue(self, cmd: str, payload: Optional[Dict[str, Any]] = None):
        """Enqueue a command for processing by the simulation thread."""
        self._cmd_queue.put((cmd, payload or {}))
        print(f"[SIM] queued {cmd} size={self._cmd_queue.qsize()}")

    def _initialize_game_drones(self):
        """Initialize drones for hide-and-seek game with roles and positions."""
        if not self.game_enabled or not self.environment:
            return

        game_config = self.config['game']
        seeker_count = game_config['seeker_count']
        hider_count = game_config['hider_count']
        total_drones = seeker_count + hider_count

        # Respawn drones with correct count
        if len(self.swarm.drones) != total_drones:
            self.swarm.respawn_formation(
                preset='random',
                num_drones=total_drones,
                spacing=5.0,
                altitude=5.0,
                seed=42,
                up_axis='y'
            )

        # Assign roles and colors
        for i, drone in enumerate(self.swarm.drones):
            if i < seeker_count:
                drone.role = "seeker"
                drone.color = [0.0, 1.0, 0.0]  # Green for seekers
                drone.behavior_state = "patrol"
                # Start seekers at edges
                pos = self.environment.get_random_position(min_clearance=1.0)
                drone.position = pos
                drone.target_position = pos
            else:
                drone.role = "hider"
                drone.color = [1.0, 0.0, 0.0]  # Red for hiders
                drone.behavior_state = "hide"
                # Start hiders at hiding spots
                hiding_spot = self.ai.hiding_spots[(i - seeker_count) % len(self.ai.hiding_spots)]
                drone.position = hiding_spot + np.array([0, 2.0, 0])  # Start above hiding spot
                drone.target_position = hiding_spot

        # Update game total hiders count
        self.game.total_hiders = hider_count
        print(f"[SIM] Initialized game: {seeker_count} seekers, {hider_count} hiders")
            
    def _simulation_loop(self):
        """Main simulation loop running in separate thread.
        
        WARNING: This method must ONLY be called by the simulation thread.
        Never call this directly from GUI code - use start() instead.
        """
        # Thread safety check
        current_thread = threading.current_thread()
        assert current_thread.name == "SimThread", f"Simulation loop must run on SimThread, not {current_thread.name}"
        
        print("[SIM] _simulation_loop ENTER")
        last = time.perf_counter()
        
        while self._running:
            now = time.perf_counter()
            dt = min(now - last, self._max_dt)
            last = now
            
            # Process up to 8 commands per tick
            cmds = 0
            while cmds < 8:
                try:
                    cmd, payload = self._cmd_queue.get_nowait()
                except queue.Empty:
                    break
                    
                print(f"[SIM] processing {cmd} {payload}")
                try:
                    if cmd == "RESPAWN":
                        with self.lock:
                            self.swarm.respawn_formation(**payload)
                            # Immediate state push
                            if self.state_update_callback:
                                states = self.swarm.get_states()
                                info = self.get_simulation_info()
                                self.state_update_callback(states, info)
                            print(f"[SIM] respawn complete: N={len(self.swarm.drones)}")
                    elif cmd == "SET_FORMATION":
                        with self.lock:
                            self.swarm.set_formation(**payload)
                    elif cmd == "PAUSE":
                        self.paused = True
                    elif cmd == "RESUME":
                        self.paused = False
                    elif cmd == "START_GAME":
                        if self.game_enabled and self.game:
                            with self.lock:
                                self._initialize_game_drones()
                                self.game.start_game()
                                print("[SIM] Game started!")
                except Exception as e:
                    print(f"[SIM] ERROR processing {cmd}: {e}")
                finally:
                    cmds += 1
            
            # Physics only when not paused
            with self.lock:
                if not self.paused:
                    # Update AI behaviors if game is active
                    if self.game_enabled and self.game and self.game.game_active and self.ai:
                        current_time = self.game.get_elapsed_time()
                        seekers = [d for d in self.swarm.drones if d.role == "seeker"]
                        hiders = [d for d in self.swarm.drones if d.role == "hider"]

                        # Update each drone's AI
                        for drone in self.swarm.drones:
                            if drone.role == "seeker":
                                self.ai.update_seeker_ai(drone, hiders, current_time)
                            elif drone.role == "hider":
                                self.ai.update_hider_ai(drone, seekers, current_time)

                    # Update physics
                    self.swarm.update(dt)

                # ALWAYS push state (paused or not)
                if self.state_update_callback:
                    states = self.swarm.get_states()
                    info = self.get_simulation_info()
                    self.state_update_callback(states, info)
            
            self._last_tick_ts = time.time()
            time.sleep(self._tick_sleep)
        
        print("[SIM] _simulation_loop EXIT")
