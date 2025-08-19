#!/usr/bin/env python3
"""Simple debug test."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test 1: Spawn module
print("Testing spawn module...")
try:
    from simulation.spawn import make_positions
    positions = make_positions(3, 'line', 3.0, 5.0, 42)
    print(f"SUCCESS: Generated {len(positions)} positions")
    for i, pos in enumerate(positions):
        print(f"  {i}: {pos}")
except Exception as e:
    print(f"FAILED: {e}")

# Test 2: Drone creation
print("\nTesting drone creation...")
try:
    from simulation.drone import Drone
    drone = Drone(0, [1, 2, 3], [1, 0, 0])
    print(f"SUCCESS: Created drone at {drone.position}")
except Exception as e:
    print(f"FAILED: {e}")

# Test 3: Swarm creation  
print("\nTesting swarm creation...")
try:
    from simulation.swarm import Swarm
    colors = [[1,0,0], [0,1,0], [0,0,1]]
    swarm = Swarm(3, colors, 3.0, "line", 5.0, 42)
    print(f"SUCCESS: Created swarm with {len(swarm.drones)} drones")
    for i, drone in enumerate(swarm.drones):
        print(f"  Drone {i}: {drone.position}")
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\nDone.")