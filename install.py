#!/usr/bin/env python3
"""
Installation helper script for Drone Swarm 3D Simulator
Handles common dependency installation issues
"""

import subprocess
import sys
import platform

def install_package(package):
    """Install a package using pip."""
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def main():
    print("Installing dependencies for Drone Swarm 3D Simulator...")
    print(f"Python version: {sys.version}")
    print(f"Platform: {platform.system()}")
    
    # Core dependencies
    packages = [
        "pygame>=2.5.0",
        "numpy>=1.23.0",
        "pyyaml>=6.0",
        "PyOpenGL>=3.1.6"
    ]
    
    # Install packages one by one
    for package in packages:
        try:
            print(f"\nInstalling {package}...")
            install_package(package)
            print(f"✓ {package} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install {package}")
            print(f"  Error: {e}")
            
            # Provide alternative suggestions
            if "PyOpenGL" in package:
                print("\n  PyOpenGL installation failed. Try:")
                print("  1. Install manually: pip install PyOpenGL")
                print("  2. On Windows, you might need: pip install PyOpenGL-binary")
                print("  3. Or download wheel from: https://www.lfd.uci.edu/~gohlke/pythonlibs/")
    
    # Try to install PyOpenGL-accelerate (optional, may fail on some systems)
    print("\nAttempting to install PyOpenGL-accelerate (optional)...")
    try:
        install_package("PyOpenGL-accelerate")
        print("✓ PyOpenGL-accelerate installed successfully")
    except:
        print("✗ PyOpenGL-accelerate installation failed (this is optional)")
        print("  The simulator will still work without acceleration")
    
    print("\n" + "="*50)
    print("Installation complete!")
    print("\nTo run the simulator:")
    print("  python main.py        # Run with GUI")
    print("  python main.py --headless  # Run without GUI")
    
    # Test imports
    print("\nTesting imports...")
    try:
        import pygame
        import numpy
        import yaml
        from OpenGL.GL import *
        print("✓ All required modules can be imported")
    except ImportError as e:
        print(f"✗ Import test failed: {e}")
        print("\nPlease resolve the import error before running the simulator")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())