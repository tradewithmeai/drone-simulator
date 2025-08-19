#!/usr/bin/env python3
"""Debug version of GUI to find where it freezes."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import all modules at module level
import pygame
import yaml
from OpenGL.GL import *
from OpenGL.GLU import *

def main():
    print("Starting debug GUI...")
    
    print("1. Basic imports OK")
    
    print("2. Loading config...")
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        print(f"   Config loaded: GUI={config['use_gui']}")
    except Exception as e:
        print(f"   ERROR loading config: {e}")
        return
    
    print("3. Initializing pygame...")
    try:
        pygame.init()
        print("   Pygame initialized")
    except Exception as e:
        print(f"   ERROR initializing pygame: {e}")
        return
    
    print("4. Creating window...")
    try:
        width = config['gui']['window_width']
        height = config['gui']['window_height']
        screen = pygame.display.set_mode((width, height), pygame.DOUBLEBUF | pygame.OPENGL)
        pygame.display.set_caption("Debug GUI")
        print(f"   Window created: {width}x{height}")
    except Exception as e:
        print(f"   ERROR creating window: {e}")
        return
    
    print("5. Setting up OpenGL...")
    try:
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, width/height, 0.1, 1000.0)
        glMatrixMode(GL_MODELVIEW)
        glEnable(GL_DEPTH_TEST)
        glClearColor(0.1, 0.1, 0.2, 1.0)
        print("   OpenGL setup complete")
    except Exception as e:
        print(f"   ERROR setting up OpenGL: {e}")
        return
    
    print("6. Importing project modules...")
    try:
        from simulation.simulator import Simulator
        print("   Simulator imported")
        from gui.camera import Camera
        print("   Camera imported")
        from gui.renderer import Renderer
        print("   Renderer imported")
    except Exception as e:
        print(f"   ERROR importing project modules: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("7. Creating simulator...")
    try:
        simulator = Simulator('config.yaml')
        print("   Simulator created")
    except Exception as e:
        print(f"   ERROR creating simulator: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("8. Creating camera...")
    try:
        smooth_camera = config['gui'].get('smooth_camera', False)
        smoothing_factor = config['gui'].get('camera_smoothing', 0.1)
        camera = Camera([15, 15, 15], [0, 5, 0], smooth_camera, smoothing_factor)
        print(f"   Camera created (smooth={smooth_camera})")
    except Exception as e:
        print(f"   ERROR creating camera: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("9. Creating renderer...")
    try:
        background_color = config['gui']['background_color']
        renderer = Renderer(width, height, background_color)
        print("   Renderer created")
    except Exception as e:
        print(f"   ERROR creating renderer: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("10. Starting simulator...")
    try:
        simulator.start()
        print("   Simulator started")
    except Exception as e:
        print(f"   ERROR starting simulator: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("11. Starting render loop...")
    clock = pygame.time.Clock()
    running = True
    frame_count = 0
    
    try:
        while running and frame_count < 300:  # Limit to 300 frames for testing
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
            
            # Clear screen
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glLoadIdentity()
            
            # Apply camera
            camera.apply_view_matrix()
            
            # Draw something simple
            renderer.draw_grid()
            renderer.draw_axes()
            
            # Get drone states
            drone_states = simulator.get_drone_states()
            
            # Draw drones
            for drone_state in drone_states:
                position = drone_state['position']
                color = drone_state['color']
                renderer.draw_drone(position, color, 0.5, False)
            
            # Swap buffers
            pygame.display.flip()
            
            # Control frame rate
            clock.tick(60)
            frame_count += 1
            
            if frame_count % 60 == 0:
                print(f"   Frame {frame_count}, FPS: {clock.get_fps():.1f}, Drones: {len(drone_states)}")
        
        print("12. Stopping simulator...")
        simulator.stop()
        print("   Simulator stopped")
        
    except Exception as e:
        print(f"   ERROR in render loop: {e}")
        import traceback
        traceback.print_exc()
        simulator.stop()
    
    print("13. Cleaning up...")
    pygame.quit()
    print("Done!")

if __name__ == "__main__":
    main()