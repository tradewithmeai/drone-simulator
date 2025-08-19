#!/usr/bin/env python3
"""Debug the GUI and drone creation."""

import sys
import os
import time
import pygame
from OpenGL.GL import *
from OpenGL.GLU import *

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def debug_drone_creation():
    print("=== DEBUGGING DRONE CREATION ===")
    
    # Test 1: Check config loading
    try:
        import yaml
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        print(f"✓ Config loaded - drones count: {config['drones']['count']}")
        print(f"✓ Spawn preset: {config['drones']['spawn_preset']}")
        print(f"✓ Spawn altitude: {config['drones']['spawn_altitude']}")
    except Exception as e:
        print(f"✗ Config loading failed: {e}")
        return
    
    # Test 2: Test simulator creation
    try:
        from simulation.simulator import Simulator
        sim = Simulator()
        print(f"✓ Simulator created")
        print(f"✓ Swarm has {len(sim.swarm.drones)} drones")
        
        # Check drone positions
        for i, drone in enumerate(sim.swarm.drones):
            print(f"  Drone {i}: pos={drone.position}, target={drone.target_position}")
            
    except Exception as e:
        print(f"✗ Simulator creation failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test 3: Test callback mechanism
    callback_called = False
    callback_data = None
    
    def test_callback(states, info):
        nonlocal callback_called, callback_data
        callback_called = True
        callback_data = (states, info)
        print(f"✓ Callback called with {len(states)} drone states")
    
    sim.set_state_callback(test_callback)
    
    # Start simulation briefly
    sim.start()
    time.sleep(0.5)
    sim.stop()
    
    if callback_called:
        states, info = callback_data
        print(f"✓ Callback received {len(states)} drone states")
        for i, state in enumerate(states):
            pos = state['position']
            print(f"  State {i}: pos=[{pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f}]")
    else:
        print(f"✗ Callback was never called")
    
    print("=== DEBUG COMPLETE ===")

def debug_minimal_gui():
    print("=== TESTING MINIMAL GUI ===")
    
    try:
        # Initialize pygame
        pygame.init()
        screen = pygame.display.set_mode((400, 300), pygame.DOUBLEBUF | pygame.OPENGL)
        pygame.display.set_caption("Debug GUI")
        
        # Basic OpenGL setup
        glEnable(GL_DEPTH_TEST)
        glClearColor(0.1, 0.1, 0.2, 1.0)
        
        # Set up perspective
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, 400/300, 0.1, 100.0)
        
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        gluLookAt(10, 10, 10,  # Camera position
                  0, 5, 0,     # Look at
                  0, 1, 0)     # Up vector
        
        # Create simulator
        from simulation.simulator import Simulator
        sim = Simulator()
        
        # Store drone states
        drone_states = []
        sim_info = {}
        
        def update_callback(states, info):
            nonlocal drone_states, sim_info
            drone_states = states
            sim_info = info
        
        sim.set_state_callback(update_callback)
        sim.start()
        
        print("✓ Minimal GUI started - press ESC to exit")
        print(f"✓ Watching {len(sim.swarm.drones)} drones")
        
        clock = pygame.time.Clock()
        running = True
        frame_count = 0
        
        while running and frame_count < 300:  # Run for 5 seconds max
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    running = False
            
            # Clear screen
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            
            # Draw coordinate axes
            glBegin(GL_LINES)
            # X axis - red
            glColor3f(1.0, 0.0, 0.0)
            glVertex3f(0, 0, 0)
            glVertex3f(5, 0, 0)
            # Y axis - green
            glColor3f(0.0, 1.0, 0.0)
            glVertex3f(0, 0, 0)
            glVertex3f(0, 5, 0)
            # Z axis - blue
            glColor3f(0.0, 0.0, 1.0)
            glVertex3f(0, 0, 0)
            glVertex3f(0, 0, 5)
            glEnd()
            
            # Draw drones as simple spheres
            for i, state in enumerate(drone_states):
                pos = state['position']
                color = state['color']
                
                glPushMatrix()
                glTranslatef(pos[0], pos[1], pos[2])
                glColor3f(color[0], color[1], color[2])
                
                # Draw a simple cube instead of sphere
                glBegin(GL_QUADS)
                # Front face
                glVertex3f(-0.5, -0.5, 0.5)
                glVertex3f(0.5, -0.5, 0.5)
                glVertex3f(0.5, 0.5, 0.5)
                glVertex3f(-0.5, 0.5, 0.5)
                # Back face  
                glVertex3f(-0.5, -0.5, -0.5)
                glVertex3f(-0.5, 0.5, -0.5)
                glVertex3f(0.5, 0.5, -0.5)
                glVertex3f(0.5, -0.5, -0.5)
                glEnd()
                
                glPopMatrix()
            
            pygame.display.flip()
            clock.tick(60)
            frame_count += 1
            
            if frame_count % 60 == 0:  # Print every second
                print(f"Frame {frame_count}: {len(drone_states)} drones visible")
        
        sim.stop()
        pygame.quit()
        print("✓ Minimal GUI test completed")
        
    except Exception as e:
        print(f"✗ Minimal GUI failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_drone_creation()
    print()
    debug_minimal_gui()