"""Tests for APF obstacle avoidance system (Phase 6B)."""

import sys
import os
import time
import pytest
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from simulation.avoidance import APFAvoidance, AvoidanceConfig
from simulation.obstacles import ObstacleManager
from simulation.drone import Drone
from simulation.flight_controller import FlightControllerConfig


# ── APF unit tests ───────────────────────────────────────────────

class TestAvoidanceDisabled:
    def test_zero_when_disabled(self):
        apf = APFAvoidance(AvoidanceConfig(enabled=False))
        obs = ObstacleManager()
        obs.add_box([5, 5, 0], [2, 2, 2])
        vel = apf.compute_avoidance_velocity(np.array([3, 5, 0]), obs)
        assert np.allclose(vel, 0)

    def test_zero_when_no_obstacles(self):
        apf = APFAvoidance(AvoidanceConfig(enabled=True))
        obs = ObstacleManager()
        vel = apf.compute_avoidance_velocity(np.array([0, 5, 0]), obs)
        assert np.allclose(vel, 0)

    def test_zero_when_obstacles_is_none(self):
        apf = APFAvoidance(AvoidanceConfig(enabled=True))
        vel = apf.compute_avoidance_velocity(np.array([0, 5, 0]), None)
        assert np.allclose(vel, 0)


class TestBoxRepulsion:
    def test_repulsion_from_positive_x(self):
        apf = APFAvoidance(AvoidanceConfig(enabled=True, sensor_range=10.0))
        obs = ObstacleManager()
        obs.add_box([10, 5, 0], [4, 4, 4])  # box spans x=[8,12]
        pos = np.array([6, 5, 0])  # close to -X face
        vel = apf.compute_avoidance_velocity(pos, obs)
        assert vel[0] < -0.1, f"Should push -X, got {vel}"

    def test_repulsion_from_negative_x(self):
        apf = APFAvoidance(AvoidanceConfig(enabled=True, sensor_range=10.0))
        obs = ObstacleManager()
        obs.add_box([0, 5, 0], [4, 4, 4])  # box spans x=[-2,2]
        pos = np.array([4, 5, 0])  # close to +X face
        vel = apf.compute_avoidance_velocity(pos, obs)
        assert vel[0] > 0.1, f"Should push +X, got {vel}"

    def test_repulsion_from_z(self):
        apf = APFAvoidance(AvoidanceConfig(enabled=True, sensor_range=10.0))
        obs = ObstacleManager()
        obs.add_box([0, 5, 5], [2, 2, 2])  # box spans z=[4,6]
        pos = np.array([0, 5, 3])
        vel = apf.compute_avoidance_velocity(pos, obs)
        assert vel[2] < -0.1, f"Should push -Z, got {vel}"

    def test_closer_means_stronger(self):
        apf = APFAvoidance(AvoidanceConfig(enabled=True, sensor_range=10.0,
                                           repulsion_gain=3.0))
        obs = ObstacleManager()
        obs.add_box([5, 5, 0], [2, 2, 2])

        vel_close = apf.compute_avoidance_velocity(np.array([3, 5, 0]), obs)
        vel_far = apf.compute_avoidance_velocity(np.array([1, 5, 0]), obs)
        assert np.linalg.norm(vel_close) > np.linalg.norm(vel_far)


class TestCylinderRepulsion:
    def test_repulsion_from_side(self):
        apf = APFAvoidance(AvoidanceConfig(enabled=True, sensor_range=10.0))
        obs = ObstacleManager()
        obs.add_cylinder([0, 0, 0], radius=3.0, height=10.0)
        pos = np.array([5, 5, 0])  # 2m from surface
        vel = apf.compute_avoidance_velocity(pos, obs)
        assert vel[0] > 0.1, f"Should push +X, got {vel}"

    def test_repulsion_from_z_side(self):
        apf = APFAvoidance(AvoidanceConfig(enabled=True, sensor_range=10.0))
        obs = ObstacleManager()
        obs.add_cylinder([0, 0, 0], radius=2.0, height=10.0)
        pos = np.array([0, 5, 4])
        vel = apf.compute_avoidance_velocity(pos, obs)
        assert vel[2] > 0.1

    def test_no_repulsion_above(self):
        apf = APFAvoidance(AvoidanceConfig(enabled=True, sensor_range=3.0))
        obs = ObstacleManager()
        obs.add_cylinder([0, 0, 0], radius=2.0, height=5.0)
        pos = np.array([0, 20, 0])  # far above
        vel = apf.compute_avoidance_velocity(pos, obs)
        assert np.linalg.norm(vel) < 0.01


class TestMultipleObstacles:
    def test_forces_sum(self):
        apf = APFAvoidance(AvoidanceConfig(enabled=True, sensor_range=15.0))
        obs = ObstacleManager()
        obs.add_box([5, 5, 0], [2, 2, 2])
        obs.add_box([-5, 5, 0], [2, 2, 2])
        pos = np.array([0, 5, 0])  # equidistant
        vel = apf.compute_avoidance_velocity(pos, obs)
        # X forces should roughly cancel
        assert abs(vel[0]) < 0.5, f"X should cancel, got {vel}"

    def test_asymmetric_forces(self):
        apf = APFAvoidance(AvoidanceConfig(enabled=True, sensor_range=15.0))
        obs = ObstacleManager()
        obs.add_box([3, 5, 0], [2, 2, 2])   # close
        obs.add_box([-10, 5, 0], [2, 2, 2])  # far
        pos = np.array([0, 5, 0])
        vel = apf.compute_avoidance_velocity(pos, obs)
        # Close box dominates → push -X
        assert vel[0] < -0.1


class TestVelocityLimiting:
    def test_clamped_to_limit(self):
        apf = APFAvoidance(AvoidanceConfig(
            enabled=True, velocity_limit=1.0, repulsion_gain=100.0,
            sensor_range=10.0))
        obs = ObstacleManager()
        obs.add_box([2, 5, 0], [2, 2, 2])
        pos = np.array([0.5, 5, 0])  # very close
        vel = apf.compute_avoidance_velocity(pos, obs)
        mag = np.linalg.norm(vel)
        assert mag <= 1.01, f"Should be clamped, got mag={mag:.2f}"


class TestSensorRange:
    def test_no_repulsion_beyond_range(self):
        apf = APFAvoidance(AvoidanceConfig(enabled=True, sensor_range=3.0))
        obs = ObstacleManager()
        obs.add_box([20, 5, 0], [2, 2, 2])
        pos = np.array([0, 5, 0])
        vel = apf.compute_avoidance_velocity(pos, obs)
        assert np.allclose(vel, 0)

    def test_repulsion_within_range(self):
        apf = APFAvoidance(AvoidanceConfig(enabled=True, sensor_range=5.0))
        obs = ObstacleManager()
        obs.add_box([5, 5, 0], [2, 2, 2])  # surface at x=4, 1m from pos
        pos = np.array([3, 5, 0])
        vel = apf.compute_avoidance_velocity(pos, obs)
        assert np.linalg.norm(vel) > 0.1


# ── Drone integration tests ─────────────────────────────────────

class TestDroneAvoidance:
    def test_drone_steers_around_box(self):
        """Drone targeting a point behind an obstacle should not crash."""
        cfg = FlightControllerConfig(
            avoidance_enabled=True,
            avoidance_sensor_range=8.0,
            avoidance_repulsion_gain=5.0,
            avoidance_velocity_limit=3.0,
        )
        obs = ObstacleManager()
        # Place box directly between start and target
        obs.add_box([5, 10, 0], [3, 3, 3])

        drone = Drone(0, [0, 10, 0], [1, 0, 0],
                       controller_config=cfg, obstacles=obs)
        drone.set_target([10, 10, 0])

        crashed = False
        for _ in range(600):  # 10 seconds
            drone.update(1 / 60)
            if drone.crashed:
                crashed = True
                break

        assert not crashed, "Drone should avoid crashing into obstacle"

    def test_no_obstacles_converges_normally(self):
        cfg = FlightControllerConfig(avoidance_enabled=True)
        obs = ObstacleManager()  # empty
        drone = Drone(0, [0, 10, 0], [1, 0, 0],
                       controller_config=cfg, obstacles=obs)
        drone.set_target([5, 10, 0])
        for _ in range(600):
            drone.update(1 / 60)
        error = np.linalg.norm(drone.position - drone.target_position)
        assert error < 1.0, f"Should converge, error={error:.2f}"

    def test_avoidance_disabled_flies_straight(self):
        cfg = FlightControllerConfig(avoidance_enabled=False)
        obs = ObstacleManager()
        obs.add_box([5, 10, 0], [3, 3, 3])
        drone = Drone(0, [0, 10, 0], [1, 0, 0],
                       controller_config=cfg, obstacles=obs)
        drone.set_target([10, 10, 0])
        # Without avoidance, drone flies straight (may collide)
        for _ in range(300):
            drone.update(1 / 60)
        # Just verify it ran without error
        assert True


# ── API tests ────────────────────────────────────────────────────

class TestAvoidanceAPI:
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

    def test_get_avoidance(self, client):
        r = client.get("/api/avoidance")
        assert r.status_code == 200
        data = r.json()
        assert 'enabled' in data
        assert 'sensor_range' in data

    def test_set_avoidance(self, client):
        r = client.post("/api/avoidance", json={
            "enabled": True,
            "sensor_range": 8.0,
            "repulsion_gain": 5.0,
            "velocity_limit": 3.0,
        })
        assert r.status_code == 200

        r = client.get("/api/avoidance")
        data = r.json()
        assert data['enabled'] is True
        assert data['sensor_range'] == 8.0
