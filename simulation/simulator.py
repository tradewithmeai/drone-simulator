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
            
        # Initialize swarm
        num_drones = self.config['simulation']['num_drones']
        drone_colors = self.config['drone']['colors']
        spacing = self.config['formation']['spacing']
        
        self.swarm = Swarm(num_drones, drone_colors, spacing)
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
                'update_rate': self.update_rate
            }
            
    def _simulation_loop(self):
        """Main simulation loop running in separate thread."""
        last_time = time.time()
        
        while self.running:
            current_time = time.time()
            actual_dt = current_time - last_time
            last_time = current_time
            
            if not self.paused:
                with self.lock:
                    # Update swarm with actual time delta
                    self.swarm.update(actual_dt)
                    
                    # Send state update to callback (e.g., GUI)
                    if self.state_update_callback:
                        states = self.swarm.get_states()
                        sim_info = self.get_simulation_info()
                        self.state_update_callback(states, sim_info)
                        
            # Sleep to maintain target update rate
            sleep_time = max(0, self.dt - actual_dt)
            time.sleep(sleep_time)