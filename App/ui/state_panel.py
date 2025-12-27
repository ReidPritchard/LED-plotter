"""Hardware state display panel."""

from PyQt6.QtWidgets import QFormLayout, QGroupBox, QLabel, QPushButton

from models import MachineConfig, PlotterState


class StatePanel(QGroupBox):
    """Panel displaying current hardware state."""

    def __init__(
        self,
        plotter_state: PlotterState,
        machine_config: MachineConfig,
        parent=None,
    ):
        super().__init__(None, parent)
        self.plotter_state = plotter_state
        self.machine_config = machine_config
        self._setup_ui()

    def _setup_ui(self):
        """Initialize the UI components."""
        layout = QFormLayout()

        # Position display
        self.pos_x_label = QLabel(f"{self.plotter_state.position_x:.1f} mm")
        self.pos_y_label = QLabel(f"{self.plotter_state.position_y:.1f} mm")
        layout.addRow("Position X:", self.pos_x_label)
        layout.addRow("Position Y:", self.pos_y_label)

        # Cable lengths
        self.left_cable_label = QLabel(f"{self.plotter_state.left_cable:.1f} mm")
        self.right_cable_label = QLabel(f"{self.plotter_state.right_cable:.1f} mm")
        layout.addRow("Left Cable:", self.left_cable_label)
        layout.addRow("Right Cable:", self.right_cable_label)

        # Calibration
        self.steps_per_mm_label = QLabel(f"{self.plotter_state.steps_per_mm:.4f}")
        layout.addRow("Steps/mm:", self.steps_per_mm_label)

        # Machine dimensions (from config)
        layout.addRow("", QLabel(""))  # Spacer
        self.config_width_label = QLabel(f"{self.machine_config.width:.0f} mm")
        self.config_height_label = QLabel(f"{self.machine_config.height:.0f} mm")
        self.config_margin_label = QLabel(f"{self.machine_config.safe_margin:.0f} mm")
        layout.addRow("Machine Width:", self.config_width_label)
        layout.addRow("Machine Height:", self.config_height_label)
        layout.addRow("Safe Margin:", self.config_margin_label)

        # Request status button
        self.status_btn = QPushButton("🔄 Request Status (?)")
        layout.addRow("", self.status_btn)

        self.setLayout(layout)

    def update_state(self, plotter_state: PlotterState):
        """Update the display with new state values."""
        self.plotter_state = plotter_state
        self.pos_x_label.setText(f"{plotter_state.position_x:.1f} mm")
        self.pos_y_label.setText(f"{plotter_state.position_y:.1f} mm")
        self.left_cable_label.setText(f"{plotter_state.left_cable:.1f} mm")
        self.right_cable_label.setText(f"{plotter_state.right_cable:.1f} mm")
        self.steps_per_mm_label.setText(f"{plotter_state.steps_per_mm:.4f}")

    def update_config_display(self, machine_config: MachineConfig):
        """Update the machine config display."""
        self.machine_config = machine_config
        self.config_width_label.setText(f"{machine_config.width:.0f} mm")
        self.config_height_label.setText(f"{machine_config.height:.0f} mm")
        self.config_margin_label.setText(f"{machine_config.safe_margin:.0f} mm")
