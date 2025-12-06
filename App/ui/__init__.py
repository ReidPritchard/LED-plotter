"""UI components for the PolarPlot controller.

This package contains modular UI panels that can be easily rearranged
in the application layout.
"""

from ui.command_panel import CommandPanel
from ui.config_panel import ConfigPanel
from ui.connection_panel import ConnectionPanel
from ui.console_panel import ConsolePanel
from ui.image_panel import ImagePanel
from ui.main_window import PlotterControlWindow
from ui.queue_panel import QueuePanel
from ui.simulation import SimulationUI
from ui.state_panel import StatePanel

__all__ = [
    "PlotterControlWindow",
    "ConnectionPanel",
    "ConfigPanel",
    "StatePanel",
    "QueuePanel",
    "CommandPanel",
    "ConsolePanel",
    "ImagePanel",
    "SimulationUI",
]
