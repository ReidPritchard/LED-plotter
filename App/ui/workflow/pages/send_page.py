"""Send page combining QueuePanel and CommandPanel."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt

from models import MachineConfig
from ui.command_panel import CommandPanel
from ui.queue_panel import QueuePanel


class SendPage(QWidget):
    """Page combining queue and command panels for sending to plotter."""

    # Navigation signals
    go_to_connect = pyqtSignal()
    go_to_dashboard = pyqtSignal()

    def __init__(self, machine_config: MachineConfig, parent: QWidget | None = None):
        super().__init__(parent)
        self.machine_config = machine_config

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Initialize the page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet(
            """
            QSplitter::handle {
                background-color: #444;
                width: 4px;
            }
            QSplitter::handle:hover {
                background-color: #666;
            }
            """
        )

        # Queue panel on the left
        self.queue_panel = QueuePanel()
        splitter.addWidget(self.queue_panel)

        # Command panel on the right
        self.command_panel = CommandPanel(self.machine_config)
        splitter.addWidget(self.command_panel)

        # Set initial sizes (60% queue, 40% commands)
        splitter.setSizes([600, 400])

        layout.addWidget(splitter, stretch=1)

        # Navigation buttons
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(10)

        self.back_btn = QPushButton("< Connect")
        self.back_btn.setMinimumHeight(35)
        self.back_btn.setStyleSheet(self._nav_button_style())
        self.back_btn.clicked.connect(self.go_to_connect.emit)
        nav_layout.addWidget(self.back_btn)

        nav_layout.addStretch()

        self.dashboard_btn = QPushButton("Dashboard")
        self.dashboard_btn.setMinimumHeight(35)
        self.dashboard_btn.setStyleSheet(self._nav_button_style())
        self.dashboard_btn.clicked.connect(self.go_to_dashboard.emit)
        nav_layout.addWidget(self.dashboard_btn)

        layout.addLayout(nav_layout)

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
        """

    def get_queue_panel(self) -> QueuePanel:
        """Get the embedded QueuePanel for external access."""
        return self.queue_panel

    def get_command_panel(self) -> CommandPanel:
        """Get the embedded CommandPanel for external access."""
        return self.command_panel
