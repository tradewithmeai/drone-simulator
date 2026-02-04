"""Hardware Abstraction Layer for drone control.

Provides a unified interface for controlling drones whether running
in simulation or on real hardware. Control code imports from this
package and works identically in both environments.
"""

from hal.types import IMUReading, GPSReading, AltitudeReading, BatteryReading, DroneStatus
from hal.drone_hal import DroneHAL
