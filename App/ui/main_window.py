"""Main application window for plotter control."""

import json
from dataclasses import asdict
from typing import Optional

import serial.tools.list_ports  # Import for port listing
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from models import CONFIG_FILE, ConnectionState, MachineConfig, PlotterState
from serial_handler import SERIAL_AVAILABLE, SerialThread
from ui.command_panel import CommandPanel
from ui.console_panel import ConsolePanel
from ui.queue_panel import QueuePanel
from ui.settings_dialog import SettingsDialog
from ui.simulation import SimulationUI
from ui.state_panel import StatePanel


class PlotterControlWindow(QMainWindow):
    """Main application window for plotter control."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PolarPlot Controller v0.1.0")
        self.setMinimumSize(1000, 800)

        # Application state
        self.machine_config = MachineConfig()
        self._load_config()  # Load saved config if available
        self.plotter_state = PlotterState()
        self.serial_thread: Optional[SerialThread] = None
        self.command_queue = []  # Display queue

        self._setup_ui()
        self._connect_signals()
        self._update_connection_state()

    def _setup_ui(self):
        """Initialize the user interface."""
        self._create_toolbar()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Middle: Splitter with state display and command queue
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.state_panel = StatePanel(self.plotter_state, self.machine_config)
        self.queue_panel = QueuePanel()
        splitter.addWidget(self.state_panel)
        splitter.addWidget(self.queue_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setVisible(False)
        main_layout.addWidget(splitter)

        # Top: Simulation panel (hidden by default)
        self.simulation_ui = SimulationUI(
            self.machine_config, self.plotter_state
        )
        self.simulation_ui.setVisible(True)
        main_layout.addWidget(self.simulation_ui)

        # Bottom: Command controls
        self.command_panel = CommandPanel(self.machine_config)
        main_layout.addWidget(self.command_panel)

        # Console output
        self.console_panel = ConsolePanel()
        main_layout.addWidget(self.console_panel)

    def _create_toolbar(self):
        """Create the main toolbar with connection controls and settings."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Settings action
        settings_action = QAction("⚙️ Settings", self)
        settings_action.setToolTip("Open machine configuration settings")
        settings_action.triggered.connect(self._open_settings_dialog)
        toolbar.addAction(settings_action)

        toolbar.addSeparator()

        # Port selection label
        toolbar.addWidget(QLabel("Port:"))

        # Port combo box
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(250)
        self._refresh_ports()
        toolbar.addWidget(self.port_combo)

        # Refresh ports button
        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setToolTip("Refresh serial ports")
        self.refresh_btn.setMaximumWidth(40)
        self.refresh_btn.clicked.connect(self._refresh_ports)
        toolbar.addWidget(self.refresh_btn)

        # Connect/Disconnect button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setMinimumWidth(100)
        self.connect_btn.clicked.connect(self._toggle_connection)
        toolbar.addWidget(self.connect_btn)

        # Connection status indicator
        self.status_label = QLabel("●")
        self.status_label.setFont(QFont("Arial", 16))
        self.status_label.setStyleSheet("color: gray;")
        self.status_label.setToolTip("Connection status")
        toolbar.addWidget(self.status_label)

    def _connect_signals(self):
        """Connect all UI signals to handlers."""

        # State panel
        self.state_panel.status_btn.clicked.connect(
            lambda: self._send_command("?")
        )

        # Queue panel
        self.queue_panel.clear_btn.clicked.connect(self._clear_queue)
        self.queue_panel.send_next_btn.clicked.connect(
            self._send_next_in_queue
        )
        self.queue_panel.send_all_btn.clicked.connect(self._send_all_in_queue)

        # Command panel
        self.command_panel.home_btn.clicked.connect(
            lambda: self._queue_command("H")
        )
        self.command_panel.test_btn.clicked.connect(
            lambda: self._queue_command("T")
        )
        self.command_panel.calibrate_btn.clicked.connect(
            lambda: self._queue_command("C")
        )
        self.command_panel.queue_move_btn.clicked.connect(
            self._queue_move_command
        )
        self.command_panel.move_now_btn.clicked.connect(
            self._send_move_command
        )
        self.command_panel.custom_input.returnPressed.connect(
            self._send_custom_command
        )
        self.command_panel.send_custom_btn.clicked.connect(
            self._send_custom_command
        )

    # === Settings Dialog ===

    def _open_settings_dialog(self):
        """Open the settings dialog for machine configuration."""
        dialog = SettingsDialog(self.machine_config, self)

        # Pre-populate with current values
        dialog.set_values(
            self.machine_config.width,
            self.machine_config.height,
            self.machine_config.safe_margin,
            self.machine_config.led_enabled,
            self.machine_config.led_brightness,
            self.machine_config.steps_per_mm,
            self.machine_config.microstepping,
            self.machine_config.speed,
            self.machine_config.acceleration,
        )

        # Show dialog and handle result
        if dialog.exec():  # User clicked OK
            # AIDEV-NOTE: Warn if connected - changing dimensions while connected could be dangerous
            if self.serial_thread and self.serial_thread.isRunning():
                reply = QMessageBox.question(
                    self,
                    "Apply While Connected?",
                    "You are currently connected to the plotter.\n\n"
                    "Changing machine dimensions while connected may cause "
                    "unexpected behavior or damage.\n\n"
                    "Are you sure you want to apply these settings?",
                    QMessageBox.StandardButton.Yes
                    | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.No:
                    return

            # Apply the new configuration
            self.machine_config = dialog.get_values()

            # Update UI elements that depend on these values
            self.state_panel.update_config_display(self.machine_config)
            self.command_panel.update_move_bounds(self.machine_config)

            # Save to file for persistence
            self._save_config()

            self.console_panel.append(
                f"✓ Configuration applied: {self.machine_config.width:.0f}×"
                f"{self.machine_config.height:.0f}mm, margin={self.machine_config.safe_margin:.0f}mm"
            )

    def _refresh_ports(self):
        """Refresh the list of available serial ports."""
        self.port_combo.clear()

        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo.addItem(
                f"{port.device} - {port.description}", port.device
            )
        if not ports:
            self.port_combo.addItem("No ports found", None)

    # === Connection Management ===

    def _toggle_connection(self):
        """Connect or disconnect from serial port."""
        if self.serial_thread and self.serial_thread.isRunning():
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        """Establish serial connection."""
        if not SERIAL_AVAILABLE:
            QMessageBox.warning(
                self,
                "Missing Dependency",
                "pyserial is not installed.\n\nInstall with: pixi add pyserial",
            )
            return

        port = self.port_combo.currentData()
        if not port:
            QMessageBox.warning(
                self, "No Port Selected", "Please select a valid serial port."
            )
            return

        self.plotter_state.connection = ConnectionState.CONNECTING
        self._update_connection_state()

        self.serial_thread = SerialThread(port)
        self.serial_thread.response_received.connect(self._handle_response)
        self.serial_thread.connection_changed.connect(
            self._handle_connection_change
        )
        self.serial_thread.error_occurred.connect(self._handle_error)
        self.serial_thread.start()

        self.console_panel.append(f"Connecting to {port}...")

    def _disconnect(self):
        """Close serial connection."""
        if self.serial_thread:
            self.serial_thread.stop()
            self.serial_thread.wait(2000)  # Wait up to 2 seconds
            self.serial_thread = None

        self.plotter_state.connection = ConnectionState.DISCONNECTED
        self._update_connection_state()
        self.console_panel.append("Disconnected.")

    def _handle_connection_change(self, state: ConnectionState):
        """Handle connection state changes from serial thread."""
        self.plotter_state.connection = state
        self._update_connection_state()

        if state == ConnectionState.CONNECTED:
            self.console_panel.append(
                "✓ Connected! Requesting initial status..."
            )
            # Request initial status
            QTimer.singleShot(1000, lambda: self._send_command("?"))

    def _update_connection_state(self):
        """Update UI based on connection state."""
        state = self.plotter_state.connection

        # AIDEV-NOTE: Update toolbar connection controls based on state
        if state == ConnectionState.CONNECTED:
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setEnabled(True)
            self.status_label.setText("●")
            self.status_label.setStyleSheet("color: green;")
            self.status_label.setToolTip("Connected")
        elif state == ConnectionState.CONNECTING:
            self.connect_btn.setText("Connecting...")
            self.connect_btn.setEnabled(False)
            self.status_label.setText("●")
            self.status_label.setStyleSheet("color: orange;")
            self.status_label.setToolTip("Connecting...")
        elif state == ConnectionState.ERROR:
            self.connect_btn.setText("Connect")
            self.connect_btn.setEnabled(True)
            self.status_label.setText("●")
            self.status_label.setStyleSheet("color: red;")
            self.status_label.setToolTip("Connection Error")
        else:  # DISCONNECTED
            self.connect_btn.setText("Connect")
            self.connect_btn.setEnabled(True)
            self.status_label.setText("●")
            self.status_label.setStyleSheet("color: gray;")
            self.status_label.setToolTip("Disconnected")

    # === Command Management ===

    def _queue_command(self, command: str):
        """Add command to the display queue."""
        self.command_queue.append(command)
        self.queue_panel.add_command(command)
        self.console_panel.append(f"Queued: {command}")

    def _queue_move_command(self):
        """Queue a move command with current input values."""
        x, y = self.command_panel.get_move_coordinates()
        command = f"M {x:.1f} {y:.1f}"
        self._queue_command(command)

    def _send_move_command(self):
        """Send move command immediately."""
        x, y = self.command_panel.get_move_coordinates()
        command = f"M {x:.1f} {y:.1f}"
        self._send_command(command)

    def _send_custom_command(self):
        """Send custom command from input field."""
        command = self.command_panel.get_custom_command()
        if command:
            self._send_command(command)
            self.command_panel.clear_custom_command()

    def _send_command(self, command: str):
        """Send command to Arduino immediately."""
        if not self.serial_thread or not self.serial_thread.isRunning():
            QMessageBox.warning(
                self, "Not Connected", "Please connect to a serial port first."
            )
            return

        self.serial_thread.send_command(command)
        self.console_panel.append(f"→ Sent: {command}")

    def _send_next_in_queue(self):
        """Send the next command in the queue."""
        if not self.command_queue:
            return

        command = self.command_queue.pop(0)
        self.queue_panel.remove_first()
        self._send_command(command)

    def _send_all_in_queue(self):
        """Send all queued commands."""
        while self.command_queue:
            self._send_next_in_queue()

    def _clear_queue(self):
        """Clear all queued commands."""
        self.command_queue.clear()
        self.queue_panel.clear()
        self.console_panel.append("Queue cleared.")

    # === Response Handling ===

    def _handle_response(self, response: str):
        """Handle responses from Arduino."""
        self.console_panel.append(f"← {response}")

        # AIDEV-NOTE: Parse status responses to update state display
        # Example: "Position: (400.0, 300.0)"
        if "Position:" in response:
            try:
                # Parse position from "Position: (x, y)" format
                pos_str = response.split("Position:")[1].strip()
                pos_str = pos_str.strip("()")
                x, y = pos_str.split(",")
                self.plotter_state.position_x = float(x.strip())
                self.plotter_state.position_y = float(y.strip())
                self.state_panel.update_state(self.plotter_state)
            except (ValueError, IndexError):
                pass  # Ignore parse errors

        # Parse cable lengths: "Cable lengths: L=xxx R=xxx"
        if "Cable lengths:" in response:
            try:
                parts = response.split("Cable lengths:")[1].strip().split()
                for part in parts:
                    if part.startswith("L="):
                        self.plotter_state.left_cable = float(part[2:])
                    elif part.startswith("R="):
                        self.plotter_state.right_cable = float(part[2:])
                self.state_panel.update_state(self.plotter_state)
            except (ValueError, IndexError):
                pass

        # Parse STEPS_PER_MM
        if "STEPS_PER_MM:" in response:
            try:
                value = response.split("STEPS_PER_MM:")[1].strip()
                self.plotter_state.steps_per_mm = float(value)
                self.state_panel.update_state(self.plotter_state)
            except (ValueError, IndexError):
                pass

    def _handle_error(self, error: str):
        """Handle errors from serial thread."""
        self.console_panel.append(f"❌ Error: {error}")
        QMessageBox.critical(self, "Serial Error", error)

    # === Configuration Management ===

    def _load_config(self):
        """Load machine configuration from file."""
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    self.machine_config.width = data.get("width", 800.0)
                    self.machine_config.height = data.get("height", 600.0)
                    self.machine_config.safe_margin = data.get(
                        "safe_margin", 50.0
                    )
                print(f"✓ Loaded configuration from {CONFIG_FILE}")
        except Exception as e:
            print(f"Warning: Could not load config file: {e}")

    def _save_config(self):
        """Save machine configuration to file."""
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(asdict(self.machine_config), f, indent=2)
            self.console_panel.append(
                f"✓ Configuration saved to {CONFIG_FILE}"
            )
        except Exception as e:
            self.console_panel.append(f"❌ Error saving config: {e}")
            QMessageBox.warning(
                self, "Save Error", f"Could not save configuration:\n{e}"
            )

    # === Application Lifecycle ===

    def closeEvent(self, event):
        """Clean up when window closes."""
        self._disconnect()
        event.accept()
