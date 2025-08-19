#!/usr/bin/env python3
"""Test Shift key detection in pygame."""

import pygame
import sys

def test_shift_keys():
    pygame.init()
    screen = pygame.display.set_mode((400, 300))
    pygame.display.set_caption("Shift Key Test")
    clock = pygame.time.Clock()
    
    print("Shift key test started. Press keys to test:")
    print("- Regular keys: 1, 2, 3, 4, 5")
    print("- Shift+keys: Shift+1, Shift+2, etc.")
    print("- ESC to exit")
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                
            elif event.type == pygame.KEYDOWN:
                key_name = pygame.key.name(event.key)
                shift_pressed = bool(event.mod & pygame.KMOD_SHIFT)
                
                print(f"Key: {key_name}, Shift: {shift_pressed}")
                
                if key_name == 'escape':
                    running = False
                elif key_name in '12345':
                    if shift_pressed:
                        print(f"  -> SHIFT+{key_name} detected!")
                    else:
                        print(f"  -> Regular {key_name} detected")
        
        screen.fill((50, 50, 50))
        pygame.display.flip()
        clock.tick(60)
    
    pygame.quit()
    print("Test completed.")

if __name__ == "__main__":
    test_shift_keys()