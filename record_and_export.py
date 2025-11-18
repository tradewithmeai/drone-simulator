#!/usr/bin/env python
"""
Record a hide-and-seek game session and export to web viewer.
"""
import time
import json
import argparse
from simulation.simulator import Simulator
from simulation.recorder import SimulationRecorder


def record_game_session(duration=30, output_html="game_replay.html"):
    """
    Record a game session and export to HTML viewer.

    Args:
        duration: How long to record (seconds)
        output_html: Output HTML filename
    """
    print("=" * 60)
    print("RECORDING HIDE-AND-SEEK GAME SESSION")
    print("=" * 60)

    # Create simulator
    sim = Simulator('config.yaml')

    # Create recorder
    recorder = SimulationRecorder()

    # Start simulator thread
    sim.start()
    time.sleep(0.5)

    # Start game
    print("\n[RECORD] Starting game...")
    sim.start_game()
    time.sleep(1.0)

    # Start recording
    game_config = sim.config.get('game', {})
    recorder.start_recording(
        environment=sim.environment,
        game_config=game_config
    )

    # Record frames
    print(f"[RECORD] Recording for {duration} seconds...")
    print("[RECORD] Press Ctrl+C to stop early\n")

    start_time = time.time()
    frame_count = 0

    try:
        while time.time() - start_time < duration:
            # Get current state
            drone_states = sim.get_drone_states()
            sim_info = sim.get_simulation_info()
            game_status = sim_info.get('game_status')

            # Record frame
            recorder.record_frame(drone_states, game_status)
            frame_count += 1

            # Print progress
            elapsed = time.time() - start_time
            if frame_count % 60 == 0:  # Every second
                if game_status:
                    print(f"[{elapsed:5.1f}s] "
                          f"Caught: {game_status['caught_count']}/{game_status['total_hiders']} | "
                          f"Time: {game_status['remaining_time']:5.1f}s | "
                          f"Frames: {frame_count}")

            # Check if game ended
            if game_status and not game_status['active'] and game_status.get('winner'):
                print(f"\n[RECORD] Game ended! Winner: {game_status['winner'].upper()}")
                time.sleep(2.0)  # Record a bit more after win
                break

            time.sleep(1/60)  # ~60 FPS recording

    except KeyboardInterrupt:
        print("\n[RECORD] Recording stopped by user")

    # Stop recording
    recorder.stop_recording()
    print(recorder.get_summary())

    # Export to JSON
    json_file = "simulation_data.json"
    recorder.export_to_json(json_file)

    # Create HTML viewer
    print(f"\n[EXPORT] Creating web viewer: {output_html}")

    # Read template
    with open('viewer_template.html', 'r') as f:
        template = f.read()

    # Read recorded data
    with open(json_file, 'r') as f:
        simulation_data = f.read()

    # Inject data into template
    html_content = template.replace('{{SIMULATION_DATA}}', simulation_data)

    # Write final HTML
    with open(output_html, 'w') as f:
        f.write(html_content)

    # Stop simulator
    sim.stop()

    print("=" * 60)
    print("EXPORT COMPLETE!")
    print("=" * 60)
    print(f"\n✅ Recorded {frame_count} frames")
    print(f"✅ Duration: {elapsed:.1f} seconds")
    print(f"✅ Web viewer: {output_html}")
    print(f"\n🌐 Open '{output_html}' in your web browser to watch the game!")
    print("\nControls:")
    print("  ▶ Play/Pause - Start/stop playback")
    print("  ⟲ Restart - Jump to beginning")
    print("  Timeline - Click to jump to any point")
    print("  Speed - Adjust playback speed (0.25x to 4x)")
    print("  Mouse drag - Rotate camera")
    print("  Mouse wheel - Zoom in/out")

    return output_html


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Record hide-and-seek game and export to web viewer')
    parser.add_argument('--duration', type=int, default=30, help='Recording duration in seconds')
    parser.add_argument('--output', type=str, default='game_replay.html', help='Output HTML filename')

    args = parser.parse_args()

    record_game_session(duration=args.duration, output_html=args.output)
