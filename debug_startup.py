#!/usr/bin/env python3
"""Debug startup issues by catching all exceptions."""

import sys
import os
import traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def debug_startup():
    print("Starting startup debug...")
    
    try:
        # Test config loading first
        print("1. Testing config loading...")
        import yaml
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        print(f"   Config loaded: {len(config)} sections")
        
        # Test simulator creation
        print("2. Testing simulator creation...")
        from simulation.simulator import Simulator
        sim = Simulator()
        print(f"   Simulator created with {len(sim.swarm.drones)} drones")
        
        # Test GUI creation (without running)
        print("3. Testing GUI creation...")
        from gui.main import DroneSwarmGUI
        gui = DroneSwarmGUI()
        print("   GUI object created successfully")
        
        # Test pygame initialization
        print("4. Testing pygame state...")
        import pygame
        print(f"   Pygame initialized: {pygame.get_init()}")
        
        print("\nAll components created successfully!")
        print("The crash must be in the GUI run loop...")
        
        return True
        
    except Exception as e:
        print(f"ERROR during startup: {e}")
        traceback.print_exc()
        return False

def test_minimal_gui():
    print("\nTesting minimal GUI startup...")
    
    try:
        import pygame
        from OpenGL.GL import glClear, GL_COLOR_BUFFER_BIT
        
        pygame.init()
        screen = pygame.display.set_mode((400, 300), pygame.DOUBLEBUF | pygame.OPENGL)
        pygame.display.set_caption("Minimal Test")
        
        print("Minimal GUI created successfully")
        
        # Quick test loop
        for i in range(10):
            glClear(GL_COLOR_BUFFER_BIT)
            pygame.display.flip()
            pygame.time.wait(100)
        
        pygame.quit()
        print("Minimal GUI test completed")
        return True
        
    except Exception as e:
        print(f"Minimal GUI failed: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if debug_startup():
        test_minimal_gui()
    else:
        print("Startup debug failed - fix errors above first")