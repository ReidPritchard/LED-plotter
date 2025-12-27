"""Horizontal step bar for workflow navigation."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from ui.workflow.models import WorkflowStep


class WorkflowStepIndicator(QPushButton):
    """Individual step indicator button."""

    def __init__(self, step: WorkflowStep, parent: QWidget | None = None):
        super().__init__(parent)
        self.step = step
        self._is_active = False

        # Setup button
        self.setText(f"{step.icon} {step.label}")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(40)

        self._update_style()

    def set_active(self, active: bool) -> None:
        """Set whether this step is currently active."""
        self._is_active = active
        self.setChecked(active)
        self._update_style()

    def _update_style(self) -> None:
        """Update button style based on state."""
        # AIDEV-NOTE: Wireframe styling - minimal but functional
        if self._is_active:
            self.setStyleSheet(
                """
                QPushButton {
                    background-color: #3d5a80;
                    color: white;
                    border: 2px solid #5d7a9d;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #4d6a90;
                }
                """
            )
        else:
            self.setStyleSheet(
                """
                QPushButton {
                    background-color: #2a2a2a;
                    color: #888;
                    border: 1px solid #444;
                    border-radius: 4px;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #3a3a3a;
                    color: #aaa;
                }
                """
            )


class WorkflowStepBar(QFrame):
    """Horizontal bar with clickable workflow step indicators."""

    # Emitted when a step is selected
    step_selected = pyqtSignal(int)  # WorkflowStep value

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._current_step = WorkflowStep.DASHBOARD
        self._indicators: dict[WorkflowStep, WorkflowStepIndicator] = {}

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Initialize the step bar UI."""
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet(
            """
            QFrame {
                background-color: #1a1a1a;
                border-bottom: 1px solid #333;
            }
            """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(5)

        # Create step indicators
        for step in WorkflowStep:
            indicator = WorkflowStepIndicator(step)
            indicator.clicked.connect(lambda checked, s=step: self._on_step_clicked(s))
            self._indicators[step] = indicator
            layout.addWidget(indicator)

            # Add separator arrow (except after last step)
            if step != WorkflowStep.SEND:
                separator = self._create_separator()
                layout.addWidget(separator)

        # Set initial active step
        self._update_indicators()

    def _create_separator(self) -> QWidget:
        """Create a separator arrow between steps."""
        from PyQt6.QtWidgets import QLabel

        separator = QLabel("→")
        separator.setStyleSheet("color: #555; font-size: 16px;")
        separator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        separator.setFixedWidth(30)
        return separator

    def _on_step_clicked(self, step: WorkflowStep) -> None:
        """Handle step indicator click."""
        if step != self._current_step:
            self.set_current_step(step)
            self.step_selected.emit(int(step))

    def set_current_step(self, step: WorkflowStep) -> None:
        """Set the currently active step."""
        self._current_step = step
        self._update_indicators()

    def _update_indicators(self) -> None:
        """Update all indicator visual states."""
        for step, indicator in self._indicators.items():
            indicator.set_active(step == self._current_step)

    def get_current_step(self) -> WorkflowStep:
        """Get the currently active step."""
        return self._current_step
