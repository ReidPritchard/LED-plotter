"""Main application window for plotter control."""

import os
from typing import Optional

import serial.tools.list_ports  # Import for port listing
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QComboBox,
    QDockWidget,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QToolBar,
    QWidget,
)

from config_manager import ConfigManager
from models import (
    ConnectionState,
    PlotterState,
    ProcessedImage,
)
from serial_handler import SerialThread
from ui.command_panel import CommandPanel
from ui.console_panel import ConsolePanel
from ui.image_panel import ImagePanel
from ui.queue_panel import QueuePanel
from ui.settings_dialog import SettingsDialog
from ui.simulation import SimulationUI
from ui.state_panel import StatePanel
from ui.styles import FONTS, StatusColors
from ui.workflow import CentralWorkflowWidget, WorkflowStep


class PlotterControlWindow(QMainWindow):
    """Main application window for plotter control."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PolarPlot Controller v0.1.0")
        self.setMinimumSize(1000, 800)

        self.setWindowIcon(QIcon(os.path.join("assets", "app_icon.icns")))

        # Application state
        self.config_manager = ConfigManager()
        self.machine_config = self.config_manager.load()
        self.plotter_state = PlotterState()
        self.serial_thread: Optional[SerialThread] = None

        # UI component references (created in _setup_ui) - type hints for static analysis
        self.state_panel: StatePanel
        self.console_panel: ConsolePanel
        self.state_dock: QDockWidget
        self.console_dock: QDockWidget
        self.queue_panel: QueuePanel
        self.command_panel: CommandPanel
        self.image_panel: ImagePanel
        self.simulation_ui: SimulationUI

        self._setup_ui()
        self._connect_signals()
        self._update_connection_state()

    def _setup_ui(self):
        """Initialize the user interface."""
        self._create_menu_bar()
        self._create_toolbar()

        # AIDEV-NOTE: Central workflow widget replaces the old dock-based UI
        # for the main workflow (Image, Preview, Connect, Send)
        self._create_central_workflow()
        self._create_dock_widgets()

    def _create_menu_bar(self):
        """Create the menu bar with View menu for panel toggles."""
        menubar = self.menuBar()

        if menubar is None:
            return

        # View menu
        menubar.addMenu("&View")

        # These actions will be created after dock widgets are set up
        self.view_actions = {}

    def _create_central_workflow(self):
        """Create the central workflow widget."""
        self.central_workflow = CentralWorkflowWidget(
            self.machine_config,
            self.plotter_state,
        )
        self.setCentralWidget(self.central_workflow)

        # Get references to embedded panels for convenience
        self.queue_panel = self.central_workflow.get_queue_panel()
        self.command_panel = self.central_workflow.get_command_panel()
        self.image_panel = self.central_workflow.get_image_panel()
        self.simulation_ui = self.central_workflow.get_simulation_ui()

    def _create_dock_widgets(self):
        """Create State and Console panels as dockable widgets."""

        # Only State and Console remain as docks
        dock_panels = [
            (
                "state_panel",
                "State",
                StatePanel(self.plotter_state, self.machine_config),
                Qt.DockWidgetArea.RightDockWidgetArea,
            ),
            (
                "console_panel",
                "Console",
                ConsolePanel(),
                Qt.DockWidgetArea.BottomDockWidgetArea,
            ),
        ]

        self.docks = []
        for attr, name, panel, area in dock_panels:
            setattr(self, attr, panel)
            dock = self._create_dock_widget(name, panel, area)
            setattr(self, f"{attr.split('_')[0]}_dock", dock)
            self.docks.append(dock)

        # Add View menu actions for docks
        self._add_view_menu_actions()
        self._add_toolbar_toggles()

    def _create_dock_widget(
        self, title: str, widget: QWidget, area: Qt.DockWidgetArea
    ) -> QDockWidget:
        """Create a dockable widget with standard settings.

        Args:
            title: Window title for the dock widget
            widget: The widget to place inside the dock
            area: Default dock area (Left, Right, Top, Bottom)

        Returns:
            The created QDockWidget
        """
        dock = QDockWidget(title, self)
        dock.setWidget(widget)
        dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
            | Qt.DockWidgetArea.TopDockWidgetArea
            | Qt.DockWidgetArea.BottomDockWidgetArea
        )
        self.addDockWidget(area, dock)
        return dock

    def _add_view_menu_actions(self):
        """Add toggle actions for dock widgets to the View menu."""
        menubar = self.menuBar()
        if menubar is None:
            return
        view_menu = menubar.actions()[0].menu()  # Get the View menu
        if view_menu is None:
            return

        # Dock widget toggles
        dock_widgets = [
            ("State", self.state_dock),
            ("Console", self.console_dock),
        ]

        for name, dock in dock_widgets:
            action = dock.toggleViewAction()
            if not action:
                continue
            action.setText(f"Show {name}")
            view_menu.addAction(action)
            self.view_actions[name] = action

        view_menu.addSeparator()

        # Workflow step shortcuts
        step_actions = [
            ("Go to Dashboard", WorkflowStep.DASHBOARD),
            ("Go to Import", WorkflowStep.IMPORT),
            ("Go to Preview", WorkflowStep.PREVIEW),
            ("Go to Connect", WorkflowStep.CONNECT),
            ("Go to Send", WorkflowStep.SEND),
        ]

        for name, step in step_actions:
            action = QAction(name, self)
            action.triggered.connect(lambda _, s=step: self.central_workflow.set_current_step(s))
            view_menu.addAction(action)
            self.view_actions[name] = action

    def _add_toolbar_toggles(self):
        """Add toggle buttons to toolbar for dock widgets."""
        # Get the main toolbar
        toolbar = self.findChild(QToolBar, "Main Toolbar")
        if not toolbar:
            return

        # Add label for panel toggles
        toolbar.addWidget(QLabel("Panels:"))

        # Emoji/icon mapping for each dock panel
        panel_icons = {
            "State": "📍",
            "Console": "💬",
        }

        # Create toggle buttons for dock widgets
        dock_widgets = [
            ("State", self.state_dock),
            ("Console", self.console_dock),
        ]

        for name, dock in dock_widgets:
            # Use the dock widget's built-in toggle action
            action = dock.toggleViewAction()
            if not action:
                continue

            # Create a toolbar button from the action
            btn = QPushButton(panel_icons.get(name, "◻"))
            btn.setToolTip(f"Toggle {name} panel")
            btn.setCheckable(True)
            btn.setChecked(dock.isVisible())
            btn.setMaximumWidth(35)

            # Connect button to dock visibility
            btn.clicked.connect(action.trigger)
            dock.visibilityChanged.connect(btn.setChecked)

            toolbar.addWidget(btn)

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

        # Connection status indicator (minimal in toolbar, full UI in Connect page)
        toolbar.addWidget(QLabel("Status:"))
        self.status_label = QLabel("●")
        self.status_label.setFont(FONTS.STATUS_INDICATOR)
        self.status_label.setStyleSheet(f"color: {StatusColors.DISCONNECTED};")
        self.status_label.setToolTip("Connection status")
        toolbar.addWidget(self.status_label)

        # Quick connect button (for convenience)
        self.quick_connect_btn = QPushButton("🔌")
        self.quick_connect_btn.setToolTip("Go to Connect page")
        self.quick_connect_btn.setMaximumWidth(35)
        self.quick_connect_btn.clicked.connect(
            lambda: self.central_workflow.set_current_step(WorkflowStep.CONNECT)
        )
        toolbar.addWidget(self.quick_connect_btn)

        toolbar.addSeparator()

        # We keep port combo for quick connection from toolbar too
        toolbar.addWidget(QLabel("Port:"))
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(200)
        self._refresh_ports()
        toolbar.addWidget(self.port_combo)

        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setToolTip("Refresh serial ports")
        self.refresh_btn.setMaximumWidth(35)
        self.refresh_btn.clicked.connect(self._refresh_ports)
        toolbar.addWidget(self.refresh_btn)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setMinimumWidth(80)
        self.connect_btn.clicked.connect(self._toggle_connection)
        toolbar.addWidget(self.connect_btn)

        toolbar.addSeparator()

        # Panel toggle buttons will be added after dock widgets are created

    def _connect_signals(self):
        """Connect all UI signals to handlers."""

        # State panel
        self.state_panel.status_btn.clicked.connect(lambda: self._send_command("?"))

        # Central workflow signals
        self.central_workflow.step_changed.connect(self._on_workflow_step_changed)
        self.central_workflow.processing_complete.connect(self._on_image_processed)
        self.central_workflow.preview_requested.connect(self._on_preview_requested)
        self.central_workflow.add_to_queue_requested.connect(self._queue_image_commands)
        self.central_workflow.connect_requested.connect(self._connect_to_port)
        self.central_workflow.disconnect_requested.connect(self._disconnect)
        self.central_workflow.home_requested.connect(lambda: self._send_command("H"))

        # Queue panel (via central workflow)
        self.queue_panel.clear_btn.clicked.connect(self._clear_queue)
        self.queue_panel.send_next_btn.clicked.connect(self._send_next_in_queue)
        self.queue_panel.send_all_btn.clicked.connect(self._send_all_in_queue)

        # Command panel (via central workflow)
        self.command_panel.home_btn.clicked.connect(lambda: self._queue_command("H"))
        self.command_panel.test_btn.clicked.connect(
            lambda:
            # AIDEV-NOTE: Queue commands to draw a colorful test
            # square with LED interpolation. Each edge transitions to
            # a different color for visual feedback
            self._queue_command_multiple(
                [
                    "H",  # Home
                    "M 200 200 255 0 0",  # Move to start, fade to red
                    "M 400 200 0 255 0",  # Bottom edge, fade to green
                    "M 400 400 0 0 255",  # Right edge, fade to blue
                    "M 200 400 255 255 0",  # Top edge, fade to yellow
                    "M 200 200 255 0 255",  # Left edge, fade to magenta
                ]
            )
        )
        self.command_panel.calibrate_btn.clicked.connect(lambda: self._queue_command("C"))
        self.command_panel.queue_move_btn.clicked.connect(self._queue_move_command)
        self.command_panel.move_now_btn.clicked.connect(self._send_move_command)
        self.command_panel.custom_input.returnPressed.connect(self._send_custom_command)
        self.command_panel.send_custom_btn.clicked.connect(self._send_custom_command)

    def _on_workflow_step_changed(self, step: int):
        """Handle workflow step changes."""
        step_name = WorkflowStep(step).label
        self.console_panel.append(f"📍 Navigated to: {step_name}")

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
            # AIDEV-NOTE: Warn if connected - changing dimensions
            # while connected could be dangerous
            if self.serial_thread and self.serial_thread.isRunning():
                reply = QMessageBox.question(
                    self,
                    "Apply While Connected?",
                    "You are currently connected to the plotter.\n\n"
                    "Changing machine dimensions while connected may cause "
                    "unexpected behavior or damage.\n\n"
                    "Are you sure you want to apply these settings?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
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
            success, error = self.config_manager.save(self.machine_config)
            if not success:
                self.console_panel.append(f"❌ Error saving config: {error}")
                QMessageBox.warning(
                    self,
                    "Save Error",
                    f"Could not save configuration:\n{error}",
                )
            else:
                self.console_panel.append("✓ Configuration saved")

            self.console_panel.append(
                f"✓ Configuration applied: "
                f"{self.machine_config.width:.0f}×"
                f"{self.machine_config.height:.0f}mm, "
                f"margin={self.machine_config.safe_margin:.0f}mm"
            )

    def _refresh_ports(self):
        """Refresh the list of available serial ports."""
        self.port_combo.clear()

        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo.addItem(f"{port.device} - {port.description}", port.device)
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
        """Establish serial connection using port from toolbar."""
        port = self.port_combo.currentData()
        if not port:
            QMessageBox.warning(self, "No Port Selected", "Please select a valid serial port.")
            return
        self._connect_to_port(port)

    def _connect_to_port(self, port: str):
        """Establish serial connection to specified port."""
        if not port:
            QMessageBox.warning(self, "No Port Selected", "Please select a valid serial port.")
            return

        self.plotter_state.connection = ConnectionState.CONNECTING
        self._update_connection_state()

        self.serial_thread = SerialThread(port)
        self.serial_thread.response_received.connect(self._handle_response)
        self.serial_thread.connection_changed.connect(self._handle_connection_change)
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
            self.console_panel.append("✓ Connected! Requesting initial status...")
            # Request initial status
            QTimer.singleShot(1000, lambda: self._send_command("?"))

    def _update_connection_state(self):
        """Update UI based on connection state."""
        state = self.plotter_state.connection
        port = self.port_combo.currentData() or ""

        # AIDEV-NOTE: Update toolbar connection controls based on state
        if state == ConnectionState.CONNECTED:
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setEnabled(True)
            self.status_label.setText("●")
            self.status_label.setStyleSheet(f"color: {StatusColors.CONNECTED};")
            self.status_label.setToolTip("Connected")
        elif state == ConnectionState.CONNECTING:
            self.connect_btn.setText("Connecting...")
            self.connect_btn.setEnabled(False)
            self.status_label.setText("●")
            self.status_label.setStyleSheet(f"color: {StatusColors.CONNECTING};")
            self.status_label.setToolTip("Connecting...")
        elif state == ConnectionState.ERROR:
            self.connect_btn.setText("Connect")
            self.connect_btn.setEnabled(True)
            self.status_label.setText("●")
            self.status_label.setStyleSheet(f"color: {StatusColors.ERROR};")
            self.status_label.setToolTip("Connection Error")
        else:  # DISCONNECTED
            self.connect_btn.setText("Connect")
            self.connect_btn.setEnabled(True)
            self.status_label.setText("●")
            self.status_label.setStyleSheet(f"color: {StatusColors.DISCONNECTED};")
            self.status_label.setToolTip("Disconnected")

        # Update central workflow with connection state
        self.central_workflow.update_connection_state(state, port)

    # === Command Management ===

    def _queue_command(self, command: str):
        """Add command to the queue."""
        self.queue_panel.add_command(command)
        self._update_queue_count()

    def _queue_command_multiple(self, commands: "list[str]"):
        """Add multiple commands to the display queue."""
        for command in commands:
            self.queue_panel.add_command(command)
        self._update_queue_count()

    def _update_queue_count(self):
        """Update queue count in dashboard."""
        count = self.queue_panel.count()
        self.central_workflow.update_queue_count(count)

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
            QMessageBox.warning(self, "Not Connected", "Please connect to a serial port first.")
            return

        self.serial_thread.send_command(command)
        self.console_panel.append(f"→ Sent: {command}")

    def _send_next_in_queue(self):
        """Send the next command in the queue."""
        command = self.queue_panel.pop_first()
        if command:
            self._send_command(command)
            self._update_queue_count()

    def _send_all_in_queue(self):
        """Send all queued commands with flow control."""
        count = self.queue_panel.count()
        if count == 0:
            return

        # AIDEV-NOTE: Flow control is now handled by SerialThread ACK protocol
        # Commands are sent one at a time, waiting for Arduino acknowledgment
        self.console_panel.append(
            f"📤 Sending {count} commands (flow-controlled, may take time)..."
        )

        while self.queue_panel.count() > 0:
            self._send_next_in_queue()

    def _clear_queue(self):
        """Clear all queued commands."""
        self.queue_panel.clear()
        self._update_queue_count()
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
                self.central_workflow.update_from_hardware_state(self.plotter_state)
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

    # === Image Processing Handlers ===

    def _on_image_processed(self, processed_image: ProcessedImage):
        """Handle completed image processing."""
        path_count = len(processed_image.paths)
        total_length = processed_image.total_path_length
        cmd_count = processed_image.command_count
        self.console_panel.append(
            f"🖼 Image processed: {path_count} paths, {cmd_count} commands, "
            f"{total_length:.1f}mm total length"
        )

    def _on_preview_requested(self, processed_image: ProcessedImage):
        """Show processed paths in simulation canvas."""
        self.console_panel.append(f"🔍 Preview loaded: {len(processed_image.paths)} paths")

    def _queue_image_commands(self, commands: "list[str]"):
        """Add image-generated commands to queue."""
        for command in commands:
            self.queue_panel.add_command(command)
        self._update_queue_count()
        self.console_panel.append(f"➕ Added {len(commands)} commands from image to queue")

    # === Application Lifecycle ===

    def closeEvent(self, a0):
        """Clean up when window closes."""
        self._disconnect()
        if a0:
            a0.accept()
