"""Machine configuration panel."""

from PyQt6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QPushButton,
    QVBoxLayout,
)

from models import MachineConfig


class ConfigPanel(QGroupBox):
    """Panel for machine dimension and margin configuration."""

    def __init__(self, machine_config: MachineConfig, parent=None):
        super().__init__("Machine Configuration", parent)
        self.machine_config = machine_config
        self._setup_ui()

    def _setup_ui(self):
        """Initialize the UI components."""
        main_layout = QVBoxLayout()

        # --- Machine Dimensions Group ---
        machine_group = QGroupBox("Machine Dimensions")
        machine_layout = QFormLayout()
        self.width_input = QDoubleSpinBox()
        self.width_input.setRange(100, 5000)
        self.width_input.setValue(self.machine_config.width)
        self.width_input.setSuffix(" mm")
        self.width_input.setDecimals(0)
        machine_layout.addRow("Width:", self.width_input)

        self.height_input = QDoubleSpinBox()
        self.height_input.setRange(100, 5000)
        self.height_input.setValue(self.machine_config.height)
        self.height_input.setSuffix(" mm")
        self.height_input.setDecimals(0)
        machine_layout.addRow("Height:", self.height_input)

        self.margin_input = QDoubleSpinBox()
        self.margin_input.setRange(0, 200)
        self.margin_input.setValue(self.machine_config.safe_margin)
        self.margin_input.setSuffix(" mm")
        self.margin_input.setDecimals(0)
        machine_layout.addRow("Margin:", self.margin_input)

        machine_group.setLayout(machine_layout)
        main_layout.addWidget(machine_group)

        # --- LED Settings Group ---
        led_group = QGroupBox("LED Settings")
        led_layout = QFormLayout()
        self.led_enabled_btn = QPushButton(
            "On" if self.machine_config.led_enabled else "Off"
        )
        self.led_enabled_btn.setCheckable(True)
        self.led_enabled_btn.setChecked(self.machine_config.led_enabled)
        led_layout.addRow("LED Enabled:", self.led_enabled_btn)

        self.led_brightness_input = QDoubleSpinBox()
        self.led_brightness_input.setRange(0, 255)
        self.led_brightness_input.setValue(self.machine_config.led_brightness)
        self.led_brightness_input.setSuffix(" (0-255)")
        self.led_brightness_input.setDecimals(0)
        led_layout.addRow("LED Brightness:", self.led_brightness_input)

        led_group.setLayout(led_layout)
        main_layout.addWidget(led_group)

        # --- Motor Settings Group ---
        motor_group = QGroupBox("Motor Settings")
        motor_layout = QFormLayout()
        self.steps_per_mm_input = QDoubleSpinBox()
        self.steps_per_mm_input.setRange(0.1, 20.0)
        self.steps_per_mm_input.setValue(self.machine_config.steps_per_mm)
        self.steps_per_mm_input.setDecimals(3)
        motor_layout.addRow("Steps per mm:", self.steps_per_mm_input)

        self.microstepping_input = QDoubleSpinBox()
        self.microstepping_input.setRange(1, 256)
        self.microstepping_input.setValue(self.machine_config.microstepping)
        self.microstepping_input.setDecimals(0)
        motor_layout.addRow("Microstepping:", self.microstepping_input)

        self.speed_input = QDoubleSpinBox()
        self.speed_input.setRange(10, 1000)
        self.speed_input.setValue(self.machine_config.speed)
        self.speed_input.setSuffix(" mm/s")
        self.speed_input.setDecimals(0)
        motor_layout.addRow("Speed:", self.speed_input)

        self.acceleration_input = QDoubleSpinBox()
        self.acceleration_input.setRange(10, 5000)
        self.acceleration_input.setValue(self.machine_config.acceleration)
        self.acceleration_input.setSuffix(" mm/s²")
        self.acceleration_input.setDecimals(0)
        motor_layout.addRow("Acceleration:", self.acceleration_input)

        motor_group.setLayout(motor_layout)
        main_layout.addWidget(motor_group)

        # --- Reset Button ---
        self.reset_btn = QPushButton("↺ Reset to Defaults")
        self.reset_btn.setToolTip(
            "Reset to default values (800×600mm, 50mm margin)"
        )
        main_layout.addWidget(self.reset_btn)

        main_layout.addStretch()
        self.setLayout(main_layout)

    def get_values(self) -> MachineConfig:
        """Get input values as MachineConfig."""
        return MachineConfig(
            self.width_input.value(),
            self.height_input.value(),
            self.margin_input.value(),
            int(self.led_brightness_input.value()),
            self.led_enabled_btn.isChecked(),
            self.steps_per_mm_input.value(),
            self.machine_config.steps_per_revolution,  # Use existing value
            int(self.microstepping_input.value()),
            self.speed_input.value(),
            self.acceleration_input.value(),
        )

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
        """Set input values."""
        self.width_input.setValue(width)
        self.height_input.setValue(height)
        self.margin_input.setValue(margin)
        self.led_enabled_btn.setChecked(led_enabled)
        self.led_enabled_btn.setText("On" if led_enabled else "Off")
        self.led_brightness_input.setValue(led_brightness)
        self.steps_per_mm_input.setValue(steps_per_mm)
        self.microstepping_input.setValue(microstepping)
        self.speed_input.setValue(speed)
        self.acceleration_input.setValue(acceleration)
