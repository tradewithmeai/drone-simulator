#!/usr/bin/env python3
"""Test respawn in headless mode."""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_headless_respawn():
    print("Testing respawn in headless mode...")
    
    try:
        from simulation.simulator import Simulator
        
        # Create simulator
        sim = Simulator()
        print(f"Created simulator with {len(sim.swarm.drones)} drones")
        
        # Start simulation
        sim.start()
        print("Simulation started")
        
        # Wait a moment
        time.sleep(0.5)
        
        # Get initial positions
        initial_states = sim.get_drone_states()
        print("Initial drone positions:")
        for i, state in enumerate(initial_states):
            pos = state['position']
            print(f"  Drone {i}: [{pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f}]")
        
        print(f"Initial spawn preset: {sim.swarm.spawn_preset}")
        
        # Test respawn
        print("\nTesting respawn to circle formation...")
        sim.respawn_formation("circle")
        
        # Wait for update
        time.sleep(0.5)
        
        # Get new positions
        new_states = sim.get_drone_states()
        print("After respawn to circle:")
        for i, state in enumerate(new_states):
            pos = state['position']
            print(f"  Drone {i}: [{pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f}]")
            
        print(f"New spawn preset: {sim.swarm.spawn_preset}")
        
        # Check if positions changed
        positions_changed = False
        for i, (old, new) in enumerate(zip(initial_states, new_states)):
            old_pos = old['position']
            new_pos = new['position']
            if abs(old_pos[0] - new_pos[0]) > 0.1 or abs(old_pos[2] - new_pos[2]) > 0.1:
                positions_changed = True
                break
        
        if positions_changed:
            print("SUCCESS: Drone positions changed after respawn!")
        else:
            print("FAILURE: Drone positions did not change!")
        
        # Stop simulation
        sim.stop()
        print("Simulation stopped")
        
        return positions_changed
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_headless_respawn()
    if success:
        print("\nHeadless respawn test PASSED!")
    else:
        print("\nHeadless respawn test FAILED!")
        sys.exit(1)