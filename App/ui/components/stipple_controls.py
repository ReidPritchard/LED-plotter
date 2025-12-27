"""Stipple rendering controls component."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QCheckBox

from models import ImageProcessingConfig
from ui.widgets import WidgetFactory


class StippleControlsWidget(QWidget):
    """Controls for stipple rendering style.

    This component provides UI controls for adjusting stipple rendering parameters:
    - Density (probability of drawing dots)
    - Max/Min radius (dot size range)
    - Points per circle (circle smoothness)
    - Invert mode (dots in bright vs dark areas)
    """

    # Signal emitted when any control value changes
    config_changed = pyqtSignal()

    def __init__(self, config: ImageProcessingConfig, parent=None):
        """Initialize stipple controls.

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

        # Density slider with auto-updating label
        self.density_slider, self.density_label = WidgetFactory.create_slider_with_label(
            range_min=0,
            range_max=100,
            value=int(self.config.stipple_density * 100),
            label_format="{:.2f}",
            tooltip="Probability of drawing each dot",
        )
        density_row = WidgetFactory.create_labeled_row("Density:", self.density_slider)
        density_row.addWidget(self.density_label)
        layout.addLayout(density_row)

        # Max radius spinbox
        self.max_radius_spin = WidgetFactory.create_double_spinbox(
            range_min=0.1,
            range_max=10.0,
            value=self.config.stipple_max_radius,
            suffix=" mm",
            step=0.5,
            tooltip="Maximum dot radius in dark areas",
        )
        layout.addLayout(WidgetFactory.create_labeled_row("Max Radius:", self.max_radius_spin))

        # Min radius spinbox
        self.min_radius_spin = WidgetFactory.create_double_spinbox(
            range_min=0.1,
            range_max=5.0,
            value=self.config.stipple_min_radius,
            suffix=" mm",
            decimals=1,
            step=0.1,
            tooltip="Minimum dot radius in light areas",
        )
        layout.addLayout(WidgetFactory.create_labeled_row("Min Radius:", self.min_radius_spin))

        # Points per circle spinbox
        self.points_spin = WidgetFactory.create_int_spinbox(
            range_min=8,
            range_max=64,
            value=self.config.stipple_points_per_circle,
            step=4,
            tooltip="Number of points to draw each circle",
        )
        layout.addLayout(WidgetFactory.create_labeled_row("Points per Circle:", self.points_spin))

        # Invert checkbox
        self.invert_check = QCheckBox("Invert (dots in bright areas)")
        self.invert_check.setChecked(self.config.stipple_invert)
        self.invert_check.setToolTip("Draw dots in bright areas instead of dark")
        layout.addWidget(self.invert_check)

        self.setLayout(layout)

    def _connect_signals(self):
        """Connect widget signals to config updates."""
        # Density slider needs special handling for label update
        self.density_slider.valueChanged.connect(self._on_density_changed)

        # Direct config updates for other controls
        self.max_radius_spin.valueChanged.connect(
            lambda v: self._update_config("stipple_max_radius", v)
        )
        self.min_radius_spin.valueChanged.connect(
            lambda v: self._update_config("stipple_min_radius", v)
        )
        self.points_spin.valueChanged.connect(
            lambda v: self._update_config("stipple_points_per_circle", v)
        )
        self.invert_check.toggled.connect(lambda v: self._update_config("stipple_invert", v))

    def _on_density_changed(self, value: int):
        """Handle density slider change.

        Args:
            value: Slider value (0-100)
        """
        density = value / 100.0
        self.config.stipple_density = density
        # Label is auto-updated by widget factory, but need to format as float
        self.density_label.setText(f"{density:.2f}")
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
