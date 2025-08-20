#!/usr/bin/env python3
"""Smoke test for spawn system - verifies spawn commands work correctly."""

import sys
import time
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulation.simulator import Simulator

def test_spawn_headless():
    """Test spawn system in headless mode."""
    print("=== Smoke Test: Spawn System ===")
    
    # Create simulator with no-spawn config
    simulator = Simulator("config.yaml")
    
    # Override to start with 0 drones for testing
    simulator.auto_spawn_config['enabled'] = False
    simulator.swarm.drones.clear()
    
    print(f"Initial state: {len(simulator.swarm.drones)} drones")
    assert len(simulator.swarm.drones) == 0, "Should start with 0 drones"
    
    # Start simulation
    simulator.start()
    print("Simulation started")
    
    # Enqueue respawn command
    simulator.respawn_formation('line', num_drones=3)
    print("Respawn command enqueued")
    
    # Wait for processing
    time.sleep(0.5)
    
    # Check results
    info = simulator.get_simulation_info()
    drone_count = info['num_drones']
    
    print(f"Result: {drone_count} drones created")
    assert drone_count == 3, f"Expected 3 drones, got {drone_count}"
    
    # Stop simulation
    simulator.stop()
    
    print("[PASS] Smoke test PASSED: Spawn system works correctly")
    return True

if __name__ == "__main__":
    try:
        test_spawn_headless()
    except AssertionError as e:
        print(f"[FAIL] Smoke test FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Smoke test ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)