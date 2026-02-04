"""HAL Demo: Control a single drone through the Hardware Abstraction Layer.

This script demonstrates controlling a drone using ONLY the HAL interface,
which is the same interface that will be used for real hardware.
No direct access to drone internals (set_target, position, etc).

Usage:
    python examples/hal_demo.py
"""

import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulation.simulator import Simulator


def main():
    print("=== HAL Demo: Single Drone Control ===\n")

    # Start simulator with default config
    sim = Simulator("config.yaml")
    sim.start()

    # Wait for auto-spawn
    time.sleep(1.0)

    # Get HAL for drone 0
    hal = sim.get_hal(0)
    if hal is None:
        print("[FAIL] Could not get HAL for drone 0")
        sim.stop()
        return

    print(f"Got HAL for drone {hal.drone_id}")

    # --- Read initial sensors ---
    gps = hal.get_gps()
    print(f"\nInitial GPS position: [{gps.position[0]:.2f}, {gps.position[1]:.2f}, {gps.position[2]:.2f}]")
    print(f"GPS fix type: {gps.fix_type}, accuracy H:{gps.accuracy_h:.1f}m V:{gps.accuracy_v:.1f}m")

    imu = hal.get_imu()
    print(f"IMU accel: [{imu.accel[0]:.3f}, {imu.accel[1]:.3f}, {imu.accel[2]:.3f}]")

    alt = hal.get_altitude()
    print(f"Altitude: baro={alt.altitude_baro:.2f}m, AGL={alt.altitude_agl:.2f}m")

    batt = hal.get_battery()
    print(f"Battery: {batt.remaining_pct:.1f}% ({batt.voltage:.2f}V)")

    status = hal.get_status()
    print(f"Status: mode={status.mode}, armed={status.armed}, airborne={status.airborne}")

    # --- Arm and takeoff ---
    print("\n--- Arming ---")
    result = hal.arm()
    print(f"Arm result: {result}")
    status = hal.get_status()
    print(f"Status after arm: mode={status.mode}, armed={status.armed}")

    # --- Command position via HAL ---
    print("\n--- Commanding position [10, 15, 5] via HAL ---")
    hal.set_position(10.0, 15.0, 5.0)

    # Wait and track progress
    for i in range(20):
        time.sleep(0.25)
        gps = hal.get_gps()
        speed = float(sum(v**2 for v in gps.velocity) ** 0.5)
        print(f"  t={i*0.25:4.1f}s  pos=[{gps.position[0]:6.2f}, {gps.position[1]:6.2f}, {gps.position[2]:6.2f}]  speed={speed:.2f} m/s")

    # --- Read final state ---
    print("\n--- Final sensor readings ---")
    gps = hal.get_gps()
    print(f"Final position: [{gps.position[0]:.2f}, {gps.position[1]:.2f}, {gps.position[2]:.2f}]")

    batt = hal.get_battery()
    print(f"Battery: {batt.remaining_pct:.1f}%")

    # --- Test velocity command ---
    print("\n--- Testing velocity command [2, 0, 0] for 2s ---")
    hal.set_velocity(2.0, 0.0, 0.0)
    for i in range(8):
        time.sleep(0.25)
        gps = hal.get_gps()
        print(f"  t={i*0.25:4.1f}s  pos=[{gps.position[0]:6.2f}, {gps.position[1]:6.2f}, {gps.position[2]:6.2f}]")

    # --- Land and disarm ---
    print("\n--- Landing ---")
    hal.land()
    time.sleep(3.0)
    gps = hal.get_gps()
    print(f"Position after land: [{gps.position[0]:.2f}, {gps.position[1]:.2f}, {gps.position[2]:.2f}]")

    hal.disarm()
    status = hal.get_status()
    print(f"Final status: mode={status.mode}, armed={status.armed}")

    # --- Verify all HAL methods for all drones ---
    print("\n--- Checking HAL for all drones ---")
    all_hals = sim.get_all_hals()
    print(f"Total drones with HAL: {len(all_hals)}")
    for drone_id, h in sorted(all_hals.items()):
        gps = h.get_gps()
        print(f"  Drone {drone_id}: pos=[{gps.position[0]:6.2f}, {gps.position[1]:6.2f}, {gps.position[2]:6.2f}]")

    sim.stop()
    print("\n=== HAL Demo Complete ===")


if __name__ == "__main__":
    main()
