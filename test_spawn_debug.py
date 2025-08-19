#!/usr/bin/env python3
"""Debug script to test spawn system without GUI."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_spawn_system():
    print("Testing spawn system components...")
    print("=" * 50)
    
    # Test 1: Import spawn module
    try:
        from simulation.spawn import make_positions, get_preset_names
        print("[OK] spawn module imported successfully")
        
        presets = get_preset_names()
        print(f"[OK] Available presets: {presets}")
        
        # Test each preset
        for preset in presets:
            positions = make_positions(5, preset, 3.0, 5.0, 42)
            print(f"[OK] {preset}: generated {len(positions)} positions")
            if positions:
                print(f"  First position: {positions[0]}")
                
    except Exception as e:
        print(f"[ERROR] spawn module failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Create swarm with spawn settings
    try:
        from simulation.swarm import Swarm
        colors = [[1,0,0], [0,1,0], [0,0,1]]
        swarm = Swarm(5, colors, 3.0, "line", 5.0, 42)
        print(f"✓ Swarm created with {len(swarm.drones)} drones")
        print(f"✓ Spawn preset: {swarm.spawn_preset}")
        
        # Test drone positions
        for i, drone in enumerate(swarm.drones):
            print(f"  Drone {i}: position {drone.position}")
            
    except Exception as e:
        print(f"✗ Swarm creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    # Test 3: Test respawn functionality
    try:
        print("\nTesting respawn functionality...")
        original_positions = [drone.position.copy() for drone in swarm.drones]
        print("Original positions saved")
        
        swarm.respawn_formation("circle", 5)
        print(f"✓ Respawned to circle formation")
        print(f"✓ New spawn preset: {swarm.spawn_preset}")
        
        # Check if positions changed
        new_positions = [drone.position.copy() for drone in swarm.drones]
        positions_changed = any(
            orig != new for orig, new in zip(original_positions, new_positions)
        )
        
        if positions_changed:
            print("✓ Drone positions changed after respawn")
            for i, (old, new) in enumerate(zip(original_positions, new_positions)):
                print(f"  Drone {i}: {old} -> {new}")
        else:
            print("✗ Drone positions did not change!")
            return False
            
    except Exception as e:
        print(f"✗ Respawn test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 4: Test simulator integration
    try:
        print("\nTesting simulator integration...")
        from simulation.simulator import Simulator
        
        # Test if we can create simulator
        sim = Simulator()
        print(f"✓ Simulator created")
        print(f"✓ Swarm has {len(sim.swarm.drones)} drones")
        print(f"✓ Spawn preset: {sim.swarm.spawn_preset}")
        
        # Test respawn through simulator
        original_count = len(sim.swarm.drones)
        sim.respawn_formation("v")
        new_count = len(sim.swarm.drones)
        
        print(f"✓ Simulator respawn: {original_count} -> {new_count} drones")
        print(f"✓ New spawn preset: {sim.swarm.spawn_preset}")
        
    except Exception as e:
        print(f"✗ Simulator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 50)
    print("✓ All spawn system tests passed!")
    return True

if __name__ == "__main__":
    success = test_spawn_system()
    if not success:
        print("\n✗ Some tests failed. Check the errors above.")
        sys.exit(1)
    else:
        print("\n🎉 Spawn system is working correctly!")