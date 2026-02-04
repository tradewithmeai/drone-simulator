"""Tests for drone-to-drone collision detection and response.

Covers:
- Sphere-sphere overlap detection
- Elastic collision impulse with restitution
- Position separation for overlapping drones
- Crash threshold (high-speed impact)
- Collision disable toggle
- Momentum conservation
- Edge cases (single drone, all crashed, zero distance)
"""

import numpy as np
import pytest
from simulation.drone import Drone
from simulation.swarm import Swarm
from simulation.physics import PhysicsConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_swarm(n=2, collision_config=None):
    """Create a minimal swarm with n drones at default positions."""
    colors = [[1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 1, 0]]
    cfg = collision_config or {
        'enabled': True,
        'drone_radius': 0.3,
        'restitution': 0.3,
        'crash_speed': 8.0,
    }
    swarm = Swarm(n, colors, spacing=5.0, spawn_preset='line',
                  spawn_altitude=10.0, seed=42, collision_config=cfg)
    return swarm


def place_drones_head_on(swarm, gap=0.5, speed=3.0, altitude=10.0):
    """Place two drones on a head-on collision course along X axis.

    Drone 0 at (-gap/2, alt, 0) moving +X at speed.
    Drone 1 at (+gap/2, alt, 0) moving -X at speed.
    """
    d0, d1 = swarm.drones[0], swarm.drones[1]
    d0.physics.position = np.array([-gap / 2, altitude, 0.0])
    d0.physics.velocity = np.array([speed, 0.0, 0.0])
    d1.physics.position = np.array([gap / 2, altitude, 0.0])
    d1.physics.velocity = np.array([-speed, 0.0, 0.0])
    # Disable flight controller so it doesn't fight the velocity
    d0.controller.disarm()
    d1.controller.disarm()


# ===========================================================================
# Basic collision detection
# ===========================================================================

class TestCollisionDetection:
    """Test that overlapping drones are detected."""

    def test_no_collision_when_far_apart(self):
        """Drones spaced far apart should not collide."""
        swarm = make_swarm(2)
        d0, d1 = swarm.drones[0], swarm.drones[1]
        d0.physics.position = np.array([0.0, 10.0, 0.0])
        d1.physics.position = np.array([5.0, 10.0, 0.0])
        v0_before = d0.physics.velocity.copy()
        v1_before = d1.physics.velocity.copy()

        swarm._detect_collisions()

        np.testing.assert_array_equal(d0.physics.velocity, v0_before)
        np.testing.assert_array_equal(d1.physics.velocity, v1_before)

    def test_collision_detected_when_overlapping(self):
        """Drones closer than 2*radius should trigger collision response."""
        swarm = make_swarm(2)
        d0, d1 = swarm.drones[0], swarm.drones[1]
        # Place them 0.4m apart (less than 2*0.3 = 0.6)
        d0.physics.position = np.array([0.0, 10.0, 0.0])
        d1.physics.position = np.array([0.4, 10.0, 0.0])
        # Moving toward each other
        d0.physics.velocity = np.array([2.0, 0.0, 0.0])
        d1.physics.velocity = np.array([-2.0, 0.0, 0.0])

        swarm._detect_collisions()

        # Velocities should have changed (collision response applied)
        assert d0.physics.velocity[0] < 2.0, "Drone 0 should have bounced"
        assert d1.physics.velocity[0] > -2.0, "Drone 1 should have bounced"

    def test_no_collision_when_separating(self):
        """Overlapping drones moving apart should not get impulse."""
        swarm = make_swarm(2)
        d0, d1 = swarm.drones[0], swarm.drones[1]
        # Overlapping but moving apart
        d0.physics.position = np.array([0.0, 10.0, 0.0])
        d1.physics.position = np.array([0.4, 10.0, 0.0])
        d0.physics.velocity = np.array([-2.0, 0.0, 0.0])
        d1.physics.velocity = np.array([2.0, 0.0, 0.0])

        v0_before = d0.physics.velocity.copy()
        v1_before = d1.physics.velocity.copy()

        swarm._detect_collisions()

        # Velocities should NOT change (they're separating)
        # But positions may still be adjusted for overlap
        np.testing.assert_array_equal(d0.physics.velocity, v0_before)
        np.testing.assert_array_equal(d1.physics.velocity, v1_before)


# ===========================================================================
# Collision response physics
# ===========================================================================

class TestCollisionResponse:
    """Test collision impulse and position correction."""

    def test_position_separation(self):
        """Overlapping drones should be pushed apart to min_dist."""
        swarm = make_swarm(2)
        d0, d1 = swarm.drones[0], swarm.drones[1]
        radius = swarm.collision_config['drone_radius']

        # Place them overlapping
        d0.physics.position = np.array([0.0, 10.0, 0.0])
        d1.physics.position = np.array([0.2, 10.0, 0.0])
        d0.physics.velocity = np.array([1.0, 0.0, 0.0])
        d1.physics.velocity = np.array([-1.0, 0.0, 0.0])

        swarm._detect_collisions()

        dist_after = np.linalg.norm(d1.physics.position - d0.physics.position)
        assert dist_after >= 2 * radius - 1e-6, \
            f"Drones should be separated to at least {2*radius}m, got {dist_after}"

    def test_momentum_conservation(self):
        """Total momentum should be conserved in collision (equal mass)."""
        swarm = make_swarm(2)
        d0, d1 = swarm.drones[0], swarm.drones[1]
        d0.physics.position = np.array([0.0, 10.0, 0.0])
        d1.physics.position = np.array([0.4, 10.0, 0.0])
        d0.physics.velocity = np.array([3.0, 0.0, 0.0])
        d1.physics.velocity = np.array([-1.0, 0.0, 0.0])

        p_before = d0.physics.velocity + d1.physics.velocity  # equal mass

        swarm._detect_collisions()

        p_after = d0.physics.velocity + d1.physics.velocity
        np.testing.assert_allclose(p_after, p_before, atol=1e-10,
                                   err_msg="Momentum not conserved")

    def test_energy_loss_with_restitution(self):
        """Kinetic energy should decrease with restitution < 1."""
        swarm = make_swarm(2, collision_config={
            'enabled': True,
            'drone_radius': 0.3,
            'restitution': 0.5,
            'crash_speed': 100.0,  # high threshold so no crash
        })
        d0, d1 = swarm.drones[0], swarm.drones[1]
        d0.physics.position = np.array([0.0, 10.0, 0.0])
        d1.physics.position = np.array([0.4, 10.0, 0.0])
        d0.physics.velocity = np.array([5.0, 0.0, 0.0])
        d1.physics.velocity = np.array([-5.0, 0.0, 0.0])

        ke_before = np.sum(d0.physics.velocity**2) + np.sum(d1.physics.velocity**2)

        swarm._detect_collisions()

        ke_after = np.sum(d0.physics.velocity**2) + np.sum(d1.physics.velocity**2)
        assert ke_after < ke_before, "Energy should decrease with restitution < 1"

    def test_perfectly_elastic_collision(self):
        """With restitution=1.0, kinetic energy should be conserved."""
        swarm = make_swarm(2, collision_config={
            'enabled': True,
            'drone_radius': 0.3,
            'restitution': 1.0,
            'crash_speed': 100.0,
        })
        d0, d1 = swarm.drones[0], swarm.drones[1]
        d0.physics.position = np.array([0.0, 10.0, 0.0])
        d1.physics.position = np.array([0.4, 10.0, 0.0])
        d0.physics.velocity = np.array([3.0, 1.0, 0.0])
        d1.physics.velocity = np.array([-2.0, 0.0, 0.0])

        ke_before = np.sum(d0.physics.velocity**2) + np.sum(d1.physics.velocity**2)

        swarm._detect_collisions()

        ke_after = np.sum(d0.physics.velocity**2) + np.sum(d1.physics.velocity**2)
        np.testing.assert_allclose(ke_after, ke_before, atol=1e-8,
                                   err_msg="Energy should be conserved with e=1.0")

    def test_velocity_reversal_head_on(self):
        """Head-on equal-speed collision should reverse velocities (with restitution)."""
        swarm = make_swarm(2, collision_config={
            'enabled': True,
            'drone_radius': 0.3,
            'restitution': 1.0,
            'crash_speed': 100.0,
        })
        d0, d1 = swarm.drones[0], swarm.drones[1]
        d0.physics.position = np.array([0.0, 10.0, 0.0])
        d1.physics.position = np.array([0.5, 10.0, 0.0])
        d0.physics.velocity = np.array([3.0, 0.0, 0.0])
        d1.physics.velocity = np.array([-3.0, 0.0, 0.0])

        swarm._detect_collisions()

        # With e=1.0, equal mass head-on: velocities swap
        np.testing.assert_allclose(d0.physics.velocity[0], -3.0, atol=1e-8)
        np.testing.assert_allclose(d1.physics.velocity[0], 3.0, atol=1e-8)


# ===========================================================================
# Crash threshold
# ===========================================================================

class TestCrashThreshold:
    """Test that high-speed impacts mark drones as crashed."""

    def test_low_speed_no_crash(self):
        """Impact below crash_speed should not crash drones."""
        swarm = make_swarm(2, collision_config={
            'enabled': True,
            'drone_radius': 0.3,
            'restitution': 0.3,
            'crash_speed': 8.0,
        })
        d0, d1 = swarm.drones[0], swarm.drones[1]
        # Relative speed = 6 m/s (below 8.0 threshold)
        d0.physics.position = np.array([0.0, 10.0, 0.0])
        d1.physics.position = np.array([0.4, 10.0, 0.0])
        d0.physics.velocity = np.array([3.0, 0.0, 0.0])
        d1.physics.velocity = np.array([-3.0, 0.0, 0.0])

        swarm._detect_collisions()

        assert not d0.crashed, "Drone 0 should not crash at low speed"
        assert not d1.crashed, "Drone 1 should not crash at low speed"

    def test_high_speed_crash(self):
        """Impact above crash_speed should crash both drones."""
        swarm = make_swarm(2, collision_config={
            'enabled': True,
            'drone_radius': 0.3,
            'restitution': 0.3,
            'crash_speed': 8.0,
        })
        d0, d1 = swarm.drones[0], swarm.drones[1]
        # Relative speed = 12 m/s (above 8.0 threshold)
        d0.physics.position = np.array([0.0, 10.0, 0.0])
        d1.physics.position = np.array([0.4, 10.0, 0.0])
        d0.physics.velocity = np.array([6.0, 0.0, 0.0])
        d1.physics.velocity = np.array([-6.0, 0.0, 0.0])

        swarm._detect_collisions()

        assert d0.crashed, "Drone 0 should crash at high speed"
        assert d1.crashed, "Drone 1 should crash at high speed"

    def test_crashed_drones_fall_to_ground(self):
        """Crashed drones should have motors off and fall under gravity."""
        swarm = make_swarm(2)
        d0 = swarm.drones[0]
        d0.physics.position = np.array([0.0, 10.0, 0.0])
        d0.physics.velocity = np.zeros(3)
        d0.crashed = True

        # Step physics several times
        for _ in range(120):
            d0.update(1.0 / 60.0)

        # Should have fallen toward ground
        assert d0.physics.position[1] < 5.0, \
            f"Crashed drone should fall, but Y={d0.physics.position[1]}"

    def test_crashed_drones_motors_off(self):
        """Crashed drones should have zero motor RPMs."""
        swarm = make_swarm(2)
        d0 = swarm.drones[0]
        d0.crashed = True
        d0.update(1.0 / 60.0)

        np.testing.assert_array_equal(d0.physics.motor_rpms, np.zeros(4))


# ===========================================================================
# Configuration toggle
# ===========================================================================

class TestCollisionConfig:
    """Test collision enable/disable and config values."""

    def test_collisions_disabled(self):
        """When disabled, overlapping drones should not interact."""
        swarm = make_swarm(2, collision_config={
            'enabled': False,
            'drone_radius': 0.3,
            'restitution': 0.3,
            'crash_speed': 8.0,
        })
        d0, d1 = swarm.drones[0], swarm.drones[1]
        d0.physics.position = np.array([0.0, 10.0, 0.0])
        d1.physics.position = np.array([0.2, 10.0, 0.0])
        d0.physics.velocity = np.array([5.0, 0.0, 0.0])
        d1.physics.velocity = np.array([-5.0, 0.0, 0.0])

        v0_before = d0.physics.velocity.copy()
        v1_before = d1.physics.velocity.copy()
        p0_before = d0.physics.position.copy()
        p1_before = d1.physics.position.copy()

        swarm._detect_collisions()

        np.testing.assert_array_equal(d0.physics.velocity, v0_before)
        np.testing.assert_array_equal(d1.physics.velocity, v1_before)
        np.testing.assert_array_equal(d0.physics.position, p0_before)
        np.testing.assert_array_equal(d1.physics.position, p1_before)

    def test_custom_radius(self):
        """Larger radius should detect collisions at greater distance."""
        swarm = make_swarm(2, collision_config={
            'enabled': True,
            'drone_radius': 1.0,  # large radius
            'restitution': 0.3,
            'crash_speed': 100.0,
        })
        d0, d1 = swarm.drones[0], swarm.drones[1]
        # 1.5m apart -- less than 2*1.0 = 2.0
        d0.physics.position = np.array([0.0, 10.0, 0.0])
        d1.physics.position = np.array([1.5, 10.0, 0.0])
        d0.physics.velocity = np.array([1.0, 0.0, 0.0])
        d1.physics.velocity = np.array([-1.0, 0.0, 0.0])

        swarm._detect_collisions()

        assert d0.physics.velocity[0] < 1.0, "Should detect collision with larger radius"

    def test_default_config(self):
        """Swarm created without collision_config should use defaults."""
        colors = [[1, 0, 0], [0, 1, 0]]
        swarm = Swarm(2, colors, spacing=5.0, spawn_preset='line',
                      spawn_altitude=10.0, seed=42)
        assert swarm.collision_config['enabled'] is True
        assert swarm.collision_config['drone_radius'] == 0.3


# ===========================================================================
# Edge cases
# ===========================================================================

class TestEdgeCases:
    """Test edge cases and robustness."""

    def test_single_drone_no_crash(self):
        """A single drone should never trigger collision."""
        swarm = make_swarm(1)
        d0 = swarm.drones[0]
        d0.physics.velocity = np.array([10.0, 0.0, 0.0])

        swarm._detect_collisions()

        assert not d0.crashed

    def test_both_crashed_skip(self):
        """If both drones are already crashed, skip collision check."""
        swarm = make_swarm(2)
        d0, d1 = swarm.drones[0], swarm.drones[1]
        d0.crashed = True
        d1.crashed = True
        d0.physics.position = np.array([0.0, 10.0, 0.0])
        d1.physics.position = np.array([0.2, 10.0, 0.0])
        d0.physics.velocity = np.array([10.0, 0.0, 0.0])
        d1.physics.velocity = np.array([-10.0, 0.0, 0.0])

        v0_before = d0.physics.velocity.copy()
        swarm._detect_collisions()

        np.testing.assert_array_equal(d0.physics.velocity, v0_before)

    def test_three_drones_pairwise(self):
        """Three drones: only the overlapping pair should collide."""
        swarm = make_swarm(3)
        d0, d1, d2 = swarm.drones[0], swarm.drones[1], swarm.drones[2]

        # d0 and d1 overlap, d2 is far away
        d0.physics.position = np.array([0.0, 10.0, 0.0])
        d1.physics.position = np.array([0.4, 10.0, 0.0])
        d2.physics.position = np.array([20.0, 10.0, 0.0])

        d0.physics.velocity = np.array([2.0, 0.0, 0.0])
        d1.physics.velocity = np.array([-2.0, 0.0, 0.0])
        d2.physics.velocity = np.array([0.0, 0.0, 0.0])

        v2_before = d2.physics.velocity.copy()

        swarm._detect_collisions()

        # d0 and d1 should have bounced
        assert d0.physics.velocity[0] < 2.0
        # d2 should be untouched
        np.testing.assert_array_equal(d2.physics.velocity, v2_before)

    def test_collision_in_update_loop(self):
        """Collisions should fire as part of normal swarm.update()."""
        swarm = make_swarm(2, collision_config={
            'enabled': True,
            'drone_radius': 0.3,
            'restitution': 0.3,
            'crash_speed': 100.0,
        })
        d0, d1 = swarm.drones[0], swarm.drones[1]
        place_drones_head_on(swarm, gap=0.4, speed=3.0, altitude=10.0)

        # Run one update step -- should trigger collision
        swarm.update(1.0 / 60.0)

        # Drones should have bounced (velocity changed direction)
        # After one physics step + collision, d0's X velocity should be reduced/reversed
        assert d0.physics.velocity[0] < 3.0

    def test_get_state_includes_crashed(self):
        """Drone get_state() should report crashed status."""
        swarm = make_swarm(2)
        d0 = swarm.drones[0]
        d0.crashed = True

        state = d0.get_state()
        assert state['crashed'] is True

    def test_respawn_clears_crashed(self):
        """Respawning should create fresh (non-crashed) drones."""
        swarm = make_swarm(2)
        swarm.drones[0].crashed = True
        swarm.drones[1].crashed = True

        swarm.respawn_formation('line', num_drones=2)

        for drone in swarm.drones:
            assert not drone.crashed, "Respawned drones should not be crashed"
