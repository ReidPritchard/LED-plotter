"""Central workflow widget that manages the main application workflow."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from models import ConnectionState, MachineConfig, PlotterState, ProcessedImage  # type: ignore[attr-defined]
from ui.command_panel import CommandPanel
from ui.image_panel import ImagePanel
from ui.queue_panel import QueuePanel
from ui.simulation import SimulationUI
from ui.workflow.models import WorkflowStep
from ui.workflow.step_bar import WorkflowStepBar
from ui.workflow.pages.dashboard_page import DashboardPage
from ui.workflow.pages.import_page import ImportPage
from ui.workflow.pages.preview_page import PreviewPage
from ui.workflow.pages.connect_page import ConnectPage
from ui.workflow.pages.send_page import SendPage


class CentralWorkflowWidget(QWidget):
    """
    Central widget managing the main application workflow.

    Organizes the workflow into steps:
    - Dashboard: Status overview and quick actions
    - Import: Image import and processing
    - Preview: Simulation and path preview
    - Connect: Serial port connection
    - Send: Command queue and sending
    """

    # AIDEV-NOTE: Workflow navigation signal - emitted when step changes
    step_changed = pyqtSignal(int)  # WorkflowStep value

    # Forwarded signals from embedded panels
    processing_complete = pyqtSignal(object)  # ProcessedImage
    preview_requested = pyqtSignal(object)  # ProcessedImage
    add_to_queue_requested = pyqtSignal(list)  # List[str] commands

    # Connection signals from ConnectPage
    connect_requested = pyqtSignal(str)  # Port name
    disconnect_requested = pyqtSignal()

    # Command signals (forwarded from queue/command panels)
    home_requested = pyqtSignal()

    def __init__(
        self,
        machine_config: MachineConfig,
        plotter_state: PlotterState,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.machine_config = machine_config
        self.plotter_state = plotter_state

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Initialize the workflow UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Step bar at the top
        self.step_bar = WorkflowStepBar()
        layout.addWidget(self.step_bar)

        # Stacked widget for page content
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, stretch=1)

        # Create pages in dependency order
        # AIDEV-NOTE: SendPage created first because PreviewPage needs queue_panel reference
        self.send_page = SendPage(self.machine_config)

        self.dashboard_page = DashboardPage(self.plotter_state)
        self.import_page = ImportPage(self.machine_config)
        self.preview_page = PreviewPage(
            self.machine_config,
            self.plotter_state,
            self.send_page.get_queue_panel(),
        )
        self.connect_page = ConnectPage()

        # Add pages to stack in WorkflowStep order
        self.stack.addWidget(self.dashboard_page)  # 0 = DASHBOARD
        self.stack.addWidget(self.import_page)  # 1 = IMPORT
        self.stack.addWidget(self.preview_page)  # 2 = PREVIEW
        self.stack.addWidget(self.connect_page)  # 3 = CONNECT
        self.stack.addWidget(self.send_page)  # 4 = SEND

    def _connect_signals(self) -> None:
        """Connect all internal signals."""
        # Step bar navigation
        self.step_bar.step_selected.connect(self._on_step_selected)

        # Dashboard quick actions
        self.dashboard_page.go_to_import.connect(lambda: self.set_current_step(WorkflowStep.IMPORT))
        self.dashboard_page.go_to_connect.connect(
            lambda: self.set_current_step(WorkflowStep.CONNECT)
        )
        self.dashboard_page.home_requested.connect(self.home_requested.emit)

        # Import page navigation
        self.import_page.go_to_dashboard.connect(
            lambda: self.set_current_step(WorkflowStep.DASHBOARD)
        )
        self.import_page.go_to_preview.connect(lambda: self.set_current_step(WorkflowStep.PREVIEW))

        # Preview page navigation
        self.preview_page.go_to_import.connect(lambda: self.set_current_step(WorkflowStep.IMPORT))
        self.preview_page.go_to_connect.connect(lambda: self.set_current_step(WorkflowStep.CONNECT))

        # Connect page navigation
        self.connect_page.go_to_preview.connect(lambda: self.set_current_step(WorkflowStep.PREVIEW))
        self.connect_page.go_to_send.connect(lambda: self.set_current_step(WorkflowStep.SEND))

        # Send page navigation
        self.send_page.go_to_connect.connect(lambda: self.set_current_step(WorkflowStep.CONNECT))
        self.send_page.go_to_dashboard.connect(
            lambda: self.set_current_step(WorkflowStep.DASHBOARD)
        )

        # Forward ImagePanel signals
        image_panel = self.import_page.get_image_panel()
        image_panel.processing_complete.connect(self._on_processing_complete)
        image_panel.preview_requested.connect(self._on_preview_requested)
        image_panel.add_to_queue_requested.connect(self.add_to_queue_requested.emit)

        # Forward ConnectPage signals
        self.connect_page.connect_requested.connect(self.connect_requested.emit)
        self.connect_page.disconnect_requested.connect(self.disconnect_requested.emit)

    def _on_step_selected(self, step_value: int) -> None:
        """Handle step selection from step bar."""
        step = WorkflowStep(step_value)
        self.set_current_step(step)

    def _on_processing_complete(self, processed_image: ProcessedImage) -> None:
        """Handle image processing completion."""
        # Update dashboard with image info
        self.dashboard_page.update_image_status(
            loaded=True,
            path_count=len(processed_image.paths),
            cmd_count=processed_image.command_count,
        )
        # Update preview stats
        self.preview_page.update_command_count(processed_image.command_count)
        # Forward signal
        self.processing_complete.emit(processed_image)

    def _on_preview_requested(self, processed_image: ProcessedImage) -> None:
        """Handle preview request - show paths in simulation."""
        self.preview_page.set_preview_paths(processed_image.paths)
        # Navigate to preview page
        self.set_current_step(WorkflowStep.PREVIEW)
        # Forward signal
        self.preview_requested.emit(processed_image)

    # === Public Methods ===

    def set_current_step(self, step: WorkflowStep) -> None:
        """Navigate to a specific workflow step."""
        self.step_bar.set_current_step(step)
        self.stack.setCurrentIndex(int(step))
        self.step_changed.emit(int(step))

    def get_current_step(self) -> WorkflowStep:
        """Get the currently active step."""
        return self.step_bar.get_current_step()

    def update_connection_state(self, state: ConnectionState, port: str = "") -> None:
        """Update connection status across all relevant pages."""
        self.dashboard_page.update_connection_state(state, port)
        self.connect_page.update_connection_state(state)

    def update_queue_count(self, count: int) -> None:
        """Update queue count display on dashboard."""
        self.dashboard_page.update_queue_count(count)

    def update_plotter_position(self, x: float, y: float) -> None:
        """Update plotter position on dashboard."""
        self.dashboard_page.update_plotter_position(x, y)

    def update_from_hardware_state(self, plotter_state: PlotterState) -> None:
        """Update simulation from hardware state."""
        self.preview_page.get_simulation_ui().update_from_hardware_state(plotter_state)
        self.update_plotter_position(plotter_state.position_x, plotter_state.position_y)

    # === Access to Embedded Panels ===

    def get_image_panel(self) -> ImagePanel:
        """Get the embedded ImagePanel for signal connections."""
        return self.import_page.get_image_panel()

    def get_simulation_ui(self) -> SimulationUI:
        """Get the embedded SimulationUI for updates."""
        return self.preview_page.get_simulation_ui()

    def get_queue_panel(self) -> QueuePanel:
        """Get the embedded QueuePanel for queue operations."""
        return self.send_page.get_queue_panel()

    def get_command_panel(self) -> CommandPanel:
        """Get the embedded CommandPanel for command operations."""
        return self.send_page.get_command_panel()
