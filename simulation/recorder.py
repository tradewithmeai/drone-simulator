"""
Simulation recorder for exporting gameplay to web-viewable format.
"""
import json
import time
from typing import List, Dict, Any
import numpy as np


class SimulationRecorder:
    """Records simulation state for playback in web viewer."""

    def __init__(self):
        self.frames = []
        self.obstacles = []
        self.events = []
        self.metadata = {}
        self.recording = False
        self.start_time = None

    def start_recording(self, environment=None, game_config=None):
        """Start recording simulation."""
        self.recording = True
        self.start_time = time.time()
        self.frames = []
        self.events = []

        # Record obstacles
        if environment:
            self.obstacles = []
            for obstacle in environment.obstacles:
                self.obstacles.append({
                    'position': obstacle.position.tolist(),
                    'size': obstacle.size.tolist()
                })

        # Record metadata
        self.metadata = {
            'start_time': self.start_time,
            'play_area_size': environment.play_area_size if environment else 50.0,
            'game_config': game_config or {}
        }

        print(f"[RECORDER] Started recording - {len(self.obstacles)} obstacles")

    def stop_recording(self):
        """Stop recording."""
        self.recording = False
        print(f"[RECORDER] Stopped recording - {len(self.frames)} frames, {len(self.events)} events")

    def record_frame(self, drone_states: List[Dict], game_status: Dict = None):
        """Record a single frame of simulation state."""
        if not self.recording:
            return

        timestamp = time.time() - self.start_time

        frame = {
            'timestamp': timestamp,
            'drones': []
        }

        # Record drone states
        for drone in drone_states:
            frame['drones'].append({
                'id': drone['id'],
                'position': drone['position'],
                'velocity': drone['velocity'],
                'color': drone['color'],
                'role': drone.get('role', 'hider'),
                'detected': drone.get('detected', False),
                'caught': drone.get('caught', False),
                'behavior_state': drone.get('behavior_state', 'idle')
            })

        # Record game status
        if game_status:
            frame['game_status'] = {
                'active': game_status.get('active', False),
                'remaining_time': game_status.get('remaining_time', 0),
                'caught_count': game_status.get('caught_count', 0),
                'total_hiders': game_status.get('total_hiders', 0),
                'winner': game_status.get('winner')
            }

        self.frames.append(frame)

    def record_event(self, event_type: str, data: Dict):
        """Record a game event (detection, catch, win)."""
        if not self.recording:
            return

        timestamp = time.time() - self.start_time

        event = {
            'timestamp': timestamp,
            'type': event_type,
            'data': data
        }

        self.events.append(event)
        print(f"[RECORDER] Event: {event_type} at t={timestamp:.1f}s")

    def export_to_json(self, filename: str):
        """Export recorded data to JSON file."""
        data = {
            'metadata': self.metadata,
            'obstacles': self.obstacles,
            'frames': self.frames,
            'events': self.events,
            'duration': self.frames[-1]['timestamp'] if self.frames else 0,
            'frame_count': len(self.frames)
        }

        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"[RECORDER] Exported {len(self.frames)} frames to {filename}")
        print(f"[RECORDER] Duration: {data['duration']:.1f}s")
        return filename

    def get_summary(self) -> str:
        """Get recording summary."""
        duration = self.frames[-1]['timestamp'] if self.frames else 0
        fps = len(self.frames) / duration if duration > 0 else 0

        return f"""
Recording Summary:
  Frames: {len(self.frames)}
  Duration: {duration:.1f}s
  FPS: {fps:.1f}
  Events: {len(self.events)}
  Obstacles: {len(self.obstacles)}
        """
