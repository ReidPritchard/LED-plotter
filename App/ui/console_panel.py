"""Console output panel."""

from PyQt6.QtWidgets import QGroupBox, QPushButton, QTextEdit, QVBoxLayout

from ui.styles import FONTS, SIZES


class ConsolePanel(QGroupBox):
    """Panel for displaying serial communication console output."""

    def __init__(self, parent=None):
        super().__init__(None, parent)
        self._setup_ui()

    def _setup_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout()

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        # AIDEV-NOTE: Use minimum height only - let dock widget handle sizing
        self.console.setMinimumHeight(SIZES.CONSOLE_MIN_HEIGHT)
        self.console.setFont(FONTS.CONSOLE)
        layout.addWidget(self.console)

        clear_console_btn = QPushButton("Clear Console")
        clear_console_btn.clicked.connect(self.clear)
        layout.addWidget(clear_console_btn)

        self.setLayout(layout)

    def append(self, message: str):
        """Add a message to the console."""
        self.console.append(message)
        # Auto-scroll to bottom
        scrollbar = self.console.verticalScrollBar()
        if scrollbar:
            scrollbar.setValue(scrollbar.maximum())

    def clear(self):
        """Clear all console output."""
        self.console.clear()
