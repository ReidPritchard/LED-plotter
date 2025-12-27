"""Centralized styling constants for the LED-plotter UI.

This module consolidates colors, fonts, and sizes used throughout the application
to ensure consistency and easier maintenance.
"""

from PyQt6.QtGui import QColor, QFont


class StatusColors:
    """Connection status indicator colors."""

    CONNECTED = "green"
    CONNECTING = "orange"
    ERROR = "red"
    DISCONNECTED = "gray"


class ThemeColors:
    """Application theme colors for simulation and UI elements."""

    # Background colors
    BACKGROUND_DARK = QColor(20, 20, 20)
    BACKGROUND_PANEL = "#2a2a2a"

    # UI borders and frames
    BORDER_DEFAULT = "gray"
    MACHINE_FRAME = QColor(60, 60, 60)
    MOTOR_BODY = QColor(40, 40, 40)
    WORK_AREA = QColor(150, 150, 150)

    # Cable colors (left = reddish, right = bluish)
    CABLE_LEFT = QColor(200, 100, 100)
    CABLE_RIGHT = QColor(100, 100, 200)

    # Safe area and boundaries
    SAFE_AREA_BORDER = QColor(100, 200, 100)

    # Path and trail visualization
    TRAIL_PATH = QColor(0, 150, 0)

    # LED default color
    LED_DEFAULT = (255, 100, 0)  # Orange


class Fonts:
    """Standard application fonts."""

    CONSOLE = QFont("Courier", 9)
    STATUS_INDICATOR = QFont("Arial", 16)


class Sizes:
    """Standard widget sizes and constraints."""

    # Console panel
    CONSOLE_MIN_HEIGHT = 100  # Removed max constraint for overflow fix

    # Image preview
    PREVIEW_MIN_SIZE = (200, 150)
    PREVIEW_MAX_SIZE = (400, 300)

    # Connection panel
    PORT_COMBO_MIN_WIDTH = 250

    # Buttons and controls
    BUTTON_MIN_WIDTH = 100
    TOGGLE_BUTTON_MAX_WIDTH = 35
    LABEL_MIN_WIDTH = 40

    # Simulation canvas
    SIMULATION_MIN_SIZE = (400, 300)
    SIMULATION_PADDING = 40  # pixels

    # UI spacing
    MOTOR_RADIUS = 8
    GONDOLA_RADIUS = 6


# Convenience aliases for backward compatibility
STATUS = StatusColors
COLORS = ThemeColors
FONTS = Fonts
SIZES = Sizes


def status_stylesheet(state: str) -> str:
    """Generate status indicator stylesheet for connection state.

    Args:
        state: Connection state ('CONNECTED', 'CONNECTING', 'ERROR', 'DISCONNECTED')

    Returns:
        CSS stylesheet string with appropriate color
    """
    color = getattr(StatusColors, state.upper(), StatusColors.DISCONNECTED)
    return f"color: {color};"


def panel_stylesheet() -> str:
    """Generate standard panel stylesheet with border and background.

    Returns:
        CSS stylesheet string for panel styling
    """
    return (
        f"border: 1px solid {ThemeColors.BORDER_DEFAULT}; "
        f"background-color: {ThemeColors.BACKGROUND_PANEL};"
    )
