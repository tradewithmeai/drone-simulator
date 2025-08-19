#!/usr/bin/env python3
"""Test the coordinate mapping system."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_coordinate_mapping():
    print("Testing coordinate mapping system...")
    print("=" * 50)
    
    from simulation.coords import map_up_axis, map_positions_list, get_bounding_box
    from simulation.spawn import make_positions
    
    # Test spawn positions
    positions = make_positions(5, 'line', 3.0, 10.0, 42)
    print("Original spawn positions (x, y_ground, z_altitude):")
    for i, pos in enumerate(positions):
        print(f"  Drone {i}: {pos}")
    
    # Test Y-up mapping
    print("\nY-up mapping (altitude->Y, ground->XZ):")
    y_up_positions = map_positions_list(positions, 'y')
    for i, pos in enumerate(y_up_positions):
        print(f"  Drone {i}: {pos}")
    
    # Test Z-up mapping  
    print("\nZ-up mapping (altitude->Z, ground->XY):")
    z_up_positions = map_positions_list(positions, 'z')
    for i, pos in enumerate(z_up_positions):
        print(f"  Drone {i}: {pos}")
    
    # Test bounding box calculation
    print("\nBounding box for Y-up positions:")
    min_pos, max_pos, centroid = get_bounding_box(y_up_positions)
    print(f"  Min: {min_pos}")
    print(f"  Max: {max_pos}")
    print(f"  Centroid: {centroid}")
    
    print("\nTest completed successfully!")

if __name__ == "__main__":
    test_coordinate_mapping()