import time
import threading
from typing import Dict, Any, Optional, Callable
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
        self.spawn_command_queue = []  # Queue for spawn commands
        self.spawn_queue_lock = threading.Lock()  # Separate lock for spawn queue
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
        if self.running:
            return
            
        self.running = True
        self.sim_thread = threading.Thread(target=self._simulation_loop)
        self.sim_thread.start()
        
    def stop(self):
        """Stop the simulation."""
        self.running = False
        if self.sim_thread:
            self.sim_thread.join()
            
    def pause(self):
        """Pause the simulation."""
        self.paused = True
        
    def resume(self):
        """Resume the simulation."""
        self.paused = False
        
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
        with self.lock:
            self.swarm.set_formation(formation_type)
            
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
        
        spawn_command = {
            'type': 'respawn',
            'preset': preset,
            'count': default_count,
            'spacing': config['spacing'],
            'altitude': config['altitude'],
            'seed': config['seed'],
            'up_axis': config['up_axis']
        }
        
        with self.spawn_queue_lock:
            self.spawn_command_queue.append(spawn_command)
            queue_size = len(self.spawn_command_queue)
        print(f"[GUI-THREAD] Respawn command queued: {spawn_command['count']} drones in '{preset}' formation (queue size: {queue_size})")
            
    def trigger_auto_spawn(self):
        """Queue auto-spawn command to be processed by simulation thread."""
        if self.auto_spawn_config['enabled']:
            config = self.auto_spawn_config
            print("[GUI-THREAD] Queuing auto-spawn command...")
            
            spawn_command = {
                'type': 'auto_spawn',
                'config': config
            }
            
            with self.spawn_queue_lock:
                self.spawn_command_queue.append(spawn_command)
                queue_size = len(self.spawn_command_queue)
            print(f"[GUI-THREAD] Auto-spawn command queued: {config['count']} drones in '{config['preset']}' formation (queue size: {queue_size})")
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
            
    def _simulation_loop(self):
        """Main simulation loop running in separate thread."""
        last_time = time.time()
        
        while self.running:
            current_time = time.time()
            actual_dt = current_time - last_time
            last_time = current_time
            
            # Process spawn commands in simulation thread (thread-safe)
            self._process_spawn_commands()
            
            with self.lock:
                if not self.paused:
                    # Update physics only when not paused
                    self.swarm.update(actual_dt)

                # Always push states (paused or not) so GUI can render and HUD stays live
                if self.state_update_callback:
                    states = self.swarm.get_states()
                    sim_info = self.get_simulation_info()
                    self.state_update_callback(states, sim_info)
                        
            # Sleep to maintain target update rate
            sleep_time = max(0, self.dt - actual_dt)
            time.sleep(sleep_time)
            
    def _process_spawn_commands(self):
        """Process queued spawn commands in the simulation thread (thread-safe)."""
        # Check queue size for debugging
        queue_size = 0
        with self.spawn_queue_lock:
            queue_size = len(self.spawn_command_queue)
        
        
        if queue_size == 0:
            return
        
        print(f"[SPAWN-DEBUG] Processing spawn queue (size: {queue_size})")
            
        # Process one command per simulation tick to avoid blocking
        command = None
        with self.spawn_queue_lock:
            if self.spawn_command_queue:
                command = self.spawn_command_queue.pop(0)
                remaining = len(self.spawn_command_queue)
                print(f"[SPAWN-DEBUG] Dequeued command: {command['type']}, remaining: {remaining}")
            else:
                print("[SPAWN-DEBUG] Queue was empty when trying to dequeue")
                return
        
        if command is None:
            print("[SPAWN-DEBUG] Command is None after dequeue")
            return
        
        # Execute spawn command with error handling
        try:
            if command['type'] == 'auto_spawn':
                config = command['config']
                print(f"[SIM-THREAD] Processing auto-spawn: {config['count']} drones...")
                
                with self.lock:
                    self.swarm.auto_spawn(
                        config['count'],
                        config['preset'], 
                        config['spacing'],
                        config['altitude'],
                        config['seed'],
                        config['up_axis']
                    )
                    
                    # Immediately push a state snapshot so GUI sees drones this frame
                    if self.state_update_callback:
                        states = self.swarm.get_states()
                        sim_info = self.get_simulation_info()
                        self.state_update_callback(states, sim_info)
                        
                actual_count = len(self.swarm.drones)
                print(f"[SIM-THREAD] Auto-spawn completed: {actual_count} drones created in '{config['preset']}' formation")
                
            elif command['type'] == 'respawn':
                print(f"[SIM-THREAD] Processing respawn: {command['count']} drones in '{command['preset']}' formation...")
                
                with self.lock:
                    self.swarm.respawn_formation(
                        command['preset'],
                        command['count'],
                        command['spacing'],
                        command['altitude'],
                        command['seed'],
                        command['up_axis']
                    )
                    
                    # Immediately push a state snapshot so GUI sees drones this frame
                    if self.state_update_callback:
                        states = self.swarm.get_states()
                        sim_info = self.get_simulation_info()
                        self.state_update_callback(states, sim_info)
                        
                actual_count = len(self.swarm.drones)
                print(f"[SIM-THREAD] Respawn completed: {actual_count} drones created in '{command['preset']}' formation")
                
        except Exception as e:
            print(f"[SIM-THREAD] Spawn command failed: {e}")
            import traceback
            traceback.print_exc()