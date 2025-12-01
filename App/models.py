"""Data models and constants for the PolarPlot controller."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# AIDEV-NOTE: Hardware constants from Arduino firmware - keep in sync
MACHINE_WIDTH = 800.0  # mm
MACHINE_HEIGHT = 600.0  # mm
SAFE_MARGIN = 50.0  # mm from edges

# Configuration file path
CONFIG_FILE = Path.home() / ".polarplot_config.json"


class ConnectionState(Enum):
    """Serial connection states."""

    DISCONNECTED = "Disconnected"
    CONNECTING = "Connecting..."
    CONNECTED = "Connected"
    ERROR = "Error"


@dataclass
class MachineConfig:
    """Machine physical configuration settings."""

    # Physical dimensions in millimeters
    width: float = 800.0  # mm
    height: float = 600.0  # mm
    safe_margin: float = 50.0  # mm from edges

    # LED settings
    led_brightness: int = 128  # 0-255
    led_enabled: bool = True

    # Motor/Movement settings
    steps_per_mm: float = 5.035  # steps per millimeter
    steps_per_revolution: int = 200  # steps per motor revolution
    microstepping: int = 16  # microstepping setting

    speed: float = 100.0  # movement speed in mm/s
    acceleration: float = 500.0  # acceleration in mm/s^2


@dataclass
class PlotterState:
    """Current hardware state received from Arduino."""

    position_x: float = MACHINE_WIDTH / 2.0
    position_y: float = MACHINE_HEIGHT / 2.0
    left_cable: float = 0.0
    right_cable: float = 0.0
    steps_per_mm: float = 5.035
    connection: ConnectionState = ConnectionState.DISCONNECTED
