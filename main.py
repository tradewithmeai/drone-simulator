#!/usr/bin/env python3
"""
Drone Swarm Simulator - Main Entry Point

This script starts the drone swarm simulation with or without GUI based on config.yaml
"""

import sys
import yaml
import time
import argparse
import signal
import atexit
from simulation.simulator import Simulator

# Global variables for cleanup
active_simulator = None
active_gui = None

def cleanup_handler():
    """Clean up resources on exit."""
    print("\n[EXIT] Cleaning up resources...")
    
    if active_simulator:
        print("[EXIT] Stopping simulator...")
        active_simulator.stop()
        
    if active_gui:
        print("[EXIT] Stopping GUI...")
        active_gui.running = False
        
    print("[EXIT] Cleanup completed")

def signal_handler(signum, frame):
    """Handle Ctrl+C and other signals."""
    print(f"\n[EXIT] Signal {signum} received, initiating shutdown...")
    try:
        cleanup_handler()
    except Exception as e:
        print(f"[EXIT] Cleanup error: {e}")
    
    # Force exit after brief delay
    import threading
    def force_exit():
        import time
        time.sleep(2)
        print("[EXIT] Force terminating...")
        import os
        os._exit(0)
    
    threading.Thread(target=force_exit, daemon=True).start()
    sys.exit(0)

# Register cleanup handlers
atexit.register(cleanup_handler)
signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
if hasattr(signal, 'SIGTERM'):
    signal.signal(signal.SIGTERM, signal_handler)  # Termination

def run_headless_simulation(config_path="config.yaml"):
    """Run simulation without GUI (headless mode)."""
    global active_simulator
    
    print("Starting headless drone swarm simulation...")
    
    simulator = Simulator(config_path)
    active_simulator = simulator  # Register for cleanup
    simulator.start()
    
    try:
        formation_patterns = ["line", "circle", "grid", "v_formation"]
        pattern_index = 0
        last_formation_time = time.time()
        
        print("Simulation running. Press Ctrl+C to stop.")
        print("Cycling through formations every 10 seconds...")
        
        while True:
            # Print simulation status
            sim_info = simulator.get_simulation_info()
            drone_states = simulator.get_drone_states()
            
            settled_count = sum(1 for drone in drone_states if drone['settled'])
            print(f"\\rFormation: {sim_info['current_formation']:<12} "
                  f"Progress: {sim_info['formation_progress']:.1%} "
                  f"Settled: {settled_count}/{len(drone_states)}", end="")
            
            # Change formation every 10 seconds
            if time.time() - last_formation_time > 10:
                formation = formation_patterns[pattern_index]
                simulator.set_formation(formation)
                pattern_index = (pattern_index + 1) % len(formation_patterns)
                last_formation_time = time.time()
                print(f"\\nSwitching to {formation} formation...")
                
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\\nStopping simulation...")
    finally:
        simulator.stop()

def run_gui_simulation(config_path="config.yaml"):
    """Run simulation with 3D GUI."""
    global active_gui
    
    try:
        from gui.main import DroneSwarmGUI
        print("Starting 3D GUI...")
        gui = DroneSwarmGUI(config_path)
        active_gui = gui  # Register for cleanup
        active_simulator = gui.simulator  # Register simulator for cleanup
        gui.run()
    except KeyboardInterrupt:
        print("\n[EXIT] Ctrl+C detected, shutting down GUI...")
        cleanup_handler()
    except ImportError as e:
        print(f"Error: GUI dependencies not available: {e}")
        print("Please install GUI dependencies:")
        print("  pip install pygame PyOpenGL PyOpenGL-accelerate")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting GUI: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Drone Swarm Simulator")
    parser.add_argument('--config', '-c', default='config.yaml', 
                       help='Configuration file path (default: config.yaml)')
    parser.add_argument('--headless', action='store_true',
                       help='Force headless mode (ignore GUI config)')
    parser.add_argument('--gui', action='store_true',
                       help='Force GUI mode (ignore config)')
    parser.add_argument('--safe-gui', action='store_true',
                       help='Run GUI in safe mode with minimal features')
    parser.add_argument('--no-spawn', action='store_true',
                       help='Ultra-safe mode: start with zero drones (manual spawn only)')
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file '{args.config}' not found.")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing configuration file: {e}")
        sys.exit(1)
    
    # Apply safe mode overrides if requested
    if args.no_spawn:
        print("ULTRA-SAFE MODE: Starting with zero drones (manual spawn only)")
        # Ultra-safe: no drones at startup, no auto-spawn
        config['drones']['count'] = 0
        config['gui']['auto_spawn_on_start'] = False
        config['gui']['enable_overlay'] = True  # Keep overlays for feedback
        
        # Save modified config
        with open(args.config + '.no-spawn', 'w') as f:
            yaml.dump(config, f)
        args.config = args.config + '.no-spawn'
        
    elif args.safe_gui:
        print("SAFE MODE: Applying minimal configuration for stability")
        # Reduce complexity for safe mode
        config['drones']['count'] = 4  # Reduce to 4 drones for stability testing
        config['gui']['show_fps'] = False
        config['gui']['show_sim_time'] = False
        config['gui']['show_formation_type'] = False
        config['gui']['show_labels'] = False
        config['gui']['show_formation_lines'] = False
        config['gui']['show_help'] = False
        config['gui']['enable_overlay'] = False
        config['gui']['auto_spawn_on_start'] = True  # ENABLE auto-spawn to test spawn system
        
        # Save modified config for GUI to use
        with open(args.config + '.safe', 'w') as f:
            yaml.dump(config, f)
        args.config = args.config + '.safe'
    
    # Determine whether to use GUI
    use_gui = config.get('use_gui', False)
    
    if args.headless:
        use_gui = False
    elif args.gui or args.safe_gui or args.no_spawn:
        use_gui = True
    
    # Start appropriate mode
    if use_gui:
        run_gui_simulation(args.config)
    else:
        run_headless_simulation(args.config)

if __name__ == "__main__":
    main()