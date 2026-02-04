"""Tests for the REST + WebSocket API server (Phase 5).

Uses FastAPI's TestClient for synchronous HTTP tests (no real server needed).
"""

import sys
import os
import json
import time
import pytest
import numpy as np

# Ensure project root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient
from simulation.simulator import Simulator
from api.server import create_app
from api.serializers import (
    serialize_imu,
    serialize_gps,
    serialize_altitude,
    serialize_battery,
    serialize_status,
    serialize_ground_truth,
    serialize_drone_state,
)
from hal.types import IMUReading, GPSReading, AltitudeReading, BatteryReading, DroneStatus


# ── Fixtures ─────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def simulator():
    """Create a simulator with drones for the whole test module."""
    sim = Simulator("config.yaml")
    sim.start()
    # Wait for auto-spawn
    time.sleep(1.5)
    yield sim
    sim.stop()


@pytest.fixture(scope="module")
def client(simulator):
    """FastAPI TestClient backed by the module-scoped simulator."""
    app = create_app(simulator, ws_push_rate=10.0)
    return TestClient(app)


# ── Serializer unit tests ────────────────────────────────────────

class TestSerializers:
    def test_serialize_imu(self):
        reading = IMUReading(
            timestamp=1.0,
            accel=np.array([1.0, 2.0, 3.0]),
            gyro=np.array([0.1, 0.2, 0.3]),
        )
        d = serialize_imu(reading)
        assert d['timestamp'] == 1.0
        assert d['accel'] == [1.0, 2.0, 3.0]
        assert d['gyro'] == [0.1, 0.2, 0.3]
        # Must be plain Python types
        assert isinstance(d['accel'], list)
        assert isinstance(d['accel'][0], float)

    def test_serialize_gps(self):
        reading = GPSReading(
            timestamp=2.0,
            position=np.array([10.0, 5.0, -3.0]),
            velocity=np.array([1.0, 0.0, 0.0]),
        )
        d = serialize_gps(reading)
        assert d['position'] == [10.0, 5.0, -3.0]
        assert d['fix_type'] == 3

    def test_serialize_altitude(self):
        reading = AltitudeReading(timestamp=3.0, altitude_baro=100.5, altitude_agl=2.1)
        d = serialize_altitude(reading)
        assert d['altitude_baro'] == 100.5
        assert d['altitude_agl'] == 2.1

    def test_serialize_battery(self):
        reading = BatteryReading(timestamp=4.0, voltage=4.2, current=1.5, remaining_pct=85.0)
        d = serialize_battery(reading)
        assert d['voltage'] == 4.2
        assert d['remaining_pct'] == 85.0

    def test_serialize_status(self):
        reading = DroneStatus(timestamp=5.0, armed=True, mode="HOVER", airborne=True)
        d = serialize_status(reading)
        assert d['armed'] is True
        assert d['mode'] == "HOVER"

    def test_serialize_ground_truth(self):
        gt = {
            'position': np.array([1.0, 2.0, 3.0]),
            'velocity': np.array([0.0, 0.0, 0.0]),
            'crashed': False,
        }
        d = serialize_ground_truth(gt)
        assert d['position'] == [1.0, 2.0, 3.0]
        assert d['crashed'] is False

    def test_serialize_drone_state(self):
        state = {
            'id': 0,
            'position': [1.0, 2.0, 3.0],
            'velocity': np.array([0.5, 0.0, 0.0]),
            'color': [1.0, 0.0, 0.0],
            'settled': True,
        }
        d = serialize_drone_state(state)
        assert d['id'] == 0
        assert isinstance(d['velocity'], list)


# ── REST endpoint tests ──────────────────────────────────────────

class TestSimulationEndpoints:
    def test_sim_info(self, client):
        r = client.get("/api/sim/info")
        assert r.status_code == 200
        data = r.json()
        assert 'running' in data
        assert 'paused' in data
        assert 'num_drones' in data
        assert data['running'] is True

    def test_sim_pause_resume(self, client):
        r = client.post("/api/sim/pause")
        assert r.status_code == 200
        assert r.json()['status'] == 'paused'

        r = client.post("/api/sim/resume")
        assert r.status_code == 200
        assert r.json()['status'] == 'resumed'

    def test_sim_step(self, client):
        client.post("/api/sim/pause")
        r = client.post("/api/sim/step")
        assert r.status_code == 200
        assert r.json()['status'] == 'stepped'
        client.post("/api/sim/resume")


class TestDroneEndpoints:
    def test_list_drones(self, client):
        r = client.get("/api/drones")
        assert r.status_code == 200
        drones = r.json()
        assert isinstance(drones, list)
        assert len(drones) > 0

    def test_get_drone_by_id(self, client):
        r = client.get("/api/drones/0")
        assert r.status_code == 200
        data = r.json()
        assert data['id'] == 0

    def test_get_drone_not_found(self, client):
        r = client.get("/api/drones/9999")
        assert r.status_code == 404

    def test_drone_imu(self, client):
        r = client.get("/api/drones/0/sensors/imu")
        assert r.status_code == 200
        data = r.json()
        assert 'accel' in data
        assert 'gyro' in data
        assert len(data['accel']) == 3

    def test_drone_gps(self, client):
        r = client.get("/api/drones/0/sensors/gps")
        assert r.status_code == 200
        data = r.json()
        assert 'position' in data
        assert 'velocity' in data

    def test_drone_altitude(self, client):
        r = client.get("/api/drones/0/sensors/altitude")
        assert r.status_code == 200
        data = r.json()
        assert 'altitude_baro' in data

    def test_drone_battery(self, client):
        r = client.get("/api/drones/0/sensors/battery")
        assert r.status_code == 200
        data = r.json()
        assert 'voltage' in data
        assert 'remaining_pct' in data

    def test_drone_status(self, client):
        r = client.get("/api/drones/0/status")
        assert r.status_code == 200
        data = r.json()
        assert 'armed' in data
        assert 'mode' in data

    def test_drone_ground_truth(self, client):
        r = client.get("/api/drones/0/ground_truth")
        assert r.status_code == 200
        data = r.json()
        assert 'position' in data
        assert 'motor_rpms' in data

    def test_sensor_not_found(self, client):
        r = client.get("/api/drones/9999/sensors/imu")
        assert r.status_code == 404


class TestDroneCommands:
    def test_set_position(self, client):
        r = client.post("/api/drones/0/command/position",
                        json={"x": 5.0, "y": 10.0, "z": 0.0})
        assert r.status_code == 200
        assert r.json()['drone_id'] == 0

    def test_set_velocity(self, client):
        r = client.post("/api/drones/0/command/velocity",
                        json={"vx": 1.0, "vy": 0.0, "vz": 0.0})
        assert r.status_code == 200

    def test_arm(self, client):
        r = client.post("/api/drones/0/command/arm")
        assert r.status_code == 200
        assert r.json()['status'] == 'armed'

    def test_disarm(self, client):
        r = client.post("/api/drones/0/command/disarm")
        assert r.status_code == 200
        assert r.json()['status'] == 'disarmed'

    def test_takeoff_not_armed(self, client):
        # Disarm first, then try takeoff
        client.post("/api/drones/1/command/disarm")
        r = client.post("/api/drones/1/command/takeoff", json={"altitude": 10.0})
        assert r.status_code == 400

    def test_takeoff_armed(self, client):
        client.post("/api/drones/0/command/arm")
        r = client.post("/api/drones/0/command/takeoff", json={"altitude": 10.0})
        assert r.status_code == 200

    def test_land(self, client):
        r = client.post("/api/drones/0/command/land")
        assert r.status_code == 200

    def test_command_not_found(self, client):
        r = client.post("/api/drones/9999/command/arm")
        assert r.status_code == 404


class TestFormationEndpoints:
    def test_set_formation(self, client):
        r = client.post("/api/formation", json={"type": "circle"})
        assert r.status_code == 200
        assert r.json()['formation'] == 'circle'

    def test_respawn(self, client):
        r = client.post("/api/respawn", json={"preset": "line", "num_drones": 4})
        assert r.status_code == 200
        assert r.json()['preset'] == 'line'


class TestObstacleEndpoints:
    def test_list_obstacles(self, client):
        r = client.get("/api/obstacles")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_add_box(self, client):
        r = client.post("/api/obstacles/box",
                        json={"position": [5, 1, 0], "size": [2, 2, 2]})
        assert r.status_code == 200

    def test_add_cylinder(self, client):
        r = client.post("/api/obstacles/cylinder",
                        json={"position": [0, 0, 5], "radius": 1.0, "height": 3.0})
        assert r.status_code == 200

    def test_remove_last(self, client):
        r = client.delete("/api/obstacles/last")
        assert r.status_code == 200

    def test_clear_obstacles(self, client):
        r = client.delete("/api/obstacles")
        assert r.status_code == 200


# ── WebSocket tests ──────────────────────────────────────────────

class TestWebSocket:
    def test_ws_receives_state(self, client):
        """WebSocket should receive a state_update frame."""
        with client.websocket_connect("/api/ws") as ws:
            data = ws.receive_json()
            assert data['type'] == 'state_update'
            assert 'timestamp' in data
            assert 'drones' in data
            assert 'sim_info' in data

    def test_ws_send_command(self, client):
        """WebSocket should accept JSON commands."""
        with client.websocket_connect("/api/ws") as ws:
            ws.send_text(json.dumps({
                "action": "set_formation",
                "type": "grid"
            }))
            # Should still get state updates back
            data = ws.receive_json()
            assert data['type'] == 'state_update'

    def test_ws_invalid_json(self, client):
        """Invalid JSON should not crash the connection."""
        with client.websocket_connect("/api/ws") as ws:
            ws.send_text("not valid json {{{")
            data = ws.receive_json()
            assert data['type'] == 'state_update'
