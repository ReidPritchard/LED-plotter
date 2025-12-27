"""Cross-hatch rendering controls component."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout

from models import ImageProcessingConfig
from ui.widgets import WidgetFactory


class CrossHatchControlsWidget(QWidget):
    """Controls for cross-hatch rendering style.

    This component provides UI controls for adjusting cross-hatch rendering parameters:
    - Max angles (number of hatch directions)
    - Base angle (starting angle for hatch layers)
    - Line spacing (dark/light areas)
    - Segment lengths (max/min)
    - Segment gap
    """

    # Signal emitted when any control value changes
    config_changed = pyqtSignal()

    def __init__(self, config: ImageProcessingConfig, parent=None):
        """Initialize cross-hatch controls.

        Args:
            config: Shared processing config (modified directly by this widget)
            parent: Parent widget
        """
        super().__init__(parent)
        self.config = config
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Create and layout UI controls."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Max angles (number of hatch directions)
        self.max_angles_spin = WidgetFactory.create_int_spinbox(
            range_min=2,
            range_max=4,
            value=self.config.cross_hatch_max_angles,
            tooltip="Maximum number of hatch directions (progressive layers)",
        )
        layout.addLayout(WidgetFactory.create_labeled_row("Max Angles:", self.max_angles_spin))

        # Base angle slider with auto-updating label
        self.base_angle_slider, self.base_angle_label = WidgetFactory.create_slider_with_label(
            range_min=0,
            range_max=180,
            value=int(self.config.cross_hatch_base_angle),
            label_format="{}°",
            tick_interval=45,
            tooltip="Starting angle (subsequent angles evenly distributed)",
        )
        base_angle_row = WidgetFactory.create_labeled_row("Base Angle:", self.base_angle_slider)
        base_angle_row.addWidget(self.base_angle_label)
        layout.addLayout(base_angle_row)

        # Line spacing (dark areas)
        self.spacing_dark_spin = WidgetFactory.create_double_spinbox(
            range_min=0.5,
            range_max=20.0,
            value=self.config.cross_hatch_line_spacing_dark,
            suffix=" mm",
            decimals=1,
            step=0.5,
            tooltip="Spacing between lines in dark areas",
        )
        layout.addLayout(
            WidgetFactory.create_labeled_row("Line Spacing (Dark):", self.spacing_dark_spin)
        )

        # Line spacing (light areas)
        self.spacing_light_spin = WidgetFactory.create_double_spinbox(
            range_min=1.0,
            range_max=50.0,
            value=self.config.cross_hatch_line_spacing_light,
            suffix=" mm",
            decimals=1,
            step=1.0,
            tooltip="Spacing between lines in light areas",
        )
        layout.addLayout(
            WidgetFactory.create_labeled_row("Line Spacing (Light):", self.spacing_light_spin)
        )

        # Segment max length
        self.seg_max_spin = WidgetFactory.create_double_spinbox(
            range_min=5.0,
            range_max=100.0,
            value=self.config.cross_hatch_segment_max_length,
            suffix=" mm",
            decimals=1,
            step=5.0,
            tooltip="Max segment length in dark areas",
        )
        layout.addLayout(WidgetFactory.create_labeled_row("Segment Max Length:", self.seg_max_spin))

        # Segment min length
        self.seg_min_spin = WidgetFactory.create_double_spinbox(
            range_min=1.0,
            range_max=50.0,
            value=self.config.cross_hatch_segment_min_length,
            suffix=" mm",
            decimals=1,
            step=1.0,
            tooltip="Min segment length in light areas",
        )
        layout.addLayout(WidgetFactory.create_labeled_row("Segment Min Length:", self.seg_min_spin))

        # Segment gap
        self.seg_gap_spin = WidgetFactory.create_double_spinbox(
            range_min=0.5,
            range_max=20.0,
            value=self.config.cross_hatch_segment_gap,
            suffix=" mm",
            decimals=1,
            step=0.5,
            tooltip="Gap between segments",
        )
        layout.addLayout(WidgetFactory.create_labeled_row("Segment Gap:", self.seg_gap_spin))

        self.setLayout(layout)

    def _connect_signals(self):
        """Connect widget signals to config updates."""
        # Base angle slider needs special handling
        self.base_angle_slider.valueChanged.connect(self._on_base_angle_changed)

        # Direct config updates for other controls
        self.max_angles_spin.valueChanged.connect(
            lambda v: self._update_config("cross_hatch_max_angles", v)
        )
        self.spacing_dark_spin.valueChanged.connect(
            lambda v: self._update_config("cross_hatch_line_spacing_dark", v)
        )
        self.spacing_light_spin.valueChanged.connect(
            lambda v: self._update_config("cross_hatch_line_spacing_light", v)
        )
        self.seg_max_spin.valueChanged.connect(
            lambda v: self._update_config("cross_hatch_segment_max_length", v)
        )
        self.seg_min_spin.valueChanged.connect(
            lambda v: self._update_config("cross_hatch_segment_min_length", v)
        )
        self.seg_gap_spin.valueChanged.connect(
            lambda v: self._update_config("cross_hatch_segment_gap", v)
        )

    def _on_base_angle_changed(self, value: int):
        """Handle base angle slider change.

        Args:
            value: Slider value (0-180 degrees)
        """
        self.config.cross_hatch_base_angle = float(value)
        # Label is auto-updated by widget factory with degree symbol
        self.config_changed.emit()

    def _update_config(self, attr: str, value):
        """Update config attribute and emit signal.

        Args:
            attr: Config attribute name
            value: New value
        """
        setattr(self.config, attr, value)
        self.config_changed.emit()

    def get_config(self) -> ImageProcessingConfig:
        """Get the current configuration.

        Returns:
            Reference to the shared config object
        """
        return self.config
