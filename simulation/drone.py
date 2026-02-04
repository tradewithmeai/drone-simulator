"""Individual drone with rigid-body physics and flight controller.

Each Drone composes:
- QuadrotorPhysics: 6-DOF rigid body simulation
- FlightController: cascaded PID from position to motor RPMs

The Drone class maintains backward compatibility with the GUI by
providing the same get_state() dict format, with optional new fields.
"""

import numpy as np
from typing import List
from simulation.physics import QuadrotorPhysics, PhysicsConfig, quat_to_euler
from simulation.flight_controller import FlightController, FlightControllerConfig
from simulation.sensors import SensorSuite, SensorConfig


class Drone:
    """Individual drone with physics simulation and flight control."""

    def __init__(self, drone_id: int, position: np.ndarray, color: List[float],
                 physics_config: PhysicsConfig = None,
                 controller_config: FlightControllerConfig = None,
                 sensor_config: SensorConfig = None):
        self.id = drone_id
        self.color = color

        # Physics engine
        self.physics = QuadrotorPhysics(physics_config)
        self.physics.position = np.array(position, dtype=float)

        # Flight controller
        self.controller = FlightController(self.physics, controller_config)

        # Sensor suite (independent noise per drone, seeded by ID)
        self.sensors = SensorSuite(sensor_config, seed=drone_id)

        # Target tracking (for GUI compatibility and formation system)
        self.target_position = np.array(position, dtype=float)

        # State
        self.settled = False
        self.convergence_threshold = 0.3  # slightly larger for physics-based settling
        self.battery_level = 100.0
        self.crashed = False

        # Battery model
        self._battery_capacity_wh = 50.0  # watt-hours
        self._battery_energy_j = self._battery_capacity_wh * 3600  # joules

        # Auto-arm and set to hover at spawn position
        self.controller.arm()
        self.controller.set_position(self.physics.position)

    @property
    def position(self) -> np.ndarray:
        """Current position (reads from physics engine)."""
        return self.physics.position

    @position.setter
    def position(self, value: np.ndarray):
        """Set position (writes to physics engine)."""
        self.physics.position = np.array(value, dtype=float)

    @property
    def velocity(self) -> np.ndarray:
        """Current velocity (reads from physics engine)."""
        return self.physics.velocity

    @velocity.setter
    def velocity(self, value: np.ndarray):
        """Set velocity (writes to physics engine)."""
        self.physics.velocity = np.array(value, dtype=float)

    def update(self, delta_time: float, wind_force: np.ndarray = None):
        """Update drone physics and control for one timestep.

        Args:
            delta_time: Time step in seconds.
            wind_force: Optional wind force vector [N] in world frame.
        """
        if self.crashed or self.battery_level <= 0:
            # Dead drone — motors off, gravity only
            self.physics.set_motor_rpms(np.zeros(4))
            self.physics.update(delta_time, wind_force)
            return

        # Run flight controller to get motor RPMs
        motor_rpms = self.controller.update(delta_time)
        self.physics.set_motor_rpms(motor_rpms)

        # Run physics simulation
        self.physics.update(delta_time, wind_force)

        # Update battery based on motor power draw
        power = self.physics.get_power_draw()
        energy_used = power * delta_time  # joules
        if self._battery_energy_j > 0:
            self.battery_level -= (energy_used / self._battery_energy_j) * 100.0
            self.battery_level = max(0.0, self.battery_level)

        # Update settled state
        distance = np.linalg.norm(self.target_position - self.physics.position)
        speed = np.linalg.norm(self.physics.velocity)
        self.settled = distance < self.convergence_threshold and speed < 0.5

    def set_target(self, target: np.ndarray):
        """Set new target position for the drone.

        This is the primary interface used by the formation system.
        Routes through the flight controller.
        """
        self.target_position = np.array(target, dtype=float)
        self.settled = False
        self.controller.set_position(self.target_position)

    def get_state(self) -> dict:
        """Get current drone state for GUI updates.

        Maintains backward compatibility with the existing GUI while
        adding new physics fields.
        """
        euler = quat_to_euler(self.physics.orientation)
        return {
            'id': self.id,
            'position': self.physics.position.tolist(),
            'velocity': self.physics.velocity.tolist(),
            'target': self.target_position.tolist(),
            'color': self.color,
            'battery': self.battery_level,
            'settled': self.settled,
            # New fields (GUI ignores unknown keys)
            'orientation': euler.tolist(),  # [roll, pitch, yaw] radians
            'angular_velocity': self.physics.angular_velocity.tolist(),
            'motor_rpms': self.physics.motor_rpms.tolist(),
            'armed': self.controller.armed,
            'mode': self.controller.mode,
            'crashed': self.crashed,
        }
