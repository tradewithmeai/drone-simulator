import math
import random
from typing import List, Tuple

Vec3 = Tuple[float, float, float]

def make_positions(n: int, preset: str, spacing: float, alt: float, seed: int = 42) -> List[Vec3]:
    """
    Generate drone spawn positions for various formation presets.
    
    Args:
        n: Number of drones
        preset: Formation type ('v', 'line', 'circle', 'grid', 'random')
        spacing: Inter-drone spacing in meters
        alt: Altitude (Y coordinate) for all drones
        seed: Random seed for deterministic placement
        
    Returns:
        List of (x, y, z) positions
    """
    preset = (preset or "v").lower()
    if n <= 0:
        return []
        
    if preset == "line":
        return _line(n, spacing, alt)
    elif preset == "circle":
        return _circle(n, spacing, alt)
    elif preset == "grid":
        return _grid(n, spacing, alt)
    elif preset == "random":
        return _random(n, spacing, alt, seed)
    else:  # default to v formation
        return _v(n, spacing, alt)

def _line(n: int, d: float, z: float) -> List[Vec3]:
    """Line formation centered on origin along X axis."""
    start = -(n - 1) * 0.5 * d
    return [(start + i * d, 0.0, z) for i in range(n)]

def _circle(n: int, d: float, z: float) -> List[Vec3]:
    """Circle formation with approximate spacing d between adjacent drones."""
    # Calculate radius to achieve desired spacing along the circumference
    r = max(d, d / (2 * math.sin(math.pi / max(n, 3))))
    return [(r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n), z) for i in range(n)]

def _v(n: int, d: float, z: float, theta_deg: float = 40.0) -> List[Vec3]:
    """V formation with leader at origin and wings at +/- theta angle."""
    theta = math.radians(theta_deg)
    out = [(0.0, 0.0, z)]  # Leader at origin
    left, right = [], []
    
    for k in range(1, n):
        arm = (k + 1) // 2  # Distance from leader along wing
        sign = +1 if k % 2 == 1 else -1  # Alternate right/left for symmetry
        x = arm * d * math.cos(theta)
        y = sign * arm * d * math.sin(theta)
        (right if sign > 0 else left).append((x, y, z))
    
    # Interleave right and left wings for stable ordering
    interleaved = []
    for i in range(max(len(left), len(right))):
        if i < len(right):
            interleaved.append(right[i])
        if i < len(left):
            interleaved.append(left[i])
    
    return out + interleaved[:n-1]

def _grid(n: int, d: float, z: float) -> List[Vec3]:
    """Grid formation centered on origin."""
    rows = int(math.floor(math.sqrt(n)))
    cols = int(math.ceil(n / rows))
    ox = -(cols - 1) * 0.5 * d  # X offset to center grid
    oy = -(rows - 1) * 0.5 * d  # Y offset to center grid
    
    out = []
    idx = 0
    for r in range(rows):
        for c in range(cols):
            if idx >= n:
                break
            out.append((ox + c * d, oy + r * d, z))
            idx += 1
    return out

def _random(n: int, d: float, z: float, seed: int) -> List[Vec3]:
    """Random formation within a square area."""
    random.seed(seed)
    # Spread within a square area proportional to number of drones
    span = max(d * math.sqrt(n), d * 3.0)
    half = span * 0.5
    return [(random.uniform(-half, half), random.uniform(-half, half), z) for _ in range(n)]

def get_preset_names() -> List[str]:
    """Get list of available formation preset names."""
    return ["v", "line", "circle", "grid", "random"]