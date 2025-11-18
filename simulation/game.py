"""
Game logic for hide-and-seek drone swarm game.
Manages detection, game state, win conditions, and AI behaviors.
"""
import numpy as np
import random
import time
from typing import List, Dict, Tuple, Optional
from .drone import Drone
from .environment import Environment


class HideAndSeekGame:
    """Manages hide-and-seek game logic."""

    def __init__(self, environment: Environment, detection_radius: float = 5.0,
                 catch_radius: float = 1.5, game_duration: float = 120.0):
        """
        Initialize the game manager.

        Args:
            environment: Environment with obstacles
            detection_radius: Distance at which seekers detect hiders
            catch_radius: Distance at which seekers catch hiders
            game_duration: Game time limit in seconds
        """
        self.environment = environment
        self.detection_radius = detection_radius
        self.catch_radius = catch_radius
        self.game_duration = game_duration

        # Game state
        self.game_active = False
        self.game_start_time = None
        self.game_end_time = None
        self.winner = None  # "seekers" or "hiders"

        # Statistics
        self.total_hiders = 0
        self.caught_count = 0
        self.detection_events = []  # Log of detection events

    def start_game(self):
        """Start a new game round."""
        self.game_active = True
        self.game_start_time = time.time()
        self.game_end_time = None
        self.winner = None
        self.caught_count = 0
        self.detection_events = []
        print(f"[GAME] Hide-and-seek game started! Duration: {self.game_duration}s")

    def end_game(self, winner: str):
        """End the game with a winner."""
        self.game_active = False
        self.game_end_time = time.time()
        self.winner = winner
        duration = self.game_end_time - self.game_start_time
        print(f"[GAME] Game over! Winner: {winner.upper()} - Duration: {duration:.1f}s")

    def get_elapsed_time(self) -> float:
        """Get elapsed game time in seconds."""
        if not self.game_start_time:
            return 0.0
        if self.game_end_time:
            return self.game_end_time - self.game_start_time
        return time.time() - self.game_start_time

    def get_remaining_time(self) -> float:
        """Get remaining game time in seconds."""
        if not self.game_active:
            return 0.0
        elapsed = self.get_elapsed_time()
        return max(0.0, self.game_duration - elapsed)

    def update(self, drones: List[Drone]) -> Dict:
        """
        Update game logic including detection and win conditions.

        Args:
            drones: List of all drones

        Returns:
            Dictionary with game status information
        """
        if not self.game_active:
            return self._get_status(drones)

        # Check time limit
        if self.get_remaining_time() <= 0:
            # Time's up - hiders win if any are still free
            uncaught_hiders = sum(1 for d in drones if d.role == "hider" and not d.caught)
            if uncaught_hiders > 0:
                self.end_game("hiders")
            else:
                self.end_game("seekers")
            return self._get_status(drones)

        # Separate drones by role
        seekers = [d for d in drones if d.role == "seeker"]
        hiders = [d for d in drones if d.role == "hider"]

        # Update detection and catching
        for seeker in seekers:
            for hider in hiders:
                if hider.caught:
                    continue

                distance = np.linalg.norm(seeker.position - hider.position)

                # Check for catch (closer than catch radius)
                if distance <= self.catch_radius:
                    self._catch_hider(hider, seeker)
                    continue

                # Check for detection (within detection radius AND line of sight)
                if distance <= self.detection_radius:
                    # Check line of sight
                    if self.environment.is_line_of_sight_clear(seeker.position, hider.position):
                        self._detect_hider(hider, seeker)

        # Check win condition - all hiders caught
        if all(h.caught for h in hiders):
            self.end_game("seekers")

        return self._get_status(drones)

    def _detect_hider(self, hider: Drone, seeker: Drone):
        """Mark a hider as detected."""
        if not hider.detected:
            hider.detected = True
            hider.detection_time = time.time()
            self.detection_events.append({
                'time': self.get_elapsed_time(),
                'hider_id': hider.id,
                'seeker_id': seeker.id
            })
            print(f"[GAME] Seeker #{seeker.id} detected Hider #{hider.id}!")

    def _catch_hider(self, hider: Drone, seeker: Drone):
        """Mark a hider as caught."""
        if not hider.caught:
            hider.caught = True
            hider.detected = True
            self.caught_count += 1
            print(f"[GAME] Seeker #{seeker.id} caught Hider #{hider.id}! ({self.caught_count}/{self.total_hiders})")

    def _get_status(self, drones: List[Drone]) -> Dict:
        """Get current game status."""
        hiders = [d for d in drones if d.role == "hider"]
        seekers = [d for d in drones if d.role == "seeker"]

        return {
            'active': self.game_active,
            'elapsed_time': self.get_elapsed_time(),
            'remaining_time': self.get_remaining_time(),
            'total_hiders': len(hiders),
            'caught_count': self.caught_count,
            'uncaught_count': sum(1 for h in hiders if not h.caught),
            'detected_count': sum(1 for h in hiders if h.detected and not h.caught),
            'seeker_count': len(seekers),
            'winner': self.winner
        }


class SimpleAI:
    """Simple AI behaviors for hide-and-seek game."""

    def __init__(self, environment: Environment):
        self.environment = environment
        self.hiding_spots = environment.find_hiding_spots(num_spots=20)
        self.patrol_points = self._generate_patrol_points(num_points=12)

    def _generate_patrol_points(self, num_points: int) -> List[np.ndarray]:
        """Generate patrol waypoints covering the play area."""
        patrol_points = []
        half_area = self.environment.play_area_size / 2.0
        margin = 10.0

        # Create a grid of patrol points
        side_points = int(np.sqrt(num_points))
        for i in range(side_points):
            for j in range(side_points):
                x = -half_area + margin + (i / (side_points - 1)) * (self.environment.play_area_size - 2 * margin)
                z = -half_area + margin + (j / (side_points - 1)) * (self.environment.play_area_size - 2 * margin)
                y = 5.0  # Fixed patrol height

                position = np.array([x, y, z])
                patrol_points.append(position)

        return patrol_points

    def update_seeker_ai(self, seeker: Drone, hiders: List[Drone], current_time: float):
        """
        Update seeker AI behavior.
        Simple patrol behavior - move to random patrol points.
        """
        # Update target every 5 seconds or when settled
        if current_time - seeker.last_target_update > 5.0 or seeker.settled:
            # Check if any hiders are visible
            visible_hiders = []
            for hider in hiders:
                if hider.caught:
                    continue

                distance = np.linalg.norm(seeker.position - hider.position)
                if distance <= 15.0:  # Extended vision range for chasing
                    if self.environment.is_line_of_sight_clear(seeker.position, hider.position):
                        visible_hiders.append((hider, distance))

            if visible_hiders:
                # Chase closest visible hider
                visible_hiders.sort(key=lambda x: x[1])
                target_hider = visible_hiders[0][0]
                seeker.set_target(target_hider.position)
                seeker.behavior_state = "chase"
            else:
                # Patrol - move to random patrol point
                patrol_point = random.choice(self.patrol_points)
                seeker.set_target(patrol_point)
                seeker.behavior_state = "patrol"

            seeker.last_target_update = current_time

    def update_hider_ai(self, hider: Drone, seekers: List[Drone], current_time: float):
        """
        Update hider AI behavior.
        Simple hiding behavior - move to hiding spots, flee if detected.
        """
        if hider.caught:
            # Stay still when caught
            hider.behavior_state = "caught"
            return

        # Check if any seekers are nearby
        nearby_seekers = []
        for seeker in seekers:
            distance = np.linalg.norm(seeker.position - hider.position)
            if distance <= 10.0:  # Danger zone
                nearby_seekers.append((seeker, distance))

        if hider.detected or nearby_seekers:
            # FLEE - move away from closest seeker
            if nearby_seekers:
                nearby_seekers.sort(key=lambda x: x[1])
                closest_seeker = nearby_seekers[0][0]

                # Move in opposite direction
                flee_direction = hider.position - closest_seeker.position
                flee_distance = np.linalg.norm(flee_direction)
                if flee_distance > 0:
                    flee_direction = flee_direction / flee_distance
                    flee_target = hider.position + flee_direction * 15.0

                    # Make sure flee target is in play area
                    half_area = self.environment.play_area_size / 2.0
                    flee_target[0] = np.clip(flee_target[0], -half_area + 5, half_area - 5)
                    flee_target[2] = np.clip(flee_target[2], -half_area + 5, half_area - 5)
                    flee_target[1] = np.clip(flee_target[1], 2.0, 10.0)

                    hider.set_target(flee_target)
                    hider.behavior_state = "flee"
                    hider.last_target_update = current_time
        else:
            # HIDE - move to nearest hiding spot
            if current_time - hider.last_target_update > 8.0 or hider.settled:
                # Find best hiding spot (closest one)
                best_spot = None
                best_distance = float('inf')

                for spot in self.hiding_spots:
                    distance = np.linalg.norm(hider.position - spot)
                    if distance < best_distance:
                        best_distance = distance
                        best_spot = spot

                if best_spot is not None:
                    hider.set_target(best_spot)
                    hider.behavior_state = "hide"
                    hider.last_target_update = current_time
