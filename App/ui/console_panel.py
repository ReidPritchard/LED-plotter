"""Console output panel."""

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QGroupBox, QPushButton, QTextEdit, QVBoxLayout


class ConsolePanel(QGroupBox):
    """Panel for displaying serial communication console output."""

    def __init__(self, parent=None):
        super().__init__("Console Output", parent)
        self._setup_ui()

    def _setup_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout()

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setMaximumHeight(150)
        self.console.setFont(QFont("Courier", 9))
        layout.addWidget(self.console)

        clear_console_btn = QPushButton("Clear Console")
        clear_console_btn.clicked.connect(self.clear)
        layout.addWidget(clear_console_btn)

        self.setLayout(layout)

    def append(self, message: str):
        """Add a message to the console."""
        self.console.append(message)
        # Auto-scroll to bottom
        self.console.verticalScrollBar().setValue(
            self.console.verticalScrollBar().maximum()
        )

    def clear(self):
        """Clear all console output."""
        self.console.clear()
