# Running the Drone Swarm Simulator

This document explains how to run the drone swarm simulation in both GUI and headless modes.

## Prerequisites

### Install Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- `pygame` - For GUI window management and input handling
- `PyOpenGL` and `PyOpenGL-accelerate` - For 3D graphics rendering
- `numpy` - For mathematical operations
- `pyyaml` - For configuration file parsing

## Configuration

The simulation behavior is controlled by `config.yaml`. Key settings:

```yaml
# Enable/disable 3D GUI
use_gui: true

# GUI settings
gui:
  window_width: 1024
  window_height: 768
  background_color: [0.1, 0.1, 0.2]

# Simulation parameters
simulation:
  num_drones: 5
  update_rate: 60  # Hz
```

## Running the Simulation

### GUI Mode (3D Visualization)

To run with the 3D GUI (default when `use_gui: true` in config):

```bash
python main.py
```

Or force GUI mode regardless of config:

```bash
python main.py --gui
```

### Headless Mode (Console Only)

To run without GUI (default when `use_gui: false` in config):

```bash
python main.py --headless
```

### Using Custom Configuration

```bash
python main.py --config my_config.yaml
```

## GUI Controls

When running in GUI mode, you can interact with the simulation using:

### Camera Controls
- **WASD** - Move camera horizontally
- **Q/E** - Move camera up/down
- **Mouse drag** - Rotate camera around target
- **Mouse wheel** - Zoom in/out
- **R** - Reset camera to default position

### Formation Controls
- **1** - Line formation
- **2** - Circle formation
- **3** - Grid formation
- **4** - V-formation
- **0** - Idle (maintain current positions)

### Display Options
- **T** - Toggle target position indicators
- **G** - Toggle ground grid
- **X** - Toggle coordinate axes
- **C** - Toggle formation connection lines

### Simulation Controls
- **Space** - Pause/Resume simulation
- **ESC** - Exit application

## Visual Elements

### Drone Representation
- **Colored spheres** - Each drone is represented as a colored 3D sphere
- **Bright colors** - Drones glow brighter when they've reached their target position
- **Wireframe targets** - Small wireframe spheres show target positions (when enabled)

### Scene Elements
- **Ground grid** - Reference grid on the XZ plane
- **Coordinate axes** - Red (X), Green (Y), Blue (Z) axes from origin
- **Formation lines** - Gray lines connecting drones in formation patterns
- **Lighting** - 3D lighting for realistic shading

## Headless Mode Output

In headless mode, the simulation prints status information to the console:

```
Formation: circle        Progress: 85.4% Settled: 4/5
Switching to grid formation...
```

The headless mode automatically cycles through formation patterns every 10 seconds for demonstration purposes.

## Troubleshooting

### GUI Not Starting
1. Ensure all GUI dependencies are installed:
   ```bash
   pip install pygame PyOpenGL PyOpenGL-accelerate
   ```

2. Check your graphics drivers support OpenGL

3. Try running in headless mode to verify the simulation core works:
   ```bash
   python main.py --headless
   ```

### Performance Issues
1. Reduce the number of drones in `config.yaml`
2. Lower the update rate
3. Close other graphics-intensive applications

### Configuration Errors
- Verify `config.yaml` syntax is valid YAML
- Check that all required configuration sections are present
- Use the provided `config.yaml` as a template

## Examples

### Quick Start - GUI Mode
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run with GUI
python main.py

# 3. Try different formations with keys 1-4
# 4. Move around with WASD and mouse
```

### Headless Demo
```bash
# Run without GUI for 30 seconds
timeout 30 python main.py --headless
```

### Custom Configuration
```bash
# Create custom config
cp config.yaml my_config.yaml
# Edit my_config.yaml to change number of drones, etc.
python main.py --config my_config.yaml
```

## Next Steps

- Modify `config.yaml` to experiment with different drone counts and formations
- Explore the source code in `simulation/` and `gui/` directories
- Add new formation patterns by extending the `Swarm` class
- Customize drone colors and behaviors through configuration