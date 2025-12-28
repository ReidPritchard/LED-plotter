"""Connect page for serial port connection management."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
import serial.tools.list_ports

from models import ConnectionState  # type: ignore[attr-defined]
from ui.styles import StatusColors


class ConnectPage(QWidget):
    """Page for managing serial port connection."""

    # Navigation signals
    go_to_preview = pyqtSignal()
    go_to_send = pyqtSignal()

    # Connection signals
    connect_requested = pyqtSignal(str)  # Port name
    disconnect_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._current_state = ConnectionState.DISCONNECTED

        self._setup_ui()
        self._refresh_ports()

    def _setup_ui(self) -> None:
        """Initialize the page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Connection panel
        conn_frame = QFrame()
        conn_frame.setStyleSheet(
            """
            QFrame {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 8px;
                padding: 20px;
            }
            """
        )
        conn_layout = QVBoxLayout(conn_frame)
        conn_layout.setSpacing(15)

        # Status indicator
        status_layout = QHBoxLayout()
        status_label = QLabel("Connection Status:")
        status_label.setStyleSheet("font-size: 14px; color: #aaa;")
        status_layout.addWidget(status_label)

        self.status_indicator = QLabel("●")
        self.status_indicator.setStyleSheet(f"font-size: 24px; color: {StatusColors.DISCONNECTED};")
        status_layout.addWidget(self.status_indicator)

        self.status_text = QLabel("Disconnected")
        self.status_text.setStyleSheet("font-size: 14px; font-weight: bold; color: white;")
        status_layout.addWidget(self.status_text)

        status_layout.addStretch()
        conn_layout.addLayout(status_layout)

        # Port selection
        port_layout = QHBoxLayout()

        port_label = QLabel("Serial Port:")
        port_label.setStyleSheet("color: #aaa;")
        port_layout.addWidget(port_label)

        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(300)
        self.port_combo.setStyleSheet(
            """
            QComboBox {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px;
            }
            QComboBox:hover {
                border-color: #666;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #aaa;
                margin-right: 10px;
            }
            """
        )
        port_layout.addWidget(self.port_combo, stretch=1)

        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setStyleSheet(self._button_style())
        self.refresh_btn.clicked.connect(self._refresh_ports)
        port_layout.addWidget(self.refresh_btn)

        conn_layout.addLayout(port_layout)

        # Connect/Disconnect button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setMinimumHeight(50)
        self.connect_btn.setStyleSheet(self._connect_button_style())
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        conn_layout.addWidget(self.connect_btn)

        layout.addWidget(conn_frame)

        # Troubleshooting section
        tips_frame = QFrame()
        tips_frame.setStyleSheet(
            """
            QFrame {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 8px;
                padding: 15px;
            }
            """
        )
        tips_layout = QVBoxLayout(tips_frame)

        tips_title = QLabel("Troubleshooting")
        tips_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #aaa;")
        tips_layout.addWidget(tips_title)

        tips = [
            "• Ensure Arduino is powered on and connected via USB",
            "• Check that no other program is using the serial port",
            "• Serial baud rate is 9600 (configured in Arduino firmware)",
            "• Try unplugging and reconnecting the USB cable",
            "• On macOS, look for ports starting with '/dev/cu.usbserial'",
        ]

        for tip in tips:
            tip_label = QLabel(tip)
            tip_label.setStyleSheet("color: #888; font-size: 12px;")
            tips_layout.addWidget(tip_label)

        layout.addWidget(tips_frame)

        layout.addStretch()

        # Navigation buttons
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(10)

        self.back_btn = QPushButton("< Preview")
        self.back_btn.setMinimumHeight(35)
        self.back_btn.setStyleSheet(self._nav_button_style())
        self.back_btn.clicked.connect(self.go_to_preview.emit)
        nav_layout.addWidget(self.back_btn)

        nav_layout.addStretch()

        self.next_btn = QPushButton("Send >")
        self.next_btn.setMinimumHeight(35)
        self.next_btn.setStyleSheet(self._nav_button_style())
        self.next_btn.clicked.connect(self.go_to_send.emit)
        nav_layout.addWidget(self.next_btn)

        layout.addLayout(nav_layout)

    def _button_style(self) -> str:
        """Get the standard button style."""
        return """
            QPushButton {
                background-color: #3d5a80;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #4d6a90;
            }
            QPushButton:pressed {
                background-color: #2d4a70;
            }
        """

    def _connect_button_style(self) -> str:
        """Get the connect button style."""
        return """
            QPushButton {
                background-color: #2e7d32;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #388e3c;
            }
            QPushButton:pressed {
                background-color: #1b5e20;
            }
        """

    def _disconnect_button_style(self) -> str:
        """Get the disconnect button style."""
        return """
            QPushButton {
                background-color: #c62828;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """

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
        """

    def _refresh_ports(self) -> None:
        """Refresh the list of available serial ports."""
        self.port_combo.clear()

        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo.addItem(f"{port.device} - {port.description}", port.device)

        if not ports:
            self.port_combo.addItem("No ports found", None)

    def _on_connect_clicked(self) -> None:
        """Handle connect/disconnect button click."""
        if self._current_state == ConnectionState.CONNECTED:
            self.disconnect_requested.emit()
        else:
            port = self.port_combo.currentData()
            if port:
                self.connect_requested.emit(port)

    def update_connection_state(self, state: ConnectionState) -> None:
        """Update the UI based on connection state."""
        self._current_state = state

        if state == ConnectionState.CONNECTED:
            self.status_indicator.setStyleSheet(
                f"font-size: 24px; color: {StatusColors.CONNECTED};"
            )
            self.status_text.setText("Connected")
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setStyleSheet(self._disconnect_button_style())
            self.port_combo.setEnabled(False)
            self.refresh_btn.setEnabled(False)
        elif state == ConnectionState.CONNECTING:
            self.status_indicator.setStyleSheet(
                f"font-size: 24px; color: {StatusColors.CONNECTING};"
            )
            self.status_text.setText("Connecting...")
            self.connect_btn.setText("Connecting...")
            self.connect_btn.setEnabled(False)
            self.port_combo.setEnabled(False)
            self.refresh_btn.setEnabled(False)
        elif state == ConnectionState.ERROR:
            self.status_indicator.setStyleSheet(f"font-size: 24px; color: {StatusColors.ERROR};")
            self.status_text.setText("Connection Error")
            self.connect_btn.setText("Retry Connect")
            self.connect_btn.setStyleSheet(self._connect_button_style())
            self.connect_btn.setEnabled(True)
            self.port_combo.setEnabled(True)
            self.refresh_btn.setEnabled(True)
        else:  # DISCONNECTED
            self.status_indicator.setStyleSheet(
                f"font-size: 24px; color: {StatusColors.DISCONNECTED};"
            )
            self.status_text.setText("Disconnected")
            self.connect_btn.setText("Connect")
            self.connect_btn.setStyleSheet(self._connect_button_style())
            self.connect_btn.setEnabled(True)
            self.port_combo.setEnabled(True)
            self.refresh_btn.setEnabled(True)

    def get_selected_port(self) -> str | None:
        """Get the currently selected port."""
        return self.port_combo.currentData()
