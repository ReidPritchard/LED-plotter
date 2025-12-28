"""Dashboard page with status overview and quick actions."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from models import ConnectionState, PlotterState  # type: ignore[attr-defined]


class StatusCard(QGroupBox):
    """A card displaying status information."""

    def __init__(self, title: str, parent: QWidget | None = None):
        super().__init__(title, parent)
        self.setStyleSheet(
            """
            QGroupBox {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 6px;
                margin-top: 12px;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #aaa;
            }
            """
        )
        self.setMinimumSize(180, 100)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(10, 15, 10, 10)

        # Main value label
        self.value_label = QLabel("--")
        self.value_label.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        self._layout.addWidget(self.value_label)

        # Detail label
        self.detail_label = QLabel("")
        self.detail_label.setStyleSheet("font-size: 11px; color: #888;")
        self._layout.addWidget(self.detail_label)

        self._layout.addStretch()

    def set_value(self, value: str) -> None:
        """Set the main value text."""
        self.value_label.setText(value)

    def set_detail(self, detail: str) -> None:
        """Set the detail text."""
        self.detail_label.setText(detail)

    def set_status_color(self, color: str) -> None:
        """Set the value label color."""
        self.value_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {color};")


class DashboardPage(QWidget):
    """Dashboard page with status overview and quick actions."""

    # Navigation signals
    go_to_import = pyqtSignal()
    go_to_connect = pyqtSignal()
    home_requested = pyqtSignal()

    def __init__(self, plotter_state: PlotterState, parent: QWidget | None = None):
        super().__init__(parent)
        self.plotter_state = plotter_state

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Initialize the dashboard UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Title
        title = QLabel("PolarPlot Dashboard")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Status cards grid
        cards_layout = QGridLayout()
        cards_layout.setSpacing(15)

        # Connection status card
        self.connection_card = StatusCard("Connection")
        self.connection_card.set_value("Disconnected")
        self.connection_card.set_detail("No port selected")
        self.connection_card.set_status_color("gray")
        cards_layout.addWidget(self.connection_card, 0, 0)

        # Queue status card
        self.queue_card = StatusCard("Command Queue")
        self.queue_card.set_value("0 commands")
        self.queue_card.set_detail("Queue is empty")
        cards_layout.addWidget(self.queue_card, 0, 1)

        # Image status card
        self.image_card = StatusCard("Image")
        self.image_card.set_value("No image")
        self.image_card.set_detail("Import an image to begin")
        cards_layout.addWidget(self.image_card, 1, 0)

        # Plotter position card
        self.position_card = StatusCard("Plotter Position")
        self.position_card.set_value("X: -- Y: --")
        self.position_card.set_detail("Connect to view position")
        cards_layout.addWidget(self.position_card, 1, 1)

        layout.addLayout(cards_layout)

        # Quick actions section
        actions_frame = QFrame()
        actions_frame.setStyleSheet(
            """
            QFrame {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 15px;
            }
            """
        )
        actions_layout = QVBoxLayout(actions_frame)

        actions_label = QLabel("Quick Actions")
        actions_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #aaa;")
        actions_layout.addWidget(actions_label)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        # Import Image button
        self.import_btn = QPushButton("📁 Import Image")
        self.import_btn.setMinimumHeight(40)
        self.import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.import_btn.setStyleSheet(self._button_style())
        self.import_btn.clicked.connect(self.go_to_import.emit)
        buttons_layout.addWidget(self.import_btn)

        # Connect button
        self.connect_btn = QPushButton("🔌 Connect to Plotter")
        self.connect_btn.setMinimumHeight(40)
        self.connect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.connect_btn.setStyleSheet(self._button_style())
        self.connect_btn.clicked.connect(self.go_to_connect.emit)
        buttons_layout.addWidget(self.connect_btn)

        # Home button
        self.home_btn = QPushButton("🏠 Home Plotter")
        self.home_btn.setMinimumHeight(40)
        self.home_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.home_btn.setStyleSheet(self._button_style())
        self.home_btn.setEnabled(False)  # Disabled until connected
        self.home_btn.clicked.connect(self.home_requested.emit)
        buttons_layout.addWidget(self.home_btn)

        actions_layout.addLayout(buttons_layout)
        layout.addWidget(actions_frame)

        layout.addStretch()

    def _button_style(self) -> str:
        """Get the standard button style."""
        return """
            QPushButton {
                background-color: #3d5a80;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
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

    def update_connection_state(self, state: ConnectionState, port: str = "") -> None:
        """Update the connection status card."""
        if state == ConnectionState.CONNECTED:
            self.connection_card.set_value("Connected")
            self.connection_card.set_detail(f"Port: {port}")
            self.connection_card.set_status_color("green")
            self.home_btn.setEnabled(True)
        elif state == ConnectionState.CONNECTING:
            self.connection_card.set_value("Connecting...")
            self.connection_card.set_detail(f"Port: {port}")
            self.connection_card.set_status_color("orange")
            self.home_btn.setEnabled(False)
        elif state == ConnectionState.ERROR:
            self.connection_card.set_value("Error")
            self.connection_card.set_detail("Connection failed")
            self.connection_card.set_status_color("red")
            self.home_btn.setEnabled(False)
        else:  # DISCONNECTED
            self.connection_card.set_value("Disconnected")
            self.connection_card.set_detail("No port selected")
            self.connection_card.set_status_color("gray")
            self.home_btn.setEnabled(False)

    def update_queue_count(self, count: int, time_estimate: float = 0.0) -> None:
        """Update the queue status card."""
        self.queue_card.set_value(f"{count} commands")
        if count == 0:
            self.queue_card.set_detail("Queue is empty")
        else:
            estimate_minutes = time_estimate / 60
            if estimate_minutes >= 1:
                self.queue_card.set_detail(f"Ready to send\nEst. time: {estimate_minutes:.1f}min")
            else:
                self.queue_card.set_detail(f"Ready to send\nEst. time: {time_estimate:.1f}s")

    def update_image_status(self, loaded: bool, path_count: int = 0, cmd_count: int = 0) -> None:
        """Update the image status card."""
        if loaded:
            self.image_card.set_value(f"{path_count} paths")
            self.image_card.set_detail(f"{cmd_count} commands ready")
        else:
            self.image_card.set_value("No image")
            self.image_card.set_detail("Import an image to begin")

    def update_plotter_position(self, x: float, y: float) -> None:
        """Update the plotter position card."""
        self.position_card.set_value(f"X: {x:.1f} Y: {y:.1f}")
        self.position_card.set_detail("Position in mm")
