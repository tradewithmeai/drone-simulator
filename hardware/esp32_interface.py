"""
ESP32-C3 Hardware Interface
Connects Python swarm logic to real ESP32-C3 flight controllers via WiFi.
"""

import socket
import struct
import threading
import time
import numpy as np
from typing import Dict, List, Callable, Optional


class ESP32Drone:
    """Interface to a single ESP32-C3 drone."""

    # Command types (must match firmware)
    CMD_ARM = 1
    CMD_DISARM = 2
    CMD_SET_MODE = 3
    CMD_CONTROL_INPUT = 4
    CMD_POSITION_TARGET = 5
    CMD_VELOCITY_COMMAND = 6

    # Flight modes
    MODE_DISARMED = 0
    MODE_ARMED = 1
    MODE_STABILIZE = 2
    MODE_ALT_HOLD = 3
    MODE_POS_HOLD = 4
    MODE_AUTONOMOUS = 5

    def __init__(self, drone_id: int, ip_address: str, command_port: int = 14551):
        """
        Initialize ESP32 drone interface.

        Args:
            drone_id: Unique drone identifier
            ip_address: Drone's WiFi IP address
            command_port: UDP port for commands
        """
        self.drone_id = drone_id
        self.ip_address = ip_address
        self.command_port = command_port

        # UDP socket for commands
        self.cmd_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Telemetry data
        self.telemetry = {
            'timestamp': 0,
            'roll': 0.0,
            'pitch': 0.0,
            'yaw': 0.0,
            'altitude': 0.0,
            'battery': 0.0,
            'armed': False,
            'mode': 0
        }

        self.last_telemetry_time = 0

        print(f"[DRONE {drone_id}] Interface initialized: {ip_address}:{command_port}")

    def arm(self):
        """Arm the drone motors."""
        self._send_command(self.CMD_ARM)
        print(f"[DRONE {self.drone_id}] ARM command sent")

    def disarm(self):
        """Disarm the drone motors."""
        self._send_command(self.CMD_DISARM)
        print(f"[DRONE {self.drone_id}] DISARM command sent")

    def set_mode(self, mode: int):
        """Set flight mode."""
        data = struct.pack('B', mode)
        self._send_command(self.CMD_SET_MODE, data)
        print(f"[DRONE {self.drone_id}] Mode set to: {mode}")

    def send_control_input(self, roll: float, pitch: float, yaw: float, throttle: float):
        """
        Send manual control inputs.

        Args:
            roll: Roll command (-1.0 to 1.0)
            pitch: Pitch command (-1.0 to 1.0)
            yaw: Yaw rate command (-1.0 to 1.0)
            throttle: Throttle (0.0 to 1.0)
        """
        data = struct.pack('ffff', roll, pitch, yaw, throttle)
        self._send_command(self.CMD_CONTROL_INPUT, data)

    def send_velocity_command(self, vx: float, vy: float, vz: float, vyaw: float):
        """
        Send velocity command (for autonomous control).

        This is what our swarm logic will use!

        Args:
            vx: X velocity (m/s)
            vy: Y velocity (m/s)
            vz: Z velocity (m/s, positive = up)
            vyaw: Yaw rate (rad/s)
        """
        data = struct.pack('ffff', vx, vy, vz, vyaw)
        self._send_command(self.CMD_VELOCITY_COMMAND, data)

    def send_position_target(self, x: float, y: float, z: float):
        """
        Send position target (for position hold mode).

        Args:
            x: Target X position (meters)
            y: Target Y position (meters)
            z: Target altitude (meters)
        """
        data = struct.pack('fff', x, y, z)
        self._send_command(self.CMD_POSITION_TARGET, data)

    def get_telemetry(self) -> Dict:
        """Get latest telemetry data."""
        return self.telemetry.copy()

    def is_connected(self) -> bool:
        """Check if receiving telemetry."""
        return (time.time() - self.last_telemetry_time) < 2.0

    def _send_command(self, cmd_type: int, data: bytes = b''):
        """Send command packet to drone."""
        packet = struct.pack('B', cmd_type) + data
        try:
            self.cmd_socket.sendto(packet, (self.ip_address, self.command_port))
        except Exception as e:
            print(f"[DRONE {self.drone_id}] Error sending command: {e}")

    def _update_telemetry(self, telemetry_data: Dict):
        """Update telemetry from received packet."""
        self.telemetry = telemetry_data
        self.last_telemetry_time = time.time()


class ESP32SwarmInterface:
    """
    Manages multiple ESP32 drones and integrates with swarm logic.

    This bridges our simulation code to real hardware!
    """

    def __init__(self, telemetry_port: int = 14550):
        """
        Initialize swarm interface.

        Args:
            telemetry_port: UDP port to listen for telemetry
        """
        self.drones: Dict[int, ESP32Drone] = {}
        self.telemetry_port = telemetry_port

        # Telemetry receiver
        self.telemetry_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.telemetry_socket.bind(('0.0.0.0', telemetry_port))
        self.telemetry_socket.settimeout(0.1)  # Non-blocking

        # Telemetry thread
        self.running = False
        self.telemetry_thread = None

        print(f"[SWARM] Interface initialized, listening on port {telemetry_port}")

    def add_drone(self, drone_id: int, ip_address: str):
        """Add a drone to the swarm."""
        drone = ESP32Drone(drone_id, ip_address)
        self.drones[drone_id] = drone
        print(f"[SWARM] Added drone {drone_id}: {ip_address}")

    def start(self):
        """Start telemetry receiver."""
        self.running = True
        self.telemetry_thread = threading.Thread(target=self._telemetry_loop, daemon=True)
        self.telemetry_thread.start()
        print("[SWARM] Telemetry receiver started")

    def stop(self):
        """Stop telemetry receiver."""
        self.running = False
        if self.telemetry_thread:
            self.telemetry_thread.join(timeout=1.0)
        print("[SWARM] Telemetry receiver stopped")

    def arm_all(self):
        """Arm all drones in swarm."""
        print("[SWARM] Arming all drones...")
        for drone in self.drones.values():
            drone.arm()
            time.sleep(0.1)

    def disarm_all(self):
        """Disarm all drones (EMERGENCY STOP)."""
        print("[SWARM] DISARMING ALL DRONES!")
        for drone in self.drones.values():
            drone.disarm()

    def set_all_mode(self, mode: int):
        """Set flight mode for all drones."""
        for drone in self.drones.values():
            drone.set_mode(mode)

    def send_swarm_velocities(self, velocities: Dict[int, np.ndarray]):
        """
        Send velocity commands to all drones.

        This integrates with our simulation!

        Args:
            velocities: Dict mapping drone_id to velocity vector [vx, vy, vz]
        """
        for drone_id, vel in velocities.items():
            if drone_id in self.drones:
                drone = self.drones[drone_id]
                drone.send_velocity_command(vel[0], vel[1], vel[2], 0.0)

    def get_swarm_states(self) -> List[Dict]:
        """
        Get telemetry from all drones in simulation format.

        Returns list compatible with our swarm simulator!
        """
        states = []
        for drone_id, drone in self.drones.items():
            telem = drone.get_telemetry()

            # Convert to simulation state format
            state = {
                'id': drone_id,
                'position': [0, telem['altitude'], 0],  # X, Y, Z (need external positioning)
                'velocity': [0, 0, 0],  # Would come from position derivative
                'color': [0.0, 1.0, 0.0],  # Green
                'role': 'seeker',
                'detected': False,
                'caught': False,
                'behavior_state': 'patrol',
                'battery': telem['battery'],
                'armed': telem['armed']
            }
            states.append(state)

        return states

    def check_connections(self):
        """Check which drones are connected."""
        connected = []
        disconnected = []

        for drone_id, drone in self.drones.items():
            if drone.is_connected():
                connected.append(drone_id)
            else:
                disconnected.append(drone_id)

        print(f"[SWARM] Connected: {connected}, Disconnected: {disconnected}")
        return connected, disconnected

    def _telemetry_loop(self):
        """Background thread to receive telemetry."""
        print("[SWARM] Telemetry loop started")

        while self.running:
            try:
                data, addr = self.telemetry_socket.recvfrom(1024)

                # Parse telemetry packet
                # Format: uint32 timestamp, 4x float (roll, pitch, yaw, alt, battery), bool armed, uint8 mode
                if len(data) >= 26:
                    timestamp, roll, pitch, yaw, altitude, battery = struct.unpack('Ifffff', data[:24])
                    armed = bool(data[24])
                    mode = data[25]

                    telemetry = {
                        'timestamp': timestamp,
                        'roll': roll,
                        'pitch': pitch,
                        'yaw': yaw,
                        'altitude': altitude,
                        'battery': battery,
                        'armed': armed,
                        'mode': mode
                    }

                    # Find which drone this came from (by IP)
                    sender_ip = addr[0]
                    for drone in self.drones.values():
                        if drone.ip_address == sender_ip:
                            drone._update_telemetry(telemetry)
                            break

            except socket.timeout:
                continue
            except Exception as e:
                print(f"[SWARM] Telemetry error: {e}")

        print("[SWARM] Telemetry loop stopped")


# ============================================================================
# INTEGRATION WITH SIMULATION
# ============================================================================

def integrate_with_simulator(swarm_interface: ESP32SwarmInterface, simulator):
    """
    Replace simulation drone control with real hardware control.

    This is the magic that connects everything!
    """

    # Override simulator's update method
    original_update = simulator.swarm.update

    def hardware_update(dt):
        """Custom update that sends commands to real drones."""

        # Run simulation logic (AI behaviors, game logic)
        original_update(dt)

        # Get desired velocities from simulation
        velocities = {}
        for drone in simulator.swarm.drones:
            # Calculate velocity from simulation
            # (In sim, drones have velocity attribute)
            velocities[drone.id] = drone.velocity

        # Send to real hardware!
        swarm_interface.send_swarm_velocities(velocities)

    # Replace update method
    simulator.swarm.update = hardware_update

    print("[INTEGRATION] Simulator connected to hardware!")


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("ESP32-C3 Swarm Hardware Interface Test")
    print("=" * 60)

    # Create swarm interface
    swarm = ESP32SwarmInterface(telemetry_port=14550)

    # Add drones (change IPs to match your drones)
    swarm.add_drone(1, "192.168.1.100")
    swarm.add_drone(2, "192.168.1.101")

    # Start telemetry receiver
    swarm.start()

    try:
        print("\nWaiting for telemetry...")
        time.sleep(2)

        # Check connections
        swarm.check_connections()

        # Arm all drones
        input("\nPress Enter to ARM drones (PROPS OFF!): ")
        swarm.arm_all()

        # Set to autonomous mode
        input("Press Enter to set AUTONOMOUS mode: ")
        swarm.set_all_mode(ESP32Drone.MODE_AUTONOMOUS)

        # Hover test
        print("\nSending hover commands...")
        for i in range(100):  # 10 seconds at 10Hz
            velocities = {
                1: np.array([0, 0, 0]),  # Hover in place
                2: np.array([0, 0, 0])
            }
            swarm.send_swarm_velocities(velocities)
            time.sleep(0.1)

            # Print telemetry
            for drone_id, drone in swarm.drones.items():
                telem = drone.get_telemetry()
                print(f"Drone {drone_id}: Alt={telem['altitude']:.2f}m Battery={telem['battery']:.1f}V")

        # Disarm
        print("\nLanding and disarming...")
        swarm.disarm_all()

    except KeyboardInterrupt:
        print("\nEmergency stop!")
        swarm.disarm_all()

    finally:
        swarm.stop()
        print("Test complete")
