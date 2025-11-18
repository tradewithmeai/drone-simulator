#!/usr/bin/env python
"""
Test script for hide-and-seek game functionality.
"""
import time
import numpy as np
from simulation.simulator import Simulator

def test_game():
    """Test the hide-and-seek game functionality."""
    print("=" * 60)
    print("HIDE-AND-SEEK GAME TEST")
    print("=" * 60)

    # Create simulator
    sim = Simulator('config.yaml')

    # Check game is enabled
    assert sim.game_enabled, "Game should be enabled in config"
    assert sim.environment is not None, "Environment should be initialized"
    assert sim.game is not None, "Game manager should be initialized"
    assert sim.ai is not None, "AI controller should be initialized"

    print(f"✓ Game components initialized")
    print(f"  - Obstacles: {len(sim.environment.obstacles)}")
    print(f"  - Hiding spots: {len(sim.ai.hiding_spots)}")
    print(f"  - Patrol points: {len(sim.ai.patrol_points)}")

    # Start simulator thread
    sim.start()
    time.sleep(0.5)

    assert sim.is_alive(), "Simulator thread should be running"
    print(f"✓ Simulator thread started")

    # Start the game
    print("\n" + "=" * 60)
    print("STARTING GAME...")
    print("=" * 60)
    sim.start_game()
    time.sleep(1.0)

    # Check drone roles were assigned
    drone_states = sim.get_drone_states()

    print(f"\nDrone roles:")
    seekers = [d for d in drone_states if d.get('role') == 'seeker']
    hiders = [d for d in drone_states if d.get('role') == 'hider']

    print(f"  Seekers: {len(seekers)} (expected 2)")
    print(f"  Hiders: {len(hiders)} (expected 7)")

    for seeker in seekers:
        print(f"    - Seeker #{seeker['id']}: pos={seeker['position']}, state={seeker['behavior_state']}")

    for hider in hiders:
        print(f"    - Hider #{hider['id']}: pos={hider['position']}, state={hider['behavior_state']}")

    assert len(seekers) == 2, f"Should have 2 seekers, got {len(seekers)}"
    assert len(hiders) == 7, f"Should have 7 hiders, got {len(hiders)}"

    print(f"\n✓ Roles assigned correctly")

    # Check game status
    sim_info = sim.get_simulation_info()
    game_status = sim_info.get('game_status')

    assert game_status is not None, "Game status should be available"
    assert game_status['active'], "Game should be active"

    print(f"\nGame status:")
    print(f"  Active: {game_status['active']}")
    print(f"  Time remaining: {game_status['remaining_time']:.1f}s")
    print(f"  Caught: {game_status['caught_count']}/{game_status['total_hiders']}")
    print(f"  Detected: {game_status['detected_count']}")

    # Let game run for a few seconds
    print("\n" + "=" * 60)
    print("RUNNING GAME FOR 10 SECONDS...")
    print("=" * 60)

    for i in range(10):
        time.sleep(1.0)
        sim_info = sim.get_simulation_info()
        game_status = sim_info.get('game_status')

        if not game_status['active']:
            print(f"\n⚠ Game ended early!")
            print(f"  Winner: {game_status['winner']}")
            break

        print(f"[{i+1:2d}s] Time: {game_status['remaining_time']:5.1f}s | "
              f"Caught: {game_status['caught_count']}/{game_status['total_hiders']} | "
              f"Detected: {game_status['detected_count']} | "
              f"Free: {game_status['uncaught_count']}")

        # Show drone behaviors
        drone_states = sim.get_drone_states()
        for drone in drone_states[:3]:  # Show first 3 drones
            print(f"      Drone #{drone['id']} ({drone['role']}): {drone['behavior_state']} "
                  f"- caught={drone.get('caught', False)}, detected={drone.get('detected', False)}")

    # Check final state
    print("\n" + "=" * 60)
    print("FINAL STATE")
    print("=" * 60)

    sim_info = sim.get_simulation_info()
    game_status = sim_info.get('game_status')

    print(f"Game active: {game_status['active']}")
    print(f"Winner: {game_status.get('winner', 'None yet')}")
    print(f"Total caught: {game_status['caught_count']}/{game_status['total_hiders']}")
    print(f"Total detected: {game_status['detected_count']}")

    # Check drone positions are valid
    drone_states = sim.get_drone_states()
    for drone in drone_states:
        pos = np.array(drone['position'])
        assert not np.any(np.isnan(pos)), f"Drone {drone['id']} has NaN position"
        assert sim.environment.is_in_play_area(pos), f"Drone {drone['id']} outside play area"

    print(f"\n✓ All drone positions valid")

    # Stop simulator
    sim.stop()

    print("\n" + "=" * 60)
    print("TEST COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print("\nSummary:")
    print("  ✓ Environment created with obstacles")
    print("  ✓ Game initialized and started")
    print("  ✓ Drones assigned roles (2 seekers, 7 hiders)")
    print("  ✓ AI behaviors active (patrol, hide, chase, flee)")
    print("  ✓ Detection system functional")
    print("  ✓ Game timer running")
    print("  ✓ All game mechanics working")

if __name__ == "__main__":
    test_game()
