"""Command input and control panel."""

from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from models import MachineConfig
from ui.widgets import WidgetFactory


class CommandPanel(QGroupBox):
    """Panel for command input and quick actions."""

    def __init__(self, machine_config: MachineConfig, parent=None):
        super().__init__("Commands", parent)
        self.machine_config = machine_config
        self._setup_ui()

    def _setup_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout()

        # Quick action buttons
        quick_layout = QHBoxLayout()

        self.home_btn = QPushButton("🏠 Home (H)")
        quick_layout.addWidget(self.home_btn)

        self.test_btn = QPushButton("🔲 Test Square (T)")
        quick_layout.addWidget(self.test_btn)

        self.calibrate_btn = QPushButton("📏 Calibrate (C)")
        quick_layout.addWidget(self.calibrate_btn)

        layout.addLayout(quick_layout)

        # Move to position
        move_layout = QHBoxLayout()
        move_layout.addWidget(QLabel("Move to:"))

        # AIDEV-NOTE: Coordinate inputs with bounds validation from machine_config
        self.move_x_input = WidgetFactory.create_double_spinbox(
            self.machine_config.safe_margin,
            self.machine_config.width - self.machine_config.safe_margin,
            self.machine_config.width / 2.0,
            " mm",
            decimals=1,
        )
        move_layout.addWidget(QLabel("X:"))
        move_layout.addWidget(self.move_x_input)

        self.move_y_input = WidgetFactory.create_double_spinbox(
            self.machine_config.safe_margin,
            self.machine_config.height - self.machine_config.safe_margin,
            self.machine_config.height / 2.0,
            " mm",
            decimals=1,
        )
        move_layout.addWidget(QLabel("Y:"))
        move_layout.addWidget(self.move_y_input)

        self.queue_move_btn = QPushButton("➡️ Queue Move")
        move_layout.addWidget(self.queue_move_btn)

        self.move_now_btn = QPushButton("⚡ Move Now")
        move_layout.addWidget(self.move_now_btn)

        layout.addLayout(move_layout)

        # Custom command input
        custom_layout = QHBoxLayout()
        custom_layout.addWidget(QLabel("Custom:"))
        self.custom_input = QLineEdit()
        self.custom_input.setPlaceholderText("Enter raw command (e.g., M 400 300)")
        custom_layout.addWidget(self.custom_input)

        self.send_custom_btn = QPushButton("Send")
        custom_layout.addWidget(self.send_custom_btn)

        layout.addLayout(custom_layout)
        self.setLayout(layout)

    def get_move_coordinates(self) -> "tuple[float, float]":
        """Get the current move X, Y coordinates."""
        return self.move_x_input.value(), self.move_y_input.value()

    def get_custom_command(self) -> str:
        """Get the custom command text."""
        return self.custom_input.text().strip()

    def clear_custom_command(self):
        """Clear the custom command input."""
        self.custom_input.clear()

    def update_move_bounds(self, machine_config: MachineConfig):
        """Update the move input spinbox bounds based on config."""
        # Store current values to restore if they're still valid
        current_x = self.move_x_input.value()
        current_y = self.move_y_input.value()

        # Update X bounds
        x_min = machine_config.safe_margin
        x_max = machine_config.width - machine_config.safe_margin
        self.move_x_input.setRange(x_min, x_max)

        # Update Y bounds
        y_min = machine_config.safe_margin
        y_max = machine_config.height - machine_config.safe_margin
        self.move_y_input.setRange(y_min, y_max)

        # Restore values if still valid, otherwise center
        if x_min <= current_x <= x_max:
            self.move_x_input.setValue(current_x)
        else:
            self.move_x_input.setValue(machine_config.width / 2.0)

        if y_min <= current_y <= y_max:
            self.move_y_input.setValue(current_y)
        else:
            self.move_y_input.setValue(machine_config.height / 2.0)
