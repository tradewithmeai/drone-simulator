#!/usr/bin/env python3
"""Simple GUI test to debug freezing issue."""

import sys
import pygame
from OpenGL.GL import *
from OpenGL.GLU import *

def main():
    """Test basic OpenGL setup."""
    print("Testing basic GUI setup...")
    
    # Initialize pygame
    pygame.init()
    
    # Set up display
    width, height = 800, 600
    screen = pygame.display.set_mode((width, height), pygame.DOUBLEBUF | pygame.OPENGL)
    pygame.display.set_caption("GUI Test")
    
    # Set up OpenGL
    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, width/height, 0.1, 100.0)
    glMatrixMode(GL_MODELVIEW)
    
    # Enable depth testing
    glEnable(GL_DEPTH_TEST)
    
    # Set clear color
    glClearColor(0.1, 0.1, 0.2, 1.0)
    
    clock = pygame.time.Clock()
    running = True
    frame_count = 0
    
    print("Starting render loop...")
    
    while running:
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
        
        # Simple camera position
        glTranslatef(0, 0, -10)
        
        # Draw a simple cube
        glRotatef(frame_count, 1, 1, 0)
        
        glBegin(GL_QUADS)
        # Front face (red)
        glColor3f(1.0, 0.0, 0.0)
        glVertex3f(-1, -1, 1)
        glVertex3f(1, -1, 1)
        glVertex3f(1, 1, 1)
        glVertex3f(-1, 1, 1)
        
        # Back face (green)
        glColor3f(0.0, 1.0, 0.0)
        glVertex3f(-1, -1, -1)
        glVertex3f(-1, 1, -1)
        glVertex3f(1, 1, -1)
        glVertex3f(1, -1, -1)
        
        # Top face (blue)
        glColor3f(0.0, 0.0, 1.0)
        glVertex3f(-1, 1, -1)
        glVertex3f(-1, 1, 1)
        glVertex3f(1, 1, 1)
        glVertex3f(1, 1, -1)
        
        # Bottom face (yellow)
        glColor3f(1.0, 1.0, 0.0)
        glVertex3f(-1, -1, -1)
        glVertex3f(1, -1, -1)
        glVertex3f(1, -1, 1)
        glVertex3f(-1, -1, 1)
        
        # Right face (magenta)
        glColor3f(1.0, 0.0, 1.0)
        glVertex3f(1, -1, -1)
        glVertex3f(1, 1, -1)
        glVertex3f(1, 1, 1)
        glVertex3f(1, -1, 1)
        
        # Left face (cyan)
        glColor3f(0.0, 1.0, 1.0)
        glVertex3f(-1, -1, -1)
        glVertex3f(-1, -1, 1)
        glVertex3f(-1, 1, 1)
        glVertex3f(-1, 1, -1)
        glEnd()
        
        # Swap buffers
        pygame.display.flip()
        
        # Control frame rate
        clock.tick(60)
        frame_count += 1
        
        if frame_count % 60 == 0:
            print(f"Frame {frame_count}, FPS: {clock.get_fps():.1f}")
    
    print("Exiting...")
    pygame.quit()

if __name__ == "__main__":
    main()