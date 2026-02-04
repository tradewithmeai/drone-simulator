"""Tests for static obstacle system: data structures, collision detection, and integration.

Covers:
- ObstacleManager add/remove/clear/load_scene
- Sphere-AABB collision from each face, inside, miss
- Sphere-cylinder collision: side, above, below, on-axis
- Collision normal direction correctness
- Integration with swarm collision loop
- Crash threshold on obstacle impact
- Disabled collisions
"""

import numpy as np
import pytest
from simulation.obstacles import ObstacleManager, Box, Cylinder
from simulation.swarm import Swarm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_manager():
    """Create a fresh ObstacleManager."""
    return ObstacleManager()


def make_swarm_with_obstacle(obstacle_type='box', collision_config=None):
    """Create a 2-drone swarm and add one obstacle."""
    colors = [[1, 0, 0], [0, 1, 0]]
    cfg = collision_config or {
        'enabled': True,
        'drone_radius': 0.3,
        'restitution': 0.3,
        'crash_speed': 8.0,
    }
    swarm = Swarm(2, colors, spacing=20.0, spawn_preset='line',
                  spawn_altitude=10.0, seed=42, collision_config=cfg)
    if obstacle_type == 'box':
        swarm.obstacles.add_box([0, 5, 0], [4, 4, 4])  # center at origin+5Y, 4x4x4
    elif obstacle_type == 'cylinder':
        swarm.obstacles.add_cylinder([0, 0, 0], 2.0, 10.0)
    return swarm


# ===========================================================================
# ObstacleManager CRUD operations
# ===========================================================================

class TestObstacleManagerCRUD:
    """Test add, remove, clear, and load_scene operations."""

    def test_add_box(self):
        mgr = make_manager()
        mgr.add_box([1, 2, 3], [4, 4, 4], [1, 0, 0])
        assert len(mgr.boxes) == 1
        np.testing.assert_array_equal(mgr.boxes[0].position, [1, 2, 3])
        np.testing.assert_array_equal(mgr.boxes[0].half_size, [2, 2, 2])

    def test_add_cylinder(self):
        mgr = make_manager()
        mgr.add_cylinder([5, 0, 5], 1.5, 8.0, [0, 1, 0])
        assert len(mgr.cylinders) == 1
        assert mgr.cylinders[0].radius == 1.5
        assert mgr.cylinders[0].height == 8.0

    def test_default_colors(self):
        mgr = make_manager()
        mgr.add_box([0, 0, 0], [1, 1, 1])
        mgr.add_cylinder([0, 0, 0], 1.0, 1.0)
        assert mgr.boxes[0].color == [0.5, 0.5, 0.5]
        assert mgr.cylinders[0].color == [0.6, 0.3, 0.1]

    def test_remove_last_box(self):
        mgr = make_manager()
        mgr.add_box([0, 0, 0], [1, 1, 1])
        mgr.add_box([5, 0, 0], [2, 2, 2])
        mgr.remove_last()
        assert len(mgr.boxes) == 1
        np.testing.assert_array_equal(mgr.boxes[0].position, [0, 0, 0])

    def test_remove_last_cylinder(self):
        mgr = make_manager()
        mgr.add_box([0, 0, 0], [1, 1, 1])
        mgr.add_cylinder([5, 0, 0], 1.0, 5.0)
        mgr.remove_last()
        assert len(mgr.cylinders) == 0
        assert len(mgr.boxes) == 1

    def test_remove_last_empty(self):
        mgr = make_manager()
        mgr.remove_last()  # should not crash

    def test_clear_all(self):
        mgr = make_manager()
        mgr.add_box([0, 0, 0], [1, 1, 1])
        mgr.add_cylinder([5, 0, 0], 1.0, 5.0)
        mgr.clear_all()
        assert len(mgr.boxes) == 0
        assert len(mgr.cylinders) == 0

    def test_load_scene(self):
        mgr = make_manager()
        scene = [
            {'type': 'box', 'position': [1, 2, 3], 'size': [4, 4, 4]},
            {'type': 'cylinder', 'position': [5, 0, 0], 'radius': 2.0, 'height': 6.0},
        ]
        mgr.load_scene(scene)
        assert len(mgr.boxes) == 1
        assert len(mgr.cylinders) == 1

    def test_load_scene_clears_previous(self):
        mgr = make_manager()
        mgr.add_box([0, 0, 0], [1, 1, 1])
        mgr.load_scene([{'type': 'box', 'position': [10, 0, 0], 'size': [2, 2, 2]}])
        assert len(mgr.boxes) == 1
        np.testing.assert_array_equal(mgr.boxes[0].position, [10, 0, 0])

    def test_get_states(self):
        mgr = make_manager()
        mgr.add_box([1, 2, 3], [4, 6, 8], [1, 0, 0])
        mgr.add_cylinder([5, 0, 0], 1.5, 10.0, [0, 1, 0])
        states = mgr.get_states()
        assert len(states) == 2
        assert states[0]['type'] == 'box'
        assert states[0]['size'] == [4, 6, 8]
        assert states[1]['type'] == 'cylinder'
        assert states[1]['radius'] == 1.5


# ===========================================================================
# Sphere-AABB collision
# ===========================================================================

class TestSphereBoxCollision:
    """Test sphere vs axis-aligned box collision detection."""

    def test_miss_far_away(self):
        mgr = make_manager()
        mgr.add_box([0, 0, 0], [2, 2, 2])  # box from (-1,-1,-1) to (1,1,1)
        hit, normal, pen = mgr.check_collision(np.array([5.0, 0.0, 0.0]), 0.3)
        assert not hit

    def test_hit_from_positive_x(self):
        mgr = make_manager()
        mgr.add_box([0, 0, 0], [2, 2, 2])
        # Sphere at x=1.2, radius 0.3 -> overlaps box at x=1
        hit, normal, pen = mgr.check_collision(np.array([1.2, 0.0, 0.0]), 0.3)
        assert hit
        assert normal[0] > 0.9, f"Normal should point +X, got {normal}"
        assert pen > 0

    def test_hit_from_negative_x(self):
        mgr = make_manager()
        mgr.add_box([0, 0, 0], [2, 2, 2])
        hit, normal, pen = mgr.check_collision(np.array([-1.2, 0.0, 0.0]), 0.3)
        assert hit
        assert normal[0] < -0.9, f"Normal should point -X, got {normal}"

    def test_hit_from_positive_y(self):
        mgr = make_manager()
        mgr.add_box([0, 0, 0], [2, 2, 2])
        hit, normal, pen = mgr.check_collision(np.array([0.0, 1.2, 0.0]), 0.3)
        assert hit
        assert normal[1] > 0.9, f"Normal should point +Y, got {normal}"

    def test_hit_from_negative_z(self):
        mgr = make_manager()
        mgr.add_box([0, 0, 0], [2, 2, 2])
        hit, normal, pen = mgr.check_collision(np.array([0.0, 0.0, -1.2]), 0.3)
        assert hit
        assert normal[2] < -0.9, f"Normal should point -Z, got {normal}"

    def test_sphere_inside_box(self):
        """Sphere center inside box should still report collision."""
        mgr = make_manager()
        mgr.add_box([0, 0, 0], [4, 4, 4])  # large box
        hit, normal, pen = mgr.check_collision(np.array([0.0, 0.0, 0.0]), 0.3)
        assert hit
        assert np.linalg.norm(normal) > 0.99  # normal should be unit length

    def test_corner_hit(self):
        """Sphere near corner of box should detect collision."""
        mgr = make_manager()
        mgr.add_box([0, 0, 0], [2, 2, 2])
        # Near the (+1,+1,+1) corner
        pos = np.array([1.1, 1.1, 1.1])
        dist_to_corner = np.linalg.norm(pos - np.array([1, 1, 1]))
        hit, normal, pen = mgr.check_collision(pos, 0.3)
        assert hit  # dist_to_corner ~0.17, radius 0.3

    def test_penetration_depth(self):
        mgr = make_manager()
        mgr.add_box([0, 0, 0], [2, 2, 2])
        # Sphere at x=1.2 (outside box), +X face at x=1, radius 0.3
        # Closest point on box is (1, 0, 0), distance = 0.2, pen = 0.3 - 0.2 = 0.1
        hit, normal, pen = mgr.check_collision(np.array([1.2, 0.0, 0.0]), 0.3)
        assert hit
        assert abs(pen - 0.1) < 0.01, f"Expected ~0.1 penetration, got {pen}"


# ===========================================================================
# Sphere-Cylinder collision
# ===========================================================================

class TestSphereCylinderCollision:
    """Test sphere vs vertical cylinder collision detection."""

    def test_miss_far_away(self):
        mgr = make_manager()
        mgr.add_cylinder([0, 0, 0], 2.0, 10.0)
        hit, normal, pen = mgr.check_collision(np.array([10.0, 5.0, 0.0]), 0.3)
        assert not hit

    def test_hit_from_side(self):
        mgr = make_manager()
        mgr.add_cylinder([0, 0, 0], 2.0, 10.0)
        # Sphere at x=2.1, within cylinder height, radius 0.3
        hit, normal, pen = mgr.check_collision(np.array([2.1, 5.0, 0.0]), 0.3)
        assert hit
        assert normal[0] > 0.9, f"Normal should point +X, got {normal}"
        assert abs(normal[1]) < 0.01, "Normal should be horizontal"

    def test_miss_above_cylinder(self):
        mgr = make_manager()
        mgr.add_cylinder([0, 0, 0], 2.0, 10.0)
        # Sphere above cylinder top (y=10 + more than radius)
        hit, _, _ = mgr.check_collision(np.array([0.0, 11.0, 0.0]), 0.3)
        assert not hit

    def test_miss_below_cylinder(self):
        mgr = make_manager()
        mgr.add_cylinder([0, 0, 0], 2.0, 10.0)
        hit, _, _ = mgr.check_collision(np.array([0.0, -1.0, 0.0]), 0.3)
        assert not hit

    def test_hit_at_base(self):
        """Sphere near cylinder base within height range."""
        mgr = make_manager()
        mgr.add_cylinder([0, 0, 0], 2.0, 10.0)
        hit, normal, pen = mgr.check_collision(np.array([2.1, 0.5, 0.0]), 0.3)
        assert hit

    def test_on_axis(self):
        """Sphere on the cylinder axis should get an arbitrary horizontal normal."""
        mgr = make_manager()
        mgr.add_cylinder([0, 0, 0], 2.0, 10.0)
        hit, normal, pen = mgr.check_collision(np.array([0.0, 5.0, 0.0]), 0.3)
        assert hit
        assert abs(normal[1]) < 0.01, "Normal should be horizontal"
        assert np.linalg.norm(normal) > 0.99

    def test_hit_from_z_direction(self):
        mgr = make_manager()
        mgr.add_cylinder([0, 0, 0], 2.0, 10.0)
        hit, normal, pen = mgr.check_collision(np.array([0.0, 5.0, 2.1]), 0.3)
        assert hit
        assert normal[2] > 0.9, f"Normal should point +Z, got {normal}"


# ===========================================================================
# Integration with Swarm collision loop
# ===========================================================================

class TestSwarmObstacleIntegration:
    """Test obstacle collisions within the swarm update loop."""

    def test_drone_bounces_off_box(self):
        """Drone flying into a box should bounce back."""
        swarm = make_swarm_with_obstacle('box', collision_config={
            'enabled': True,
            'drone_radius': 0.3,
            'restitution': 0.5,
            'crash_speed': 100.0,  # high so no crash
        })
        d0 = swarm.drones[0]
        # Position drone just outside the box, moving toward it
        # Box is at [0,5,0] size [4,4,4], so +X face at x=2
        d0.physics.position = np.array([2.2, 5.0, 0.0])
        d0.physics.velocity = np.array([-5.0, 0.0, 0.0])
        d0.controller.disarm()

        swarm._detect_collisions()

        # Velocity should have reversed (or at least reduced in -X direction)
        assert d0.physics.velocity[0] > 0, \
            f"Drone should bounce off box, but vx={d0.physics.velocity[0]}"

    def test_drone_bounces_off_cylinder(self):
        """Drone flying into a cylinder should bounce back."""
        swarm = make_swarm_with_obstacle('cylinder', collision_config={
            'enabled': True,
            'drone_radius': 0.3,
            'restitution': 0.5,
            'crash_speed': 100.0,
        })
        d0 = swarm.drones[0]
        # Cylinder at [0,0,0] r=2 h=10. Approach from +X at y=5
        d0.physics.position = np.array([2.1, 5.0, 0.0])
        d0.physics.velocity = np.array([-5.0, 0.0, 0.0])
        d0.controller.disarm()

        swarm._detect_collisions()

        assert d0.physics.velocity[0] > 0, \
            f"Drone should bounce off cylinder, but vx={d0.physics.velocity[0]}"

    def test_high_speed_crash_into_obstacle(self):
        """High-speed impact with obstacle should crash the drone."""
        swarm = make_swarm_with_obstacle('box', collision_config={
            'enabled': True,
            'drone_radius': 0.3,
            'restitution': 0.3,
            'crash_speed': 5.0,
        })
        d0 = swarm.drones[0]
        d0.physics.position = np.array([2.2, 5.0, 0.0])
        d0.physics.velocity = np.array([-10.0, 0.0, 0.0])  # above crash_speed
        d0.controller.disarm()

        swarm._detect_collisions()

        assert d0.crashed, "Drone should crash on high-speed obstacle impact"

    def test_low_speed_no_crash_on_obstacle(self):
        """Low-speed impact with obstacle should not crash."""
        swarm = make_swarm_with_obstacle('box', collision_config={
            'enabled': True,
            'drone_radius': 0.3,
            'restitution': 0.3,
            'crash_speed': 8.0,
        })
        d0 = swarm.drones[0]
        d0.physics.position = np.array([2.2, 5.0, 0.0])
        d0.physics.velocity = np.array([-2.0, 0.0, 0.0])  # below crash_speed
        d0.controller.disarm()

        swarm._detect_collisions()

        assert not d0.crashed

    def test_crashed_drone_skips_obstacle_check(self):
        """Already crashed drones should not interact with obstacles."""
        swarm = make_swarm_with_obstacle('box')
        d0 = swarm.drones[0]
        d0.crashed = True
        d0.physics.position = np.array([2.2, 5.0, 0.0])
        d0.physics.velocity = np.array([-10.0, 0.0, 0.0])

        v_before = d0.physics.velocity.copy()
        swarm._detect_collisions()
        np.testing.assert_array_equal(d0.physics.velocity, v_before)

    def test_collision_disabled(self):
        """When collisions disabled, obstacles should not affect drones."""
        swarm = make_swarm_with_obstacle('box', collision_config={
            'enabled': False,
            'drone_radius': 0.3,
            'restitution': 0.3,
            'crash_speed': 8.0,
        })
        d0 = swarm.drones[0]
        d0.physics.position = np.array([2.2, 5.0, 0.0])
        d0.physics.velocity = np.array([-5.0, 0.0, 0.0])
        d0.controller.disarm()

        v_before = d0.physics.velocity.copy()
        swarm._detect_collisions()
        np.testing.assert_array_equal(d0.physics.velocity, v_before)

    def test_obstacle_in_update_loop(self):
        """Obstacle collision should fire during normal swarm.update()."""
        swarm = make_swarm_with_obstacle('box', collision_config={
            'enabled': True,
            'drone_radius': 0.3,
            'restitution': 0.5,
            'crash_speed': 100.0,
        })
        d0 = swarm.drones[0]
        d0.physics.position = np.array([2.2, 5.0, 0.0])
        d0.physics.velocity = np.array([-5.0, 0.0, 0.0])
        d0.controller.disarm()

        swarm.update(1.0 / 60.0)

        # After physics step + collision, velocity should change
        assert d0.physics.velocity[0] > -5.0

    def test_get_obstacle_states_through_swarm(self):
        """Swarm should expose obstacle states for GUI."""
        swarm = make_swarm_with_obstacle('box')
        states = swarm.get_obstacle_states()
        assert len(states) == 1
        assert states[0]['type'] == 'box'

    def test_no_obstacles_no_crash(self):
        """Swarm with no obstacles should not crash drones."""
        colors = [[1, 0, 0]]
        swarm = Swarm(1, colors, spacing=5.0, spawn_preset='line',
                      spawn_altitude=10.0, seed=42)
        d0 = swarm.drones[0]
        d0.physics.velocity = np.array([10.0, 0.0, 0.0])
        swarm._detect_collisions()
        assert not d0.crashed

    def test_drone_pushed_out_of_obstacle(self):
        """Drone overlapping obstacle should be pushed out."""
        swarm = make_swarm_with_obstacle('box', collision_config={
            'enabled': True,
            'drone_radius': 0.3,
            'restitution': 0.3,
            'crash_speed': 100.0,
        })
        d0 = swarm.drones[0]
        # Place drone partially inside the box
        # Box +X face is at x=2, drone at x=1.9 with radius 0.3
        d0.physics.position = np.array([1.9, 5.0, 0.0])
        d0.physics.velocity = np.array([-1.0, 0.0, 0.0])
        d0.controller.disarm()

        swarm._detect_collisions()

        # Drone should be pushed out to at least x = 2.0 + 0.3 (face + radius)
        # Actually, pushed by penetration along normal
        assert d0.physics.position[0] > 1.9, \
            f"Drone should be pushed out, but x={d0.physics.position[0]}"
