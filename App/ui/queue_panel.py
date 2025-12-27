"""Command queue visualization panel."""

from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QListWidget,
    QPushButton,
    QVBoxLayout,
)


class QueuePanel(QGroupBox):
    """Panel for visualizing and managing the command queue."""

    def __init__(self, parent=None):
        super().__init__(None, parent)
        self._setup_ui()

    def _setup_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout()

        self.queue_list = QListWidget()
        layout.addWidget(self.queue_list)

        # Queue controls
        btn_layout = QHBoxLayout()

        self.clear_btn = QPushButton("Clear Queue")
        btn_layout.addWidget(self.clear_btn)

        self.send_next_btn = QPushButton("Send Next")
        btn_layout.addWidget(self.send_next_btn)

        self.send_all_btn = QPushButton("Send All")
        btn_layout.addWidget(self.send_all_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def add_command(self, command: str):
        """Add a command to the queue display."""
        self.queue_list.addItem(command)

    def count(self) -> int:
        """Get number of commands in queue."""
        return self.queue_list.count()

    def pop_first(self) -> str | None:
        """Remove and return first command, or None if empty."""
        if self.queue_list.count() > 0:
            item = self.queue_list.takeItem(0)
            return item.text() if item else None
        return None

    def remove_first(self):
        """Remove the first command from the queue display (deprecated - use pop_first)."""
        if self.queue_list.count() > 0:
            self.queue_list.takeItem(0)

    def clear(self):
        """Clear all commands from the queue display."""
        self.queue_list.clear()

    def is_empty(self) -> bool:
        """Check if the queue is empty."""
        return self.queue_list.count() == 0

    def get_all_commands(self) -> "list[str]":
        """Get all commands currently in the queue display."""
        commands = []
        for i in range(self.queue_list.count()):
            item = self.queue_list.item(i)
            if item:
                commands.append(item.text())
        return commands
