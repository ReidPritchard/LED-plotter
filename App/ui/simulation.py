"""Simulation of the machine's state and future behavior."""

import math
from typing import List, Tuple

from PyQt6 import QtWidgets
from PyQt6.QtCore import QPointF, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QCheckBox, QSlider

from models import MachineConfig, PlotterState


class SimulationCanvas(QtWidgets.QWidget):
    """Custom widget for rendering the plotter simulation."""

    def __init__(self, machine_config: MachineConfig, parent=None):
        super().__init__(parent)
        self.machine_config = machine_config
        self.setMinimumSize(400, 300)

        # AIDEV-NOTE: Simulated position separate from hardware state
        self.sim_x = machine_config.width / 2.0
        self.sim_y = machine_config.height / 2.0

        # Path trail for visualization
        self.path_trail: List[Tuple[float, float]] = []
        self.show_trail = True
        self.show_safe_area = True

    def set_position(self, x: float, y: float):
        """Update the simulated gondola position."""
        self.sim_x = x
        self.sim_y = y
        self.update()  # Trigger repaint

    def add_to_trail(self, x: float, y: float):
        """Add a point to the path trail."""
        self.path_trail.append((x, y))
        if len(self.path_trail) > 1000:  # Limit trail length
            self.path_trail.pop(0)

    def clear_trail(self):
        """Clear the path trail."""
        self.path_trail.clear()
        self.update()

    def _world_to_screen(self, x: float, y: float) -> Tuple[float, float]:
        """
        Convert world coordinates (mm) to screen coordinates (pixels).

        AIDEV-NOTE: Maintains aspect ratio and adds padding for visualization
        """
        padding = 40  # pixels
        available_width = self.width() - 2 * padding
        available_height = self.height() - 2 * padding

        # Scale to fit while maintaining aspect ratio
        scale_x = available_width / self.machine_config.width
        scale_y = available_height / self.machine_config.height
        scale = min(scale_x, scale_y)

        # Center the drawing
        offset_x = (self.width() - self.machine_config.width * scale) / 2
        offset_y = padding

        screen_x = offset_x + x * scale
        screen_y = offset_y + y * scale

        return screen_x, screen_y

    def _calculate_cable_lengths(
        self, x: float, y: float
    ) -> Tuple[float, float]:
        """
        Calculate cable lengths for a given XY position.

        AIDEV-NOTE: Inverse kinematics using Pythagorean theorem
        Left motor at (0, 0), right motor at (width, 0)
        """
        left_cable = math.sqrt(x**2 + y**2)
        right_cable = math.sqrt((self.machine_config.width - x) ** 2 + y**2)
        return left_cable, right_cable

    def paintEvent(self, event):
        """Render the simulation visualization."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor(20, 20, 20))

        # Draw machine frame (top bar where motors are mounted)
        left_motor = self._world_to_screen(0, 0)
        right_motor = self._world_to_screen(self.machine_config.width, 0)

        painter.setPen(QPen(QColor(60, 60, 60), 4))
        painter.drawLine(
            int(left_motor[0]),
            int(left_motor[1]),
            int(right_motor[0]),
            int(right_motor[1]),
        )

        # Draw motors (circles at top corners)
        motor_radius = 8
        painter.setBrush(QBrush(QColor(40, 40, 40)))
        painter.drawEllipse(
            int(left_motor[0] - motor_radius),
            int(left_motor[1] - motor_radius),
            motor_radius * 2,
            motor_radius * 2,
        )
        painter.drawEllipse(
            int(right_motor[0] - motor_radius),
            int(right_motor[1] - motor_radius),
            motor_radius * 2,
            motor_radius * 2,
        )

        # Draw safe area boundary
        if self.show_safe_area:
            margin = self.machine_config.safe_margin
            tl = self._world_to_screen(margin, margin)
            br = self._world_to_screen(
                self.machine_config.width - margin,
                self.machine_config.height - margin,
            )
            painter.setPen(
                QPen(QColor(100, 200, 100), 2, Qt.PenStyle.DashLine)
            )
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(
                int(tl[0]), int(tl[1]), int(br[0] - tl[0]), int(br[1] - tl[1])
            )

        # Draw work area boundary
        tl_work = self._world_to_screen(0, 0)
        br_work = self._world_to_screen(
            self.machine_config.width, self.machine_config.height
        )
        painter.setPen(QPen(QColor(150, 150, 150), 1))
        painter.drawRect(
            int(tl_work[0]),
            int(tl_work[1]),
            int(br_work[0] - tl_work[0]),
            int(br_work[1] - tl_work[1]),
        )

        # Draw cables from motors to gondola
        gondola_pos = self._world_to_screen(self.sim_x, self.sim_y)
        painter.setPen(QPen(QColor(200, 100, 100), 2))
        painter.drawLine(
            int(left_motor[0]),
            int(left_motor[1]),
            int(gondola_pos[0]),
            int(gondola_pos[1]),
        )
        painter.setPen(QPen(QColor(100, 100, 200), 2))
        painter.drawLine(
            int(right_motor[0]),
            int(right_motor[1]),
            int(gondola_pos[0]),
            int(gondola_pos[1]),
        )

        # Draw path trail
        if self.show_trail and len(self.path_trail) > 1:
            path = QPainterPath()
            first_point = self._world_to_screen(
                self.path_trail[0][0], self.path_trail[0][1]
            )
            path.moveTo(QPointF(first_point[0], first_point[1]))

            for i in range(1, len(self.path_trail)):
                screen_pos = self._world_to_screen(
                    self.path_trail[i][0], self.path_trail[i][1]
                )
                path.lineTo(QPointF(screen_pos[0], screen_pos[1]))

            painter.setPen(QPen(QColor(0, 150, 0), 1.5))
            painter.drawPath(path)

        # Draw gondola/pen holder
        gondola_radius = 6
        painter.setBrush(QBrush(QColor(255, 100, 0)))
        painter.setPen(QPen(QColor(200, 80, 0), 2))
        painter.drawEllipse(
            int(gondola_pos[0] - gondola_radius),
            int(gondola_pos[1] - gondola_radius),
            gondola_radius * 2,
            gondola_radius * 2,
        )

        # Draw cable lengths as text
        left_cable, right_cable = self._calculate_cable_lengths(
            self.sim_x, self.sim_y
        )
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.drawText(
            10, 20, f"Sim Position: ({self.sim_x:.1f}, {self.sim_y:.1f}) mm"
        )
        painter.drawText(10, 40, f"Left Cable: {left_cable:.1f} mm")
        painter.drawText(10, 60, f"Right Cable: {right_cable:.1f} mm")


class SimulationUI(QtWidgets.QWidget):
    """UI for simulating the machine's state and future behavior."""

    def __init__(
        self, machine_config: MachineConfig, plotter_state: PlotterState
    ):
        super().__init__()
        self.machine_config = machine_config
        self.plotter_state = plotter_state

        # Simulation state
        self.is_running = False
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._animation_step)

        # Animation parameters
        self.target_x = machine_config.width / 2.0
        self.target_y = machine_config.height / 2.0
        self.animation_speed = 100.0  # mm/s
        self.last_update_ms = 0

        self.init_ui()

    def init_ui(self):
        """Initialize the UI components."""
        # Main layout
        main_layout = QtWidgets.QVBoxLayout()

        # Canvas
        self.canvas = SimulationCanvas(self.machine_config)
        main_layout.addWidget(self.canvas)

        # Control panel
        control_layout = QtWidgets.QHBoxLayout()

        # Playback controls
        self.start_button = QtWidgets.QPushButton("▶ Play")
        self.stop_button = QtWidgets.QPushButton("⏸ Pause")
        self.reset_button = QtWidgets.QPushButton("↻ Reset")
        self.clear_trail_button = QtWidgets.QPushButton("Clear Trail")

        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addWidget(self.reset_button)
        control_layout.addWidget(self.clear_trail_button)

        # Visualization options
        self.trail_checkbox = QCheckBox("Show Trail")
        self.trail_checkbox.setChecked(True)
        self.safe_area_checkbox = QCheckBox("Show Safe Area")
        self.safe_area_checkbox.setChecked(True)

        control_layout.addWidget(self.trail_checkbox)
        control_layout.addWidget(self.safe_area_checkbox)

        control_layout.addStretch()

        main_layout.addLayout(control_layout)

        # Speed control
        speed_layout = QtWidgets.QHBoxLayout()
        speed_layout.addWidget(QtWidgets.QLabel("Speed:"))
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setMinimum(10)
        self.speed_slider.setMaximum(500)
        self.speed_slider.setValue(100)
        self.speed_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.speed_slider.setTickInterval(50)
        speed_layout.addWidget(self.speed_slider)
        self.speed_label = QtWidgets.QLabel("100 mm/s")
        speed_layout.addWidget(self.speed_label)

        main_layout.addLayout(speed_layout)

        # Test movement controls
        test_layout = QtWidgets.QHBoxLayout()
        test_layout.addWidget(QtWidgets.QLabel("Quick Test Moves:"))
        self.home_sim_button = QtWidgets.QPushButton("Home (Center)")
        self.tl_corner_button = QtWidgets.QPushButton("Top Left")
        self.tr_corner_button = QtWidgets.QPushButton("Top Right")
        self.bl_corner_button = QtWidgets.QPushButton("Bottom Left")
        self.br_corner_button = QtWidgets.QPushButton("Bottom Right")

        test_layout.addWidget(self.home_sim_button)
        test_layout.addWidget(self.tl_corner_button)
        test_layout.addWidget(self.tr_corner_button)
        test_layout.addWidget(self.bl_corner_button)
        test_layout.addWidget(self.br_corner_button)
        test_layout.addStretch()

        main_layout.addLayout(test_layout)

        self.setLayout(main_layout)

        # Connect signals
        self.start_button.clicked.connect(self.start_simulation)
        self.stop_button.clicked.connect(self.stop_simulation)
        self.reset_button.clicked.connect(self.reset_simulation)
        self.clear_trail_button.clicked.connect(self.canvas.clear_trail)

        self.trail_checkbox.stateChanged.connect(self._toggle_trail)
        self.safe_area_checkbox.stateChanged.connect(self._toggle_safe_area)

        self.speed_slider.valueChanged.connect(self._update_speed)

        # Test movement buttons
        self.home_sim_button.clicked.connect(self._move_to_home)
        self.tl_corner_button.clicked.connect(self._move_to_tl)
        self.tr_corner_button.clicked.connect(self._move_to_tr)
        self.bl_corner_button.clicked.connect(self._move_to_bl)
        self.br_corner_button.clicked.connect(self._move_to_br)

    def start_simulation(self):
        """Start the simulation animation."""
        if not self.is_running:
            self.is_running = True
            self.last_update_ms = 0
            self.animation_timer.start(50)  # 20 FPS
            self.start_button.setText("▶ Running...")
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)

    def stop_simulation(self):
        """Stop the simulation animation."""
        if self.is_running:
            self.is_running = False
            self.animation_timer.stop()
            self.start_button.setText("▶ Play")
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)

    def reset_simulation(self):
        """Reset the simulation to home position."""
        self.stop_simulation()
        self.target_x = self.machine_config.width / 2.0
        self.target_y = self.machine_config.height / 2.0
        self.canvas.set_position(self.target_x, self.target_y)
        self.canvas.clear_trail()

    def _update_speed(self, value: int):
        """Update animation speed from slider."""
        self.animation_speed = float(value)
        self.speed_label.setText(f"{value} mm/s")

    def _toggle_trail(self, state: int):
        """Toggle path trail visibility."""
        self.canvas.show_trail = state == Qt.CheckState.Checked.value
        self.canvas.update()

    def _toggle_safe_area(self, state: int):
        """Toggle safe area boundary visibility."""
        self.canvas.show_safe_area = state == Qt.CheckState.Checked.value
        self.canvas.update()

    def _animation_step(self):
        """
        Execute one animation frame.

        AIDEV-NOTE: Smoothly interpolate position toward target at specified speed
        """
        dt = 0.05  # 50ms timer = 0.05s per frame

        current_x = self.canvas.sim_x
        current_y = self.canvas.sim_y

        # Calculate direction to target
        dx = self.target_x - current_x
        dy = self.target_y - current_y
        distance = math.sqrt(dx**2 + dy**2)

        if distance < 0.1:  # Close enough to target
            self.canvas.set_position(self.target_x, self.target_y)
            return

        # Move toward target at specified speed
        max_step = self.animation_speed * dt
        if distance > max_step:
            # Normalize direction and scale by step size
            step_x = (dx / distance) * max_step
            step_y = (dy / distance) * max_step
            new_x = current_x + step_x
            new_y = current_y + step_y
        else:
            # Close enough, just snap to target
            new_x = self.target_x
            new_y = self.target_y

        self.canvas.set_position(new_x, new_y)
        self.canvas.add_to_trail(new_x, new_y)

    def move_to(self, x: float, y: float):
        """
        Command the simulation to move to a target position.

        Public method for external control (e.g., from command panel).
        """
        # AIDEV-NOTE: Constrain to safe area
        margin = self.machine_config.safe_margin
        x = max(margin, min(x, self.machine_config.width - margin))
        y = max(margin, min(y, self.machine_config.height - margin))

        self.target_x = x
        self.target_y = y

        if not self.is_running:
            # If not animating, just jump to position
            self.canvas.set_position(x, y)
            self.canvas.add_to_trail(x, y)

    # === Test Movement Methods ===

    def _move_to_home(self):
        """Move simulation to home (center) position."""
        self.move_to(
            self.machine_config.width / 2.0, self.machine_config.height / 2.0
        )

    def _move_to_tl(self):
        """Move to top-left corner (within safe margin)."""
        margin = self.machine_config.safe_margin
        self.move_to(margin, margin)

    def _move_to_tr(self):
        """Move to top-right corner (within safe margin)."""
        margin = self.machine_config.safe_margin
        self.move_to(self.machine_config.width - margin, margin)

    def _move_to_bl(self):
        """Move to bottom-left corner (within safe margin)."""
        margin = self.machine_config.safe_margin
        self.move_to(margin, self.machine_config.height - margin)

    def _move_to_br(self):
        """Move to bottom-right corner (within safe margin)."""
        margin = self.machine_config.safe_margin
        self.move_to(
            self.machine_config.width - margin,
            self.machine_config.height - margin,
        )

    def update_from_hardware_state(self, plotter_state: PlotterState):
        """
        Update simulation to match actual hardware position.

        Call this when receiving position updates from Arduino.
        """
        self.plotter_state = plotter_state
        # Update canvas to show hardware position
        self.canvas.set_position(
            plotter_state.position_x, plotter_state.position_y
        )
