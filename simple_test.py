#!/usr/bin/env python3
"""Simple test for spawn system."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # Test basic spawn
    from simulation.spawn import make_positions
    positions = make_positions(3, 'line', 3.0, 5.0, 42)
    print(f"Spawn test: {len(positions)} positions generated")
    for i, pos in enumerate(positions):
        print(f"  Drone {i}: {pos}")
    
    # Test swarm creation
    from simulation.swarm import Swarm
    colors = [[1,0,0], [0,1,0], [0,0,1]]
    swarm = Swarm(3, colors, 3.0, "line", 5.0, 42)
    print(f"Swarm created with {len(swarm.drones)} drones")
    
    # Test respawn
    print("Before respawn:")
    for i, drone in enumerate(swarm.drones):
        print(f"  Drone {i}: {drone.position}")
    
    swarm.respawn_formation("circle")
    print("After respawn to circle:")
    for i, drone in enumerate(swarm.drones):
        print(f"  Drone {i}: {drone.position}")
        
    print("Test completed successfully!")
    
except Exception as e:
    print(f"Test failed: {e}")
    import traceback
    traceback.print_exc()