#!/usr/bin/env python3
"""Debug just the simulation without GUI dependencies."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def debug_simulation():
    print("=== DEBUGGING SIMULATION ONLY ===")
    
    # Test config without yaml
    try:
        # Manual config instead of yaml
        config = {
            'drones': {
                'count': 5,
                'spawn_preset': 'line',
                'spawn_altitude': 5.0,
                'spacing': 3.0,
                'seed': 42,
                'size': 0.5,
                'colors': [[1,0,0], [0,1,0], [0,0,1], [1,1,0], [1,0,1]]
            },
            'simulation': {
                'update_rate': 60,
                'max_speed': 10.0,
                'max_acceleration': 5.0
            }
        }
        print("✓ Manual config created")
        
        # Test spawn directly
        from simulation.spawn import make_positions
        positions = make_positions(config['drones']['count'], 
                                 config['drones']['spawn_preset'],
                                 config['drones']['spacing'],
                                 config['drones']['spawn_altitude'],
                                 config['drones']['seed'])
        print(f"✓ Generated {len(positions)} spawn positions:")
        for i, pos in enumerate(positions):
            print(f"  Position {i}: {pos}")
        
        # Test swarm creation
        from simulation.swarm import Swarm
        swarm = Swarm(config['drones']['count'],
                     config['drones']['colors'],
                     config['drones']['spacing'],
                     config['drones']['spawn_preset'],
                     config['drones']['spawn_altitude'],
                     config['drones']['seed'])
        print(f"✓ Created swarm with {len(swarm.drones)} drones")
        
        # Check initial drone positions
        print("✓ Initial drone positions:")
        for i, drone in enumerate(swarm.drones):
            print(f"  Drone {i}: pos={drone.position}, target={drone.target_position}")
        
        # Test update
        swarm.update(0.016)  # 60 FPS = ~0.016 seconds per frame
        print("✓ Swarm update completed")
        
        # Test formation change
        swarm.set_formation('circle')
        print("✓ Set formation to circle")
        
        print("✓ New target positions:")
        for i, drone in enumerate(swarm.drones):
            print(f"  Drone {i}: target={drone.target_position}")
        
        # Test respawn
        print("\n--- Testing Respawn ---")
        old_positions = [drone.position.copy() for drone in swarm.drones]
        swarm.respawn_formation('grid')
        new_positions = [drone.position.copy() for drone in swarm.drones]
        
        print("✓ Respawn completed")
        print("Position changes:")
        for i, (old, new) in enumerate(zip(old_positions, new_positions)):
            changed = not all(abs(a-b) < 0.001 for a, b in zip(old, new))
            status = "CHANGED" if changed else "SAME"
            print(f"  Drone {i}: {old} -> {new} [{status}]")
        
        return True
        
    except Exception as e:
        print(f"✗ Simulation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = debug_simulation()
    if success:
        print("\n🎉 SIMULATION CORE IS WORKING!")
        print("The issue is likely with GUI dependencies (pygame, PyOpenGL) or GUI integration.")
    else:
        print("\n❌ SIMULATION CORE HAS ISSUES!")
        print("Fix simulation issues before testing GUI.")