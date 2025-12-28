"""Preview page wrapper for SimulationUI."""

from typing import List

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from models import ColoredPath, MachineConfig, PlotterState  # type: ignore[attr-defined]
from ui.queue_panel import QueuePanel
from ui.simulation import SimulationUI


class PreviewPage(QWidget):
    """Page wrapper for the simulation preview with navigation."""

    # Navigation signals
    go_to_import = pyqtSignal()
    go_to_connect = pyqtSignal()

    def __init__(
        self,
        machine_config: MachineConfig,
        plotter_state: PlotterState,
        queue_panel: QueuePanel | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.machine_config = machine_config
        self.plotter_state = plotter_state
        self.queue_panel = queue_panel

        self._path_count = 0
        self._command_count = 0
        self.time_estimate = 0.0

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Initialize the page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Embed the SimulationUI
        # AIDEV-NOTE: SimulationUI takes queue_panel for queue execution simulation
        self.simulation_ui = SimulationUI(
            self.machine_config,
            self.plotter_state,
            self.queue_panel,
        )
        layout.addWidget(self.simulation_ui, stretch=1)

        # Statistics bar
        stats_frame = QFrame()
        stats_frame.setStyleSheet(
            """
            QFrame {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 5px;
            }
            """
        )
        stats_layout = QHBoxLayout(stats_frame)
        stats_layout.setContentsMargins(10, 5, 10, 5)

        self.paths_label = QLabel("Paths: 0")
        self.paths_label.setStyleSheet("color: #aaa;")
        stats_layout.addWidget(self.paths_label)

        stats_layout.addWidget(self._create_separator())

        self.commands_label = QLabel("Commands: 0")
        self.commands_label.setStyleSheet("color: #aaa;")
        stats_layout.addWidget(self.commands_label)

        stats_layout.addWidget(self._create_separator())

        self.time_label = QLabel("Est. Time: --")
        self.time_label.setStyleSheet("color: #aaa;")
        stats_layout.addWidget(self.time_label)

        stats_layout.addStretch()

        layout.addWidget(stats_frame)

        # Navigation buttons
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(10)

        self.back_btn = QPushButton("< Import")
        self.back_btn.setMinimumHeight(35)
        self.back_btn.setStyleSheet(self._nav_button_style())
        self.back_btn.clicked.connect(self.go_to_import.emit)
        nav_layout.addWidget(self.back_btn)

        nav_layout.addStretch()

        self.next_btn = QPushButton("Connect >")
        self.next_btn.setMinimumHeight(35)
        self.next_btn.setStyleSheet(self._nav_button_style())
        self.next_btn.clicked.connect(self.go_to_connect.emit)
        nav_layout.addWidget(self.next_btn)

        layout.addLayout(nav_layout)

    def _create_separator(self) -> QLabel:
        """Create a separator for the stats bar."""
        sep = QLabel("|")
        sep.setStyleSheet("color: #555;")
        return sep

    def _nav_button_style(self) -> str:
        """Get navigation button style."""
        return """
            QPushButton {
                background-color: #3d5a80;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4d6a90;
            }
            QPushButton:pressed {
                background-color: #2d4a70;
            }
            QPushButton:disabled {
                background-color: #333;
                color: #666;
            }
        """

    def set_preview_paths(self, paths: List[ColoredPath]) -> None:
        """Set paths for preview display."""
        self._path_count = len(paths)
        self.simulation_ui.set_preview_paths(paths)
        self._update_stats()

    def update_command_count(self, count: int) -> None:
        """Update the command count display."""
        self._command_count = count
        self._update_stats()

    def update_estimated_time(self, time_seconds: float) -> None:
        """Update the estimated time display."""
        if time_seconds <= 0:
            self.time_label.setText("Est. Time: --")
        elif time_seconds < 60:
            self.time_label.setText(f"Est. Time: {time_seconds:.0f}s")
        else:
            minutes = time_seconds / 60
            self.time_label.setText(f"Est. Time: {minutes:.1f}min")

    def _update_stats(self) -> None:
        """Update statistics display."""
        self.paths_label.setText(f"Paths: {self._path_count}")
        self.commands_label.setText(f"Commands: {self._command_count}")

    def get_simulation_ui(self) -> SimulationUI:
        """Get the embedded SimulationUI for external access."""
        return self.simulation_ui
