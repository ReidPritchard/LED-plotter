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


class RenderStyle(Enum):
    """Image-to-path rendering styles.

    AIDEV-NOTE: Each style converts image brightness to drawable paths differently.
    """

    SINE_WAVES = "sine_waves"  # Horizontal waves with brightness-based amplitude/frequency
    STIPPLES = "stipples"  # Dots distributed based on brightness
    HATCHING = "hatching"  # Parallel lines with brightness-based density


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


# --- Image Processing Models ---


@dataclass
class ColoredPath:
    """A vectorized path with associated color.

    AIDEV-NOTE: Represents a single path segment from image vectorization.
    Points are in mm coordinates (machine space). Color is RGB (0-255).
    """

    points: "list[tuple[float, float]]"  # (x, y) coordinates in mm
    color: "tuple[int, int, int]"  # RGB color (0-255)
    is_closed: bool = False  # Whether path forms a closed loop


@dataclass
class ImageProcessingConfig:
    """Configuration for image vectorization and color quantization."""

    # Rendering style
    render_style: RenderStyle = RenderStyle.STIPPLES

    # Color quantization
    num_colors: int = 8  # Number of colors to quantize to (4-32)
    quantization_method: str = "kmeans"  # "kmeans", "median_cut", "octree"

    # VTracer settings
    filter_speckle: int = 4  # Discard patches smaller than X px
    color_precision: int = 6  # Color precision (1-8)

    # Path simplification
    simplify_tolerance: float = 0.5  # mm tolerance for Douglas-Peucker
    min_segment_length: float = 1.0  # Minimum segment length in mm

    # Sine wave style settings
    wave_line_spacing: float = 5.0  # Spacing between wave lines in mm
    wave_min_amplitude: float = 0.5  # Minimum wave amplitude in mm
    wave_max_amplitude: float = 4.0  # Maximum wave amplitude in mm
    wave_min_frequency: float = 0.5  # Minimum wave frequency (cycles per mm)
    wave_max_frequency: float = 3.0  # Maximum wave frequency (cycles per mm)

    # Stipples style settings
    stipple_density: float = 0.1  # Dots per mm²
    stipple_max_radius: float = 3.0  # Maximum dot radius in mm
    stipple_min_radius: float = 0.15  # Minimum dot radius in mm
    stipple_points_per_circle: int = 8  # Points per stipple circle

    # Should stipples be used to represent light areas instead of dark?
    # think black background with white dots
    stipple_invert: bool = False


@dataclass
class ProcessedImage:
    """Result of image processing pipeline."""

    # Extracted paths with colors
    paths: "list[ColoredPath]"

    # Color palette extracted from image
    palette: "list[tuple[int, int, int]]"

    # Style of rendering used
    render_style: RenderStyle

    # Scaling applied to fit machine bounds
    scale_factor: float = 1.0
    offset_x: float = 0.0  # X offset in mm
    offset_y: float = 0.0  # Y offset in mm

    # Original image dimensions (pixels)
    original_width: int = 0
    original_height: int = 0

    # Statistics
    total_path_length: float = 0.0  # Total path length in mm
    command_count: int = 0  # Number of commands that will be generated
