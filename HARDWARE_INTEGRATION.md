# 🔧 Hardware Integration Guide
## From Simulation to Real Flying Drones

This guide shows you how to build ESP32-C3 based drones and run the hide-and-seek game on real hardware.

---

## 📦 Complete System Overview

```
┌─────────────────────────────────────────────────────────┐
│                  COMPLETE SYSTEM                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Ground Station (Python)                                │
│  ├── Swarm Logic (simulation/game.py)                  │
│  ├── AI Behaviors (hide, seek, patrol)                 │
│  ├── Hardware Interface (hardware/esp32_interface.py)  │
│  └── WiFi Communication                                 │
│         │                                                │
│         ▼ (UDP Commands)                                │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  Drone #1    │  │  Drone #2    │  │  Drone #3    │ │
│  │              │  │              │  │              │ │
│  │ ESP32-C3     │  │ ESP32-C3     │  │ ESP32-C3     │ │
│  │ Flight Ctrl  │  │ Flight Ctrl  │  │ Flight Ctrl  │ │
│  │ MPU6050 IMU  │  │ MPU6050 IMU  │  │ MPU6050 IMU  │ │
│  │ 4x Motors    │  │ 4x Motors    │  │ 4x Motors    │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│         │                 │                 │           │
│         └─────────────────┴─────────────────┘           │
│                   (WiFi Network)                        │
└─────────────────────────────────────────────────────────┘
```

---

## 🛠️ Part 1: Building a Drone

### Bill of Materials (Per Drone)

| Component | Specs | Qty | Cost (USD) |
|-----------|-------|-----|------------|
| ESP32-C3 Mini | RISC-V, WiFi | 1 | $3 |
| MPU6050 IMU | 6-axis gyro+accel | 1 | $2 |
| ESCs | 20A, BLHeli | 4 | $20 |
| Brushless Motors | 2204 2300KV | 4 | $40 |
| Propellers | 5045 (2CW + 2CCW) | 4 | $5 |
| Frame | 210mm carbon fiber | 1 | $25 |
| LiPo Battery | 3S 1500mAh 75C | 1 | $20 |
| Power Distribution | 5V BEC included | 1 | $5 |
| Misc | Wires, connectors | - | $10 |
| **TOTAL** | | | **~$130** |

### Tools Needed
- Soldering iron
- Multimeter
- Hex drivers (1.5mm, 2.0mm)
- Wire strippers
- Heat shrink tubing
- Zip ties

### Assembly Steps

#### 1. Frame Assembly
```
1. Install 4 arms to center plate
2. Mount motors to arms (2 CW, 2 CCW)
3. Check motor rotation direction
4. Secure with Loctite
```

#### 2. Electronics Installation
```
1. Mount PDB (Power Distribution Board) to frame
2. Solder ESC power leads to PDB
3. Solder battery connector to PDB
4. Connect ESP32-C3:
   - 5V from BEC → ESP32 VIN
   - GND → ESP32 GND
   - ESC signals → GPIO 2,3,4,5
```

#### 3. IMU Installation
```
1. Mount MPU6050 on vibration dampener
2. Align with drone's forward direction
3. Connect I2C:
   - SDA → GPIO 6
   - SCL → GPIO 7
   - VCC → 3.3V
   - GND → GND
```

#### 4. Battery Monitor
```
Voltage Divider Circuit:

Battery+ ──[10kΩ]──┬──[3.3kΩ]── GND
                   │
                   └─→ GPIO 8

Calculation:
For 3S (12.6V max):
Vout = 12.6V * (3.3kΩ / (10kΩ + 3.3kΩ)) = 3.13V ✓
```

#### 5. Wiring Diagram
```
                ESP32-C3 Mini
                ┌─────────────┐
    ESC1 ←─────│ GPIO 2      │
    ESC2 ←─────│ GPIO 3      │
    ESC3 ←─────│ GPIO 4      │
    ESC4 ←─────│ GPIO 5      │
                │             │
   SDA ───────→│ GPIO 6      │
   SCL ───────→│ GPIO 7      │
   VBatt ─────→│ GPIO 8      │
                │             │
   5V ────────→│ VIN    3.3V │──→ MPU6050 VCC
   GND ───────→│ GND     GND │──→ MPU6050 GND
                └─────────────┘
```

#### 6. Propeller Installation
```
FRONT (Forward)

M1 (CCW)        M2 (CW)
    \            /
     \    X    /
      \   │   /
       \  │  /
        \ │ /
         \│/
         /│\
        / │ \
       /  │  \
      /   │   \
     /    X    \
    /            \
M4 (CW)        M3 (CCW)

BACK

⚠️ Critical: Wrong props = instant crash!
```

---

## 💻 Part 2: Firmware Setup

### Step 1: Install Arduino IDE
```bash
# Download from: https://www.arduino.cc/en/software
# Install ESP32 board support (see firmware README)
```

### Step 2: Configure WiFi
Edit `firmware/esp32-c3-flight-controller/config.h`:
```cpp
#define WIFI_SSID       "DroneSwarm_5GHz"  // Your network
#define WIFI_PASSWORD   "YourPassword123"

#define DRONE_ID        1  // Unique per drone: 1, 2, 3, etc.
```

### Step 3: Upload Firmware
```
1. Connect ESP32-C3 via USB
2. Select Board: Tools → ESP32C3 Dev Module
3. Select Port: Tools → Port → (your port)
4. Click Upload (→)
5. Wait for "Done uploading"
6. Open Serial Monitor (115200 baud)
```

### Step 4: ESC Calibration
**CRITICAL - Do this ONCE per drone!**

```
1. Remove ALL propellers
2. Disconnect battery
3. In flight_controller.ino, uncomment:
   motors.calibrate();
4. Upload code
5. Follow serial monitor prompts:
   - Send MAX throttle
   - Connect battery
   - ESCs beep (confirming calibration)
   - Send MIN throttle
   - Calibration complete
6. Comment out motors.calibrate() again
7. Re-upload firmware
```

### Step 5: IMU Calibration
```
1. Place drone on LEVEL surface
2. Keep completely still
3. Power on
4. Wait 3 seconds (auto-calibration)
5. LED will blink slowly (ready)
```

### Step 6: Motor Direction Test
**Still NO propellers!**
```python
# Run from Python:
from hardware.esp32_interface import ESP32Drone

drone = ESP32Drone(1, "192.168.1.100")
drone.arm()
drone.send_control_input(0.1, 0, 0, 0.1)  # Slow spin

# Verify each motor spins correctly
# If wrong direction, swap any 2 motor wires
```

---

## 🐍 Part 3: Python Interface Setup

### Step 1: Install Dependencies
```bash
cd drone-simulator
pip install numpy

# Already have from simulation:
# - pygame
# - PyOpenGL
```

### Step 2: Test Individual Drone
```python
# test_single_drone.py

from hardware.esp32_interface import ESP32Drone, ESP32SwarmInterface
import time

# Create swarm interface
swarm = ESP32SwarmInterface(telemetry_port=14550)

# Add your drone (change IP!)
swarm.add_drone(1, "192.168.1.100")

# Start telemetry receiver
swarm.start()

# Wait for connection
time.sleep(2)
swarm.check_connections()

# Arm drone
print("Arming...")
swarm.arm_all()

# Hover test (2 seconds)
print("Hover test...")
for i in range(20):
    swarm.send_swarm_velocities({
        1: [0, 0, 0]  # vx, vy, vz = 0 (hover)
    })
    time.sleep(0.1)

# Disarm
print("Disarming...")
swarm.disarm_all()
swarm.stop()
```

### Step 3: Find Drone IP Addresses
```python
# On drone startup, check Serial Monitor:
# "IP Address: 192.168.1.XXX"

# Or scan network:
import socket

for i in range(100, 110):
    ip = f"192.168.1.{i}"
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0.1)
    try:
        sock.sendto(b'\x01', (ip, 14551))  # Send ARM
        print(f"Drone found at {ip}")
    except:
        pass
    sock.close()
```

---

## 🎮 Part 4: Running Hide-and-Seek on Real Drones

### Step 1: Modify Game Configuration
Edit `config.yaml`:
```yaml
game:
  enabled: true
  seeker_count: 1  # Start with 1 seeker for testing
  hider_count: 2   # 2 hiders
  game_duration: 60.0  # Shorter for battery life
  detection_radius: 3.0  # Meters (real-world scale)
  catch_radius: 1.0

  environment:
    play_area_size: 10.0  # Smaller area (10x10m)
    num_obstacles: 3  # Fewer obstacles (use real objects)
```

### Step 2: Create Hardware Game Script
```python
# hardware_hideandseek.py

import time
import numpy as np
from simulation.simulator import Simulator
from hardware.esp32_interface import ESP32SwarmInterface, integrate_with_simulator

print("=" * 60)
print("HIDE-AND-SEEK ON REAL DRONES!")
print("=" * 60)

# Create simulator (for game logic only)
sim = Simulator('config.yaml')

# Create hardware interface
swarm = ESP32SwarmInterface(telemetry_port=14550)

# Add your drones (CHANGE IPs!)
swarm.add_drone(1, "192.168.1.100")  # Seeker
swarm.add_drone(2, "192.168.1.101")  # Hider 1
swarm.add_drone(3, "192.168.1.102")  # Hider 2

# Start telemetry
swarm.start()

# Connect simulator to hardware
integrate_with_simulator(swarm, sim)

# Start simulation
sim.start()
time.sleep(1)

# Check all drones connected
connected, disconnected = swarm.check_connections()
if disconnected:
    print(f"ERROR: Drones not connected: {disconnected}")
    exit(1)

# ARM SEQUENCE
input("Ready to ARM? Props OFF! Press Enter...")
swarm.arm_all()
time.sleep(1)

# Set autonomous mode
swarm.set_all_mode(ESP32SwarmInterface.ESP32Drone.MODE_AUTONOMOUS)

# Start game
print("\nStarting hide-and-seek game...")
sim.start_game()

# Game loop (runs until time expires or all caught)
try:
    while True:
        # Get game status
        sim_info = sim.get_simulation_info()
        game_status = sim_info.get('game_status')

        if not game_status['active']:
            print(f"\nGAME OVER! Winner: {game_status['winner']}")
            break

        # Print status
        print(f"Time: {game_status['remaining_time']:5.1f}s | "
              f"Caught: {game_status['caught_count']}/{game_status['total_hiders']}")

        time.sleep(1)

except KeyboardInterrupt:
    print("\nEmergency stop!")

finally:
    # EMERGENCY DISARM
    print("Disarming all drones...")
    swarm.disarm_all()
    sim.stop()
    swarm.stop()
    print("Shutdown complete")
```

### Step 3: Safety Checklist
```
PRE-FLIGHT:
□ Prop guards installed
□ Battery fully charged
□ Open area (10x10m minimum)
□ No people nearby
□ Fire extinguisher ready
□ First aid kit available
□ Emergency stop button ready (Ctrl+C)

DURING FLIGHT:
□ Monitor battery voltage
□ Watch for erratic behavior
□ Be ready to disarm
□ Keep visual line of sight

POST-FLIGHT:
□ Disconnect battery immediately
□ Check for damage
□ Download logs
```

---

## 📊 Part 5: Tuning and Optimization

### PID Tuning Process
```
1. Start with default values in config.h
2. Hover test - should be stable
3. If oscillates:
   - Reduce P gain by 20%
   - Increase D gain by 50%
4. If sluggish:
   - Increase P gain by 20%
5. Repeat until smooth
```

### Battery Life Optimization
```
Typical 1500mAh 3S battery:
- Hover time: 8-10 minutes
- Active flying: 5-7 minutes
- Game duration: 3-5 minutes (recommended)

⚠️ Land at 3.5V per cell (10.5V for 3S)
```

### Communication Range
```
WiFi 2.4GHz:
- Indoor: 20-30 meters
- Outdoor: 50-100 meters
- Through walls: Significantly reduced

Tips:
- Use directional antenna on ground station
- Keep router central to play area
- Avoid metal obstacles
```

---

## 🔍 Troubleshooting

### Drone won't connect to WiFi
```
1. Check SSID/password in config.h
2. Verify router is 2.4GHz (NOT 5GHz)
3. Check Serial Monitor for errors
4. Try connecting laptop to same network
5. Reduce distance to router
```

### Drone flips on takeoff
```
Common causes:
1. Wrong propeller direction
2. Wrong motor rotation
3. ESCs not calibrated
4. IMU not calibrated
5. IMU mounted wrong orientation

Fix:
1. Re-check propeller installation
2. Test motors individually
3. Re-calibrate ESCs
4. Re-calibrate IMU on level surface
```

### Drift during hover
```
1. Recalibrate IMU (must be perfectly level)
2. Check frame is not bent
3. Verify all props are balanced
4. Add small I gain to PID
5. Check motor/ESC condition
```

### Lost control mid-flight
```
IMMEDIATE:
1. Press Ctrl+C (emergency disarm)
2. Or let safety timeout trigger (2 seconds)

CAUSES:
- WiFi packet loss
- Battery voltage drop
- EMI interference
- Software crash

PREVENTION:
- Monitor signal strength
- Fresh battery only
- Keep distance < 30m
- Test thoroughly on ground first
```

---

## 📈 Performance Expectations

### Control Loop Performance
```
ESP32-C3 @ 160MHz:
- Main loop: 500 Hz (2ms)
- IMU update: 1000 Hz
- WiFi latency: 10-30ms
- Total latency: 15-35ms

This is good enough for stable flight!
```

### Positioning Accuracy
```
Without GPS/external tracking:
- Altitude: ±0.5m (barometer)
- Horizontal: Drift (IMU integration errors)
- Need external position system for precision

With external tracking (OptiTrack, etc.):
- 3D position: ±1cm
- Perfect for swarm control
```

---

## 🚀 Next Steps

### Add GPS (Outdoor Flight)
```
1. Connect GPS module to UART
2. Enable GPS code in firmware
3. Wait for 3D fix before arming
4. Enable position hold mode
```

### Add Camera (Computer Vision)
```
1. Mount ESP32-CAM module
2. Stream video to ground station
3. Run detection on ground station
4. Send position updates to ESP32-C3
```

### Build Full Swarm (5+ Drones)
```
1. Build 5-10 identical drones
2. Flash firmware with unique IDs
3. Set up central WiFi access point
4. Run hide-and-seek with teams!
```

---

## 📝 Summary

**What You've Built:**
✅ Custom flight controller using ESP32-C3
✅ WiFi-based swarm communication
✅ Integration with Python game logic
✅ Real flying hide-and-seek drones!

**Total Cost:**
- Single drone: ~$130
- 3-drone swarm: ~$400
- 9-drone swarm: ~$1,200

**Time Required:**
- Build one drone: 4-6 hours
- Firmware setup: 1-2 hours
- Tuning/testing: 3-5 hours
- **Total: 8-13 hours per drone**

**Result:**
A working swarm of drones that can autonomously play hide-and-seek using AI behaviors, all controlled from Python!

---

## ⚠️ Final Safety Reminder

**NEVER:**
- Fly near people
- Fly indoors without prop guards
- Use damaged batteries
- Fly in rain
- Exceed your skill level

**ALWAYS:**
- Have emergency stop ready
- Monitor battery voltage
- Use prop guards
- Fly in open areas
- Follow local regulations

---

**Happy building and flying!** 🚁✨

For questions or issues, check:
- Firmware README: `firmware/esp32-c3-flight-controller/README.md`
- Python interface: `hardware/esp32_interface.py`
- Game documentation: `HIDEANDSEEK.md`
