# Drone Swarm 3D Simulator

A real-time 3D visualization system for drone swarm formation control and physics simulation.

## Features

- **Real-time 3D visualization** using PyOpenGL and Pygame
- **Interactive camera controls** with WASD movement, mouse rotation, and scroll zoom
- **Multiple formation patterns**: Line, Circle, Grid, and V-formation
- **Physics simulation** with acceleration limits and proportional control
- **Configurable simulation** via YAML configuration file
- **Dual mode operation**: 3D GUI or headless console mode

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run with 3D GUI
python main.py

# Or run headless
python main.py --headless
```

## Controls

- **1-4**: Formation patterns (Line, Circle, Grid, V)
- **WASD/QE**: Camera movement
- **Mouse**: Camera rotation and zoom
- **Space**: Pause/Resume
- **T/G/X/C**: Toggle display elements

## Project Structure

```
drone-swarm-3d-sim/
├── simulation/          # Core simulation engine
│   ├── drone.py        # Individual drone physics
│   ├── swarm.py        # Swarm formation control
│   └── simulator.py    # Main simulation loop
├── gui/                # 3D visualization
│   ├── main.py         # GUI entry point
│   ├── camera.py       # 3D camera controls
│   └── renderer.py     # OpenGL rendering
├── docs/
│   └── RUN.md          # Detailed usage instructions
├── config.yaml         # Simulation configuration
└── main.py             # Application entry point
```

## Documentation

See [docs/RUN.md](docs/RUN.md) for detailed usage instructions and configuration options.