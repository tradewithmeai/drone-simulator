"""Serializers for converting HAL readings to JSON-safe dicts.

HAL sensor readings contain numpy arrays which aren't JSON-serializable.
These helpers convert everything to plain Python types.
"""

import numpy as np


def _arr(v) -> list:
    """Convert numpy array or list-like to plain Python list of floats."""
    if isinstance(v, np.ndarray):
        return v.tolist()
    if isinstance(v, (list, tuple)):
        return [float(x) for x in v]
    return v


def serialize_imu(reading) -> dict:
    return {
        'timestamp': float(reading.timestamp),
        'accel': _arr(reading.accel),
        'gyro': _arr(reading.gyro),
    }


def serialize_gps(reading) -> dict:
    return {
        'timestamp': float(reading.timestamp),
        'position': _arr(reading.position),
        'velocity': _arr(reading.velocity),
        'accuracy_h': float(reading.accuracy_h),
        'accuracy_v': float(reading.accuracy_v),
        'fix_type': int(reading.fix_type),
    }


def serialize_altitude(reading) -> dict:
    return {
        'timestamp': float(reading.timestamp),
        'altitude_baro': float(reading.altitude_baro),
        'altitude_agl': float(reading.altitude_agl),
        'altitude_gps': float(reading.altitude_gps),
    }


def serialize_battery(reading) -> dict:
    return {
        'timestamp': float(reading.timestamp),
        'voltage': float(reading.voltage),
        'current': float(reading.current),
        'remaining_pct': float(reading.remaining_pct),
    }


def serialize_status(reading) -> dict:
    return {
        'timestamp': float(reading.timestamp),
        'armed': bool(reading.armed),
        'mode': str(reading.mode),
        'airborne': bool(reading.airborne),
        'error_flags': int(reading.error_flags),
    }


def serialize_ground_truth(gt: dict) -> dict:
    """Convert ground truth dict (contains numpy arrays) to JSON-safe dict."""
    return {k: _arr(v) if isinstance(v, np.ndarray) else v for k, v in gt.items()}


def sanitize(obj):
    """Recursively convert numpy types to plain Python types for JSON."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize(x) for x in obj]
    return obj


def serialize_drone_state(state: dict) -> dict:
    """Convert a drone state dict to JSON-safe dict.

    Drone states from get_states() already use plain lists for positions,
    but this ensures everything is serializable.
    """
    return sanitize(state)
