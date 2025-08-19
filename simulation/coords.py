"""Coordinate system mapping utilities."""

from typing import Tuple, List

Vec3 = Tuple[float, float, float]

def map_up_axis(pos: Vec3, up_axis: str) -> Vec3:
    """Map position coordinates based on up-axis configuration.
    
    Args:
        pos: Position tuple (x, y_ground, z_alt) from spawn
        up_axis: "y" for Y-up (altitude->Y, ground->XZ) or "z" for Z-up (altitude->Z, ground->XY)
        
    Returns:
        Mapped position tuple for rendering system
    """
    x, y, z = pos
    ua = (up_axis or "y").lower()
    
    if ua == "y":
        # Y is up: interpret altitude as Y, ground-plane is XZ
        # Incoming spawn is (x, y_ground, z_alt) -> map altitude into Y
        return (x, z, y)  # x stays x, altitude (z) becomes y, ground (y) becomes z
    else:
        # Default Z-up: ground-plane XY, altitude Z  
        return (x, y, z)  # Keep as-is

def map_positions_list(positions: List[Vec3], up_axis: str) -> List[Vec3]:
    """Map a list of positions using the specified up-axis.
    
    Args:
        positions: List of position tuples
        up_axis: Up-axis configuration
        
    Returns:
        List of mapped position tuples
    """
    return [map_up_axis(pos, up_axis) for pos in positions]

def get_bounding_box(positions: List[Vec3]) -> Tuple[Vec3, Vec3, Vec3]:
    """Calculate bounding box and centroid for camera framing.
    
    Args:
        positions: List of position tuples
        
    Returns:
        Tuple of (min_pos, max_pos, centroid)
    """
    if not positions:
        return (0, 0, 0), (0, 0, 0), (0, 0, 0)
    
    xs = [p[0] for p in positions]
    ys = [p[1] for p in positions] 
    zs = [p[2] for p in positions]
    
    min_pos = (min(xs), min(ys), min(zs))
    max_pos = (max(xs), max(ys), max(zs))
    centroid = ((min(xs) + max(xs)) * 0.5, 
                (min(ys) + max(ys)) * 0.5, 
                (min(zs) + max(zs)) * 0.5)
    
    return min_pos, max_pos, centroid

def calculate_camera_distance(min_pos: Vec3, max_pos: Vec3, min_distance: float = 20.0) -> float:
    """Calculate appropriate camera distance for framing.
    
    Args:
        min_pos: Minimum position bounds
        max_pos: Maximum position bounds
        min_distance: Minimum camera distance
        
    Returns:
        Recommended camera distance
    """
    span_x = max_pos[0] - min_pos[0]
    span_y = max_pos[1] - min_pos[1] 
    span_z = max_pos[2] - min_pos[2]
    
    max_span = max(span_x, span_y, span_z)
    return max(min_distance, max_span * 1.5)