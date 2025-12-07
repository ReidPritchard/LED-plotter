"""Serial connection control panel."""

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
)

# Try to import serial, gracefully handle if not installed
try:
    import serial.tools.list_ports

    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


class ConnectionPanel(QGroupBox):
    """Panel for managing serial port connections."""

    def __init__(self, parent=None):
        super().__init__("Serial Connection", parent)
        self._setup_ui()

    def _setup_ui(self):
        """Initialize the UI components."""
        layout = QHBoxLayout()

        # Port selection
        layout.addWidget(QLabel("Port:"))
        self.port_combo = QComboBox()
        self.refresh_ports()
        layout.addWidget(self.port_combo)

        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_ports)
        layout.addWidget(refresh_btn)

        # Connect/Disconnect button
        self.connect_btn = QPushButton("Connect")
        layout.addWidget(self.connect_btn)

        # Connection status indicator
        self.status_label = QLabel("●")
        self.status_label.setFont(QFont("Arial", 16))
        layout.addWidget(self.status_label)

        layout.addStretch()
        self.setLayout(layout)

    def refresh_ports(self):
        """Refresh the list of available serial ports."""
        self.port_combo.clear()
        if SERIAL_AVAILABLE:
            ports = serial.tools.list_ports.comports()  # type: ignore
            for port in ports:
                self.port_combo.addItem(
                    f"{port.device} - {port.description}", port.device
                )
            if not ports:
                self.port_combo.addItem("No ports found", None)
        else:
            self.port_combo.addItem("pyserial not installed", None)

    def get_selected_port(self) -> str:
        """Get the currently selected port."""
        return self.port_combo.currentData()

    def update_status(
        self, connected: bool, connecting: bool = False, error: bool = False
    ):
        """Update the visual connection status."""
        if connected:
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setEnabled(True)
            self.status_label.setText("●")
            self.status_label.setStyleSheet("color: green;")
        elif connecting:
            self.connect_btn.setText("Connecting...")
            self.connect_btn.setEnabled(False)
            self.status_label.setText("●")
            self.status_label.setStyleSheet("color: orange;")
        elif error:
            self.connect_btn.setText("Connect")
            self.connect_btn.setEnabled(True)
            self.status_label.setText("●")
            self.status_label.setStyleSheet("color: red;")
        else:  # Disconnected
            self.connect_btn.setText("Connect")
            self.connect_btn.setEnabled(True)
            self.status_label.setText("●")
            self.status_label.setStyleSheet("color: gray;")
