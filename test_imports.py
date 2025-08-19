#!/usr/bin/env python3
"""Test script to verify all imports work correctly."""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test all module imports."""
    print("Testing imports...")
    print("-" * 50)
    
    # Test standard library imports
    try:
        import sys
        import time
        import threading
        import math
        print("✓ Standard library imports OK")
    except ImportError as e:
        print(f"✗ Standard library import failed: {e}")
        return False
    
    # Test third-party imports
    try:
        import pygame
        print(f"✓ pygame {pygame.version.ver} imported")
    except ImportError as e:
        print(f"✗ pygame import failed: {e}")
        return False
    
    try:
        import numpy as np
        print(f"✓ numpy {np.__version__} imported")
    except ImportError as e:
        print(f"✗ numpy import failed: {e}")
        return False
    
    try:
        import yaml
        print(f"✓ yaml imported")
    except ImportError as e:
        print(f"✗ yaml import failed: {e}")
        return False
    
    try:
        import OpenGL.GL as GL
        import OpenGL.GLU as GLU
        print("✓ PyOpenGL imported")
    except ImportError as e:
        print(f"✗ PyOpenGL import failed: {e}")
        return False
    
    # Test project imports
    try:
        from simulation.drone import Drone
        print("✓ simulation.drone imported")
    except ImportError as e:
        print(f"✗ simulation.drone import failed: {e}")
        return False
    
    try:
        from simulation.swarm import Swarm
        print("✓ simulation.swarm imported")
    except ImportError as e:
        print(f"✗ simulation.swarm import failed: {e}")
        return False
    
    try:
        from simulation.simulator import Simulator
        print("✓ simulation.simulator imported")
    except ImportError as e:
        print(f"✗ simulation.simulator import failed: {e}")
        return False
    
    try:
        from gui.camera import Camera
        print("✓ gui.camera imported")
    except ImportError as e:
        print(f"✗ gui.camera import failed: {e}")
        return False
    
    try:
        from gui.renderer import Renderer
        print("✓ gui.renderer imported")
    except ImportError as e:
        print(f"✗ gui.renderer import failed: {e}")
        return False
    
    try:
        from gui.overlay import TextOverlay
        print("✓ gui.overlay imported")
    except ImportError as e:
        print(f"✗ gui.overlay import failed: {e}")
        return False
    
    try:
        from gui.main import DroneSwarmGUI
        print("✓ gui.main imported")
    except ImportError as e:
        print(f"✗ gui.main import failed: {e}")
        return False
    
    print("-" * 50)
    print("All imports successful!")
    return True

if __name__ == "__main__":
    success = test_imports()
    
    if success:
        print("\n✓ All modules imported successfully!")
        print("\nYou can now run:")
        print("  python main.py        # For GUI mode")
        print("  python main.py --headless  # For headless mode")
    else:
        print("\n✗ Some imports failed. Please check the errors above.")
        sys.exit(1)