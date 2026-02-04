"""Tests for wind simulation system (Phase 6A)."""

import sys
import os
import time
import pytest
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from simulation.environment import Environment, WindConfig
from simulation.drone import Drone
from simulation.swarm import Swarm


# ── Environment unit tests ───────────────────────────────────────

class TestWindDisabled:
    def test_zero_force_when_disabled(self):
        env = Environment(WindConfig(enabled=False))
        force = env.get_wind_force(1.0, 0.1)
        assert np.allclose(force, 0)

    def test_update_safe_when_disabled(self):
        env = Environment(WindConfig(enabled=False))
        env.update(1 / 60)
        force = env.get_wind_force(1.0)
        assert np.allclose(force, 0)


class TestConstantWind:
    def test_positive_x_force(self):
        cfg = WindConfig(enabled=True,
                         base_velocity=np.array([5.0, 0, 0]),
                         gust_magnitude=0.0)
        env = Environment(cfg)
        force = env.get_wind_force(0.0, 0.1)
        assert force[0] > 0, f"Expected +X force, got {force}"

    def test_negative_z_force(self):
        cfg = WindConfig(enabled=True,
                         base_velocity=np.array([0, 0, -3.0]),
                         gust_magnitude=0.0)
        env = Environment(cfg)
        force = env.get_wind_force(0.0, 0.1)
        assert force[2] < 0

    def test_force_scales_with_drag(self):
        cfg = WindConfig(enabled=True,
                         base_velocity=np.array([5.0, 0, 0]),
                         gust_magnitude=0.0)
        env = Environment(cfg)
        f1 = env.get_wind_force(0.0, 0.1)
        f2 = env.get_wind_force(0.0, 0.5)
        assert abs(f2[0]) > abs(f1[0])

    def test_force_consistent_no_gusts(self):
        cfg = WindConfig(enabled=True,
                         base_velocity=np.array([5.0, 0, 0]),
                         gust_magnitude=0.0)
        env = Environment(cfg)
        forces = [env.get_wind_force(i * 0.1, 0.1) for i in range(10)]
        for f in forces:
            np.testing.assert_allclose(f, forces[0], atol=1e-6)


class TestWindGusts:
    def test_gusts_vary_over_time(self):
        cfg = WindConfig(enabled=True,
                         base_velocity=np.zeros(3),
                         gust_magnitude=3.0,
                         gust_frequency=10.0)
        env = Environment(cfg)
        forces = []
        for _ in range(300):
            env.update(1 / 60)
            forces.append(env.get_wind_force(0.0, 0.1).copy())
        magnitudes = [np.linalg.norm(f) for f in forces]
        assert max(magnitudes) > 0.01, "Gusts should produce non-zero forces"
        assert np.std(magnitudes) > 0.001, "Gusts should vary"

    def test_gusts_mostly_horizontal(self):
        cfg = WindConfig(enabled=True,
                         base_velocity=np.zeros(3),
                         gust_magnitude=5.0,
                         gust_frequency=10.0)
        env = Environment(cfg)
        y_forces = []
        xz_forces = []
        for _ in range(300):
            env.update(1 / 60)
            f = env.get_wind_force(0.0, 0.1)
            y_forces.append(abs(f[1]))
            xz_forces.append(np.sqrt(f[0] ** 2 + f[2] ** 2))
        # Y component should be much smaller on average (scaled by 0.2)
        assert np.mean(y_forces) < np.mean(xz_forces) or np.mean(xz_forces) < 0.01


# ── Drone-level wind tests ───────────────────────────────────────

class TestDroneWindDrift:
    def test_drone_drifts_in_wind_direction(self):
        drone = Drone(0, [0, 10, 0], [1, 0, 0])
        wind = np.array([50.0, 0, 0])  # strong wind
        x_before = drone.position[0]
        for _ in range(60):
            drone.update(1 / 60, wind)
        assert drone.position[0] > x_before, "Drone should drift in +X"

    def test_drone_drifts_negative_z(self):
        drone = Drone(0, [0, 10, 0], [1, 0, 0])
        wind = np.array([0, 0, -50.0])
        z_before = drone.position[2]
        for _ in range(60):
            drone.update(1 / 60, wind)
        assert drone.position[2] < z_before

    def test_no_drift_without_wind(self):
        drone = Drone(0, [0, 10, 0], [1, 0, 0])
        drone.set_target([0, 10, 0])
        for _ in range(300):
            drone.update(1 / 60)
        # Should stay near target
        error = np.linalg.norm(drone.position - drone.target_position)
        assert error < 1.0


class TestFlightControllerWindCompensation:
    def test_compensates_moderate_wind(self):
        drone = Drone(0, [0, 10, 0], [1, 0, 0])
        drone.set_target([0, 10, 0])
        wind = np.array([5.0, 0, 0])  # moderate wind
        for _ in range(600):  # 10 seconds
            drone.update(1 / 60, wind)
        error = np.linalg.norm(drone.position - drone.target_position)
        assert error < 2.0, f"Controller should hold position, error={error:.2f}m"

    def test_overwhelmed_by_extreme_wind(self):
        drone = Drone(0, [0, 10, 0], [1, 0, 0])
        drone.set_target([0, 10, 0])
        wind = np.array([200.0, 0, 0])  # extreme wind
        for _ in range(300):
            drone.update(1 / 60, wind)
        # Should have drifted significantly
        assert drone.position[0] > 5.0


# ── Swarm integration ────────────────────────────────────────────

class TestSwarmWindIntegration:
    def test_swarm_passes_wind_to_drones(self):
        env = Environment(WindConfig(
            enabled=True,
            base_velocity=np.array([50.0, 0, 0]),
            gust_magnitude=0.0,
        ))
        swarm = Swarm(2, [[1, 0, 0], [0, 1, 0]], spacing=5.0,
                       spawn_preset='line', spawn_altitude=10.0,
                       seed=42, up_axis='y', environment=env)
        x_before = [d.position[0] for d in swarm.drones]
        for _ in range(60):
            swarm.update(1 / 60, env)
        x_after = [d.position[0] for d in swarm.drones]
        for i in range(2):
            assert x_after[i] > x_before[i], f"Drone {i} should drift"

    def test_swarm_no_wind_stable(self):
        env = Environment(WindConfig(enabled=False))
        swarm = Swarm(2, [[1, 0, 0], [0, 1, 0]], spacing=5.0,
                       spawn_preset='line', spawn_altitude=10.0,
                       seed=42, up_axis='y', environment=env)
        for _ in range(120):
            swarm.update(1 / 60, env)
        # Drones should be near their spawn positions
        for d in swarm.drones:
            error = np.linalg.norm(d.position - d.target_position)
            assert error < 2.0


# ── API tests ────────────────────────────────────────────────────

class TestWindAPI:
    @pytest.fixture(scope="class")
    def client(self):
        from simulation.simulator import Simulator
        from api.server import create_app
        from fastapi.testclient import TestClient
        sim = Simulator("config.yaml")
        sim.start()
        time.sleep(1.5)
        app = create_app(sim)
        yield TestClient(app)
        sim.stop()

    def test_get_wind(self, client):
        r = client.get("/api/wind")
        assert r.status_code == 200
        data = r.json()
        assert 'enabled' in data
        assert 'base_velocity' in data

    def test_set_wind(self, client):
        r = client.post("/api/wind", json={
            "enabled": True,
            "base_velocity": [3.0, 0, 0],
            "gust_magnitude": 1.0,
            "gust_frequency": 0.5,
        })
        assert r.status_code == 200

        r = client.get("/api/wind")
        data = r.json()
        assert data['enabled'] is True
        assert data['base_velocity'][0] == 3.0

    def test_sim_info_includes_wind(self, client):
        r = client.get("/api/sim/info")
        data = r.json()
        assert 'wind' in data
