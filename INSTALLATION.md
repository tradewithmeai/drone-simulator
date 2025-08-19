# Installation Guide for Drone Swarm 3D Simulator

## Quick Install

### Option 1: Standard Installation
```bash
pip install -r requirements.txt
```

### Option 2: Using Install Script
```bash
python install.py
```

### Option 3: Windows Users
```batch
# Run the batch file
install.bat

# Or use Windows-specific requirements
pip install -r requirements-windows.txt
```

## Troubleshooting Common Issues

### Issue 1: PyOpenGL-accelerate fails to install

**Solution**: This is optional. The simulator works without it.
```bash
# Install without acceleration
pip install pygame numpy pyyaml PyOpenGL
```

### Issue 2: PyOpenGL fails on Windows

**Solution**: Use PyOpenGL-binary instead
```bash
pip install PyOpenGL-binary
```

### Issue 3: numpy version conflicts

**Solution**: Use minimal requirements
```bash
pip install -r requirements-minimal.txt
```

### Issue 4: "No module named OpenGL.GL"

**Solutions**:
1. Reinstall PyOpenGL:
   ```bash
   pip uninstall PyOpenGL PyOpenGL-accelerate
   pip install PyOpenGL
   ```

2. On Windows, download wheel from:
   https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyopengl
   
   Then install:
   ```bash
   pip install PyOpenGL‑3.1.7‑cp311‑cp311‑win_amd64.whl
   ```

### Issue 5: pygame fails to install

**Solution**: Ensure you have Python 3.7+ and upgrade pip
```bash
python -m pip install --upgrade pip
pip install pygame
```

## Manual Installation (Step by Step)

If automated installation fails, install each package manually:

```bash
# 1. Upgrade pip
python -m pip install --upgrade pip

# 2. Install numpy first (many packages depend on it)
pip install numpy

# 3. Install pygame
pip install pygame

# 4. Install PyYAML
pip install pyyaml

# 5. Install PyOpenGL (try binary version on Windows)
pip install PyOpenGL
# OR on Windows:
pip install PyOpenGL-binary

# 6. Optional: Try PyOpenGL-accelerate
pip install PyOpenGL-accelerate
```

## Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## System Requirements

- **Python**: 3.7 or higher
- **Operating System**: Windows 10/11, macOS 10.14+, Linux (Ubuntu 20.04+)
- **Graphics**: OpenGL 3.3+ support
- **RAM**: 2GB minimum
- **Disk Space**: 200MB

## Verify Installation

Run this command to verify all dependencies are installed:

```python
python -c "
import pygame
import numpy
import yaml
from OpenGL.GL import *
print('✓ pygame:', pygame.version.ver)
print('✓ numpy:', numpy.__version__)
print('✓ PyYAML: installed')
print('✓ PyOpenGL: installed')
print('All dependencies verified!')
"
```

## Alternative: Using Conda

If pip installation fails, try Conda:

```bash
# Install Miniconda from: https://docs.conda.io/en/latest/miniconda.html

# Create environment
conda create -n drone-sim python=3.9

# Activate environment
conda activate drone-sim

# Install packages
conda install pygame numpy pyyaml
conda install -c conda-forge pyopengl
```

## Docker Option

For consistent environment across systems:

```dockerfile
FROM python:3.9
RUN apt-get update && apt-get install -y \
    python3-opengl \
    xvfb
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py", "--headless"]
```

## Getting Help

If you continue to have issues:

1. Check Python version: `python --version`
2. Check pip version: `pip --version`
3. Try in a fresh virtual environment
4. Post the full error message when asking for help
5. Include your OS and Python version

## Common Error Messages and Solutions

| Error | Solution |
|-------|----------|
| `No module named 'OpenGL'` | Install PyOpenGL or PyOpenGL-binary |
| `Microsoft Visual C++ 14.0 is required` | Install Visual Studio Build Tools |
| `error: Microsoft Visual C++ 14.0 is required` | Use pre-compiled wheels or conda |
| `ImportError: DLL load failed` | Reinstall with binary wheels |
| `pygame.error: video system not initialized` | Ensure you have display drivers installed |

## Next Steps

Once installation is complete:
1. Run `python main.py` to start the simulator with GUI
2. Run `python main.py --headless` for console-only mode
3. See `docs/RUN.md` for usage instructions