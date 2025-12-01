"""Settings dialog for machine configuration."""

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QVBoxLayout,
)

from models import MachineConfig
from ui.config_panel import ConfigPanel


class SettingsDialog(QDialog):
    """Dialog window for editing machine configuration settings."""

    def __init__(self, machine_config: MachineConfig, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PolarPlot Settings")
        self.setMinimumWidth(600)
        self.machine_config = machine_config
        self._setup_ui()

    def _setup_ui(self):
        """Initialize the dialog UI."""
        layout = QVBoxLayout()

        # AIDEV-NOTE: ConfigPanel handles machine dimensions and margins
        self.config_panel = ConfigPanel(self.machine_config)
        layout.addWidget(self.config_panel)

        # Dialog buttons (OK/Cancel)
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def get_values(self) -> MachineConfig:
        """Get configuration values from the panel."""
        return self.config_panel.get_values()

    def set_values(
        self,
        width: float,
        height: float,
        margin: float,
        led_enabled: bool,
        led_brightness: int,
        steps_per_mm: float,
        microstepping: int,
        speed: float,
        acceleration: float,
    ):
        """Set configuration values in the panel."""
        self.config_panel.set_values(
            width,
            height,
            margin,
            led_enabled,
            led_brightness,
            steps_per_mm,
            microstepping,
            speed,
            acceleration,
        )
