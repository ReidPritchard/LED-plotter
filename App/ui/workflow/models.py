"""Data models for the workflow widget."""

from enum import IntEnum


class WorkflowStep(IntEnum):
    """Workflow step identifiers for navigation."""

    DASHBOARD = 0
    IMPORT = 1
    PREVIEW = 2
    CONNECT = 3
    SEND = 4

    @property
    def label(self) -> str:
        """Get display label for step."""
        labels = {
            WorkflowStep.DASHBOARD: "Dashboard",
            WorkflowStep.IMPORT: "1. Import",
            WorkflowStep.PREVIEW: "2. Preview",
            WorkflowStep.CONNECT: "3. Connect",
            WorkflowStep.SEND: "4. Send",
        }
        return labels.get(self, str(self.name))

    @property
    def icon(self) -> str:
        """Get icon/emoji for step (wireframe style)."""
        icons = {
            WorkflowStep.DASHBOARD: "🏠",
            WorkflowStep.IMPORT: "📁",
            WorkflowStep.PREVIEW: "👁",
            WorkflowStep.CONNECT: "🔌",
            WorkflowStep.SEND: "📤",
        }
        return icons.get(self, "○")
