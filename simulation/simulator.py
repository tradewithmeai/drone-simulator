import time
import threading
import queue
from typing import Dict, Any, Optional, Callable, Tuple
import numpy as np
import yaml
from simulation.swarm import Swarm
from simulation.sensors import SensorConfig
from simulation.environment import Environment, WindConfig
from simulation.flight_controller import FlightControllerConfig

class Simulator:
    """Main simulation engine that manages the drone swarm."""
    
    def __init__(self, config_path: str = "config.yaml"):
        self._running = False
        self.paused = False
        self.lock = threading.RLock()
        
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
        
        # Load sensor configuration
        sensor_cfg = self.config.get('sensors', {})
        imu_cfg = sensor_cfg.get('imu', {})
        gps_cfg = sensor_cfg.get('gps', {})
        baro_cfg = sensor_cfg.get('baro', {})
        rf_cfg = sensor_cfg.get('rangefinder', {})
        bat_cfg = sensor_cfg.get('battery', {})
        self.sensor_config = SensorConfig(
            perfect_mode=sensor_cfg.get('perfect_mode', False),
            accel_noise_std=imu_cfg.get('accel_noise_std', 0.02),
            accel_bias_drift=imu_cfg.get('accel_bias_drift', 0.0001),
            accel_bias_max=imu_cfg.get('accel_bias_max', 0.2),
            gyro_noise_std=imu_cfg.get('gyro_noise_std', 0.001),
            gyro_bias_drift=imu_cfg.get('gyro_bias_drift', 0.00005),
            gyro_bias_max=imu_cfg.get('gyro_bias_max', 0.01),
            gps_update_rate=gps_cfg.get('update_rate', 10.0),
            gps_pos_noise_h=gps_cfg.get('pos_noise_h', 1.5),
            gps_pos_noise_v=gps_cfg.get('pos_noise_v', 3.0),
            gps_vel_noise_std=gps_cfg.get('vel_noise_std', 0.1),
            baro_noise_std=baro_cfg.get('noise_std', 0.3),
            baro_bias_drift=baro_cfg.get('bias_drift', 0.001),
            baro_bias_max=baro_cfg.get('bias_max', 2.0),
            rangefinder_noise_std=rf_cfg.get('noise_std', 0.02),
            rangefinder_max_range=rf_cfg.get('max_range', 40.0),
            battery_voltage_noise_std=bat_cfg.get('voltage_noise_std', 0.01),
            battery_current_noise_std=bat_cfg.get('current_noise_std', 0.05),
        )

        # Load collision configuration
        self.collision_config = self.config.get('collision', {
            'enabled': True,
            'drone_radius': 0.3,
            'restitution': 0.3,
            'crash_speed': 8.0,
        })

        # Load flight controller configuration (including avoidance)
        fc_cfg = self.config.get('flight_controller', {})
        self.controller_config = FlightControllerConfig(
            pos_kp=fc_cfg.get('pos_kp', 0.8),
            pos_ki=fc_cfg.get('pos_ki', 0.0),
            pos_kd=fc_cfg.get('pos_kd', 0.2),
            max_velocity=fc_cfg.get('max_velocity', 8.0),
            vel_kp=fc_cfg.get('vel_kp', 1.2),
            vel_ki=fc_cfg.get('vel_ki', 0.05),
            vel_kd=fc_cfg.get('vel_kd', 0.02),
            max_tilt_angle=fc_cfg.get('max_tilt_angle', 0.35),
            alt_kp=fc_cfg.get('alt_kp', 1.0),
            alt_ki=fc_cfg.get('alt_ki', 0.1),
            alt_kd=fc_cfg.get('alt_kd', 0.6),
            max_vertical_vel=fc_cfg.get('max_vertical_vel', 5.0),
            max_thrust_adjust=fc_cfg.get('max_thrust_adjust', 0.25),
            att_kp=fc_cfg.get('att_kp', 5.0),
            att_ki=fc_cfg.get('att_ki', 0.0),
            att_kd=fc_cfg.get('att_kd', 0.2),
            max_rate=fc_cfg.get('max_rate', 4.0),
            rate_kp=fc_cfg.get('rate_kp', 0.3),
            rate_ki=fc_cfg.get('rate_ki', 0.02),
            rate_kd=fc_cfg.get('rate_kd', 0.0),
            avoidance_enabled=fc_cfg.get('avoidance_enabled', False),
            avoidance_sensor_range=fc_cfg.get('avoidance_sensor_range', 5.0),
            avoidance_safety_margin=fc_cfg.get('avoidance_safety_margin', 0.5),
            avoidance_repulsion_gain=fc_cfg.get('avoidance_repulsion_gain', 3.0),
            avoidance_velocity_limit=fc_cfg.get('avoidance_velocity_limit', 2.0),
        )

        # Load wind / environment configuration
        wind_cfg = self.config.get('wind', {})
        self.environment = Environment(WindConfig(
            enabled=wind_cfg.get('enabled', False),
            base_velocity=np.array(wind_cfg.get('base_velocity', [0, 0, 0]), dtype=float),
            gust_magnitude=wind_cfg.get('gust_magnitude', 2.0),
            gust_frequency=wind_cfg.get('gust_frequency', 0.1),
        ))

        self.swarm = Swarm(initial_count, drone_colors, spacing, spawn_preset,
                           spawn_altitude, seed, up_axis, sensor_config=self.sensor_config,
                           collision_config=self.collision_config,
                           environment=self.environment,
                           controller_config=self.controller_config)

        # Load obstacle scene from config
        obstacle_cfg = self.config.get('obstacles', {})
        if obstacle_cfg.get('enabled', False):
            preset = obstacle_cfg.get('preset_scene', 'default')
            scenes = obstacle_cfg.get('scenes', {})
            if preset in scenes:
                self.swarm.obstacles.load_scene(scenes[preset])
                print(f"[SIM] Loaded obstacle scene '{preset}' with {len(scenes[preset])} objects")

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
        self.enqueue("SET_FORMATION", {"formation_type": formation_type})
            
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
            
    def add_box_obstacle(self, position, size, color=None):
        """Queue command to add a box obstacle."""
        self.enqueue("ADD_BOX", {
            'position': position,
            'size': size,
            'color': color,
        })

    def add_cylinder_obstacle(self, position, radius, height, color=None):
        """Queue command to add a cylinder obstacle."""
        self.enqueue("ADD_CYLINDER", {
            'position': position,
            'radius': radius,
            'height': height,
            'color': color,
        })

    def remove_last_obstacle(self):
        """Queue command to remove the last obstacle."""
        self.enqueue("REMOVE_OBSTACLE")

    def clear_all_obstacles(self):
        """Queue command to clear all obstacles."""
        self.enqueue("CLEAR_OBSTACLES")

    def get_hal(self, drone_id: int):
        """Get the HAL interface for a specific drone.

        Args:
            drone_id: The drone's integer ID.

        Returns:
            SimHAL instance, or None if drone_id not found.
        """
        with self.lock:
            return self.swarm.get_hal(drone_id)

    def get_all_hals(self) -> dict:
        """Get HAL interfaces for all drones."""
        with self.lock:
            return self.swarm.get_all_hals()

    def get_drone_states(self) -> list:
        """Get current state of all drones."""
        with self.lock:
            return self.swarm.get_states()
            
    def get_simulation_info(self) -> Dict[str, Any]:
        """Get general simulation information."""
        with self.lock:
            return {
                'running': self._running,
                'paused': self.paused,
                'current_formation': self.swarm.current_formation,
                'formation_complete': self.swarm.is_formation_complete(),
                'formation_progress': self.swarm.get_formation_progress(),
                'num_drones': len(self.swarm.drones),
                'update_rate': self.update_rate,
                'spawn_preset': self.swarm.spawn_preset,
                'obstacles': self.swarm.get_obstacle_states(),
                'wind': {
                    'enabled': self.environment.wind.enabled,
                    'base_velocity': self.environment.wind.base_velocity.tolist(),
                    'gust_magnitude': self.environment.wind.gust_magnitude,
                    'gust_frequency': self.environment.wind.gust_frequency,
                },
            }
            
    def enqueue(self, cmd: str, payload: Optional[Dict[str, Any]] = None):
        """Enqueue a command for processing by the simulation thread."""
        self._cmd_queue.put((cmd, payload or {}))
        print(f"[SIM] queued {cmd} size={self._cmd_queue.qsize()}")
            
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
        start_time = time.perf_counter()  # Track simulation start time for auto-spawn
        
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
                    elif cmd == "ADD_BOX":
                        with self.lock:
                            self.swarm.obstacles.add_box(**payload)
                    elif cmd == "ADD_CYLINDER":
                        with self.lock:
                            self.swarm.obstacles.add_cylinder(**payload)
                    elif cmd == "REMOVE_OBSTACLE":
                        with self.lock:
                            self.swarm.obstacles.remove_last()
                    elif cmd == "CLEAR_OBSTACLES":
                        with self.lock:
                            self.swarm.obstacles.clear_all()
                    elif cmd == "PAUSE":
                        self.paused = True
                    elif cmd == "RESUME":
                        self.paused = False
                except Exception as e:
                    print(f"[SIM] ERROR processing {cmd}: {e}")
                finally:
                    cmds += 1
            
            # Handle auto-spawn after initial startup delay (no race conditions)
            if (not self.auto_spawn_triggered and 
                self.auto_spawn_config['enabled'] and 
                time.perf_counter() - start_time >= 0.5):
                
                print(f"[SIM] Triggering auto-spawn after 0.5s delay...")
                self.auto_spawn_triggered = True
                
                try:
                    with self.lock:
                        config = self.auto_spawn_config
                        self.swarm.auto_spawn(
                            config['count'], 
                            config['preset'],
                            config['spacing'],
                            config['altitude'], 
                            config['seed'],
                            config['up_axis']
                        )
                        # Immediate state push after auto-spawn
                        if self.state_update_callback:
                            states = self.swarm.get_states()
                            info = self.get_simulation_info()
                            self.state_update_callback(states, info)
                        print(f"[SIM] Auto-spawn completed: {len(self.swarm.drones)} drones created")
                except Exception as e:
                    print(f"[SIM] Auto-spawn failed: {e}")
            
            # Physics only when not paused
            with self.lock:
                if not self.paused:
                    self.swarm.update(dt, self.environment)
                # ALWAYS push state (paused or not)
                if self.state_update_callback:
                    states = self.swarm.get_states()
                    info = self.get_simulation_info()
                    self.state_update_callback(states, info)
            
            self._last_tick_ts = time.time()
            time.sleep(self._tick_sleep)
        
        print("[SIM] _simulation_loop EXIT")
