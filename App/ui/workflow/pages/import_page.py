"""Import page wrapper for ImagePanel."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from models import MachineConfig
from ui.image_panel import ImagePanel


class ImportPage(QWidget):
    """Page wrapper for the image import panel with navigation."""

    # Navigation signals
    go_to_dashboard = pyqtSignal()
    go_to_preview = pyqtSignal()

    def __init__(self, machine_config: MachineConfig, parent: QWidget | None = None):
        super().__init__(parent)
        self.machine_config = machine_config

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Initialize the page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Embed the ImagePanel
        self.image_panel = ImagePanel(self.machine_config)
        layout.addWidget(self.image_panel, stretch=1)

        # Navigation buttons
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(10)

        self.back_btn = QPushButton("< Dashboard")
        self.back_btn.setMinimumHeight(35)
        self.back_btn.setStyleSheet(self._nav_button_style())
        self.back_btn.clicked.connect(self.go_to_dashboard.emit)
        nav_layout.addWidget(self.back_btn)

        nav_layout.addStretch()

        self.next_btn = QPushButton("Preview >")
        self.next_btn.setMinimumHeight(35)
        self.next_btn.setEnabled(False)  # Enabled when image is processed
        self.next_btn.setStyleSheet(self._nav_button_style())
        self.next_btn.clicked.connect(self.go_to_preview.emit)
        nav_layout.addWidget(self.next_btn)

        layout.addLayout(nav_layout)

        # Connect internal signals to enable/disable navigation
        self.image_panel.processing_complete.connect(self._on_processing_complete)

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

    def _on_processing_complete(self, processed_image) -> None:
        """Enable preview navigation when image is processed."""
        self.next_btn.setEnabled(True)

    def get_image_panel(self) -> ImagePanel:
        """Get the embedded ImagePanel for signal connections."""
        return self.image_panel
