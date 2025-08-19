# Drone Swarm 3D Simulator

A comprehensive Python-based drone swarm simulation system with real-time 3D visualization, interactive controls, and advanced GUI features.

## 🚁 Overview

This project implements a sophisticated 3D drone swarm simulator with real-time physics simulation, multiple formation patterns, and an immersive OpenGL-based visualization system. Built in Python with PyOpenGL and Pygame, it provides both educational and research capabilities for drone swarm behavior analysis.

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
pip install PyYAML pygame PyOpenGL numpy
```

### Basic Usage

```bash
# Test dependencies and core functionality
python main.py --headless

# Run GUI in safe mode (minimal features for stability testing)
python main.py --safe-gui

# Run full GUI with all features
python main.py
```

## 🧪 Troubleshooting & Testing

### Step-by-Step Debugging

If you experience crashes or GUI issues, follow these steps to isolate the problem:

#### 1. Test Headless Mode
```bash
python main.py --headless
```
**Expected:** Console output showing drones spawning, moving, and forming patterns  
**If this fails:** Core simulation issue - check dependencies and config

#### 2. Test Safe GUI Mode
```bash
python main.py --safe-gui
```
**Expected:** Minimal GUI with 6 drones, no overlays, stable rendering  
**If this fails:** OpenGL/graphics driver issue

#### 3. Test Full GUI
```bash
python main.py
```
**Expected:** Full featured GUI with overlays, 9 drones, all controls working

### Safe Mode Features

Safe mode (`--safe-gui`) automatically disables potentially problematic features:
- Reduces drones to 6 (from 9)
- Disables all overlays (FPS, labels, formation info)  
- Disables formation connection lines
- Maintains auto-spawn and basic 3D rendering

## 🎮 Controls

### Camera Controls
- **WASD/QE**: Move camera in 3D space
- **Mouse drag**: Rotate camera around target
- **Mouse wheel**: Zoom in/out
- **R**: Reset camera to default position
- **Home**: Frame swarm (center camera on all drones)
- **6-9**: Lock camera to follow specific drone

### Formation Controls
- **1**: Line formation
- **2**: Circle formation  
- **3**: Grid formation
- **4**: V-formation
- **0**: Idle (maintain current positions)

### Spawning Controls
- **Shift+1**: Respawn drones in Line formation
- **Shift+2**: Respawn drones in Circle formation
- **Shift+3**: Respawn drones in Grid formation
- **Shift+4**: Respawn drones in V formation
- **Shift+5**: Respawn drones in Random formation

### Display Toggles
- **T**: Toggle target position indicators
- **G**: Toggle ground grid
- **X**: Toggle coordinate axes
- **C/F**: Toggle formation connection lines
- **L**: Toggle drone ID labels

### Simulation Controls
- **P**: Pause/Resume simulation
- **O**: Step simulation one tick (when paused)
- **H**: Toggle help overlay
- **ESC**: Exit application

## ⚙️ Configuration

Edit `config.yaml` to customize behavior:

```yaml
gui:
  enable_overlay: true         # Master switch for all overlays
  show_fps: true              # FPS counter
  show_formation_lines: true   # Formation connection lines
  
drones:
  count: 9                    # Number of drones
  spawn_preset: v             # Initial formation: v|line|circle|grid|random
```

## 📊 Performance & Diagnostics

The GUI automatically logs diagnostic information every 5 seconds:
- Current FPS and performance
- Number of active drones  
- Camera position
- Overlay status

Example output:
```
[DIAGNOSTIC] Time: 15.2s | FPS: 58.3 | Drones: 9 | Camera: (15.0, 15.0, 15.0) | Overlay: True | Formation: v_formation
```

## 🔧 Technical Features

- **Optimized rendering**: Persistent textures, batched operations
- **Thread-safe simulation**: Separate simulation and GUI threads
- **Error handling**: Graceful degradation when components fail
- **Coordinate mapping**: Y-up coordinate system with auto-spawn
- **Safe mode**: Stability testing with minimal features

## 📁 Project Structure

```
drone-swarm-3d-sim/
├── simulation/              # Core simulation engine
│   ├── drone.py            # Individual drone physics
│   ├── swarm.py            # Swarm formation control
│   ├── spawn.py            # Formation spawn positions
│   ├── coords.py           # Coordinate system mapping
│   └── simulator.py        # Main simulation loop
├── gui/                    # 3D visualization
│   ├── main.py             # GUI entry point  
│   ├── camera.py           # 3D camera controls
│   ├── renderer.py         # OpenGL rendering
│   └── overlay.py          # HUD text overlays
├── config.yaml             # Simulation configuration
└── main.py                 # Application entry point
```