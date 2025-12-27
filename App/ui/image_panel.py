"""Image import and processing panel for photo-to-plotter workflow."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from image_processing import ImageProcessor
from models import (
    ImageProcessingConfig,
    MachineConfig,
    ProcessedImage,
    RenderStyle,
)
from path_to_commands import PathToCommandsConverter


class ProcessingThread(QThread):
    """Background thread for image processing to avoid blocking UI."""

    finished = pyqtSignal(object)  # ProcessedImage
    error = pyqtSignal(str)  # Error message
    progress = pyqtSignal(int)  # Progress percentage

    def __init__(
        self,
        file_path: str,
        machine_config: MachineConfig,
        processing_config: ImageProcessingConfig,
    ):
        super().__init__()
        self.file_path = file_path
        self.machine_config = machine_config
        self.processing_config = processing_config

    def run(self):
        """Execute image processing in background."""
        try:
            processor = ImageProcessor(
                self.machine_config, self.processing_config
            )

            self.progress.emit(10)
            # Load image
            _ = processor.load_image(self.file_path)

            self.progress.emit(30)
            # Process image
            result = processor.process(self.file_path)

            self.progress.emit(100)
            self.finished.emit(result)

        except Exception as e:
            self.error.emit(str(e))


class ImagePanel(QGroupBox):
    """Panel for image import and processing controls."""

    # Signals for communication with main window
    processing_complete = pyqtSignal(object)  # ProcessedImage
    preview_requested = pyqtSignal(object)  # ProcessedImage
    add_to_queue_requested = pyqtSignal(list)  # List[str] commands

    def __init__(
        self, machine_config: MachineConfig, parent: QWidget | None = None
    ):
        super().__init__("Image Import", parent)
        self.machine_config = machine_config
        self.processing_config = ImageProcessingConfig()
        self.current_image_path: str | None = None
        self.processed_result: ProcessedImage | None = None
        self.processing_thread: ProcessingThread | None = None

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout()

        # --- Image Selection Section ---
        self._create_file_selection(layout)

        # --- Image Preview ---
        self._create_preview_area(layout)

        # --- Color Quantization Controls ---
        self._create_quantization_controls(layout)

        # --- Processing Options ---
        self._create_processing_options(layout)

        # --- Action Buttons ---
        self._create_action_buttons(layout)

        # --- Progress and Status ---
        self._create_status_area(layout)

        self.setLayout(layout)

    def _create_file_selection(self, parent_layout: QVBoxLayout):
        """Create file selection controls."""
        file_layout = QHBoxLayout()

        self.file_path_label = QLabel("No image selected")
        self.file_path_label.setWordWrap(True)
        file_layout.addWidget(self.file_path_label, stretch=1)

        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.setToolTip("Select an image file (PNG, JPG, etc.)")
        file_layout.addWidget(self.browse_btn)

        parent_layout.addLayout(file_layout)

    def _create_preview_area(self, parent_layout: QVBoxLayout):
        """Create image preview thumbnail."""
        self.preview_label = QLabel()
        self.preview_label.setMinimumSize(200, 150)
        self.preview_label.setMaximumSize(400, 300)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet(
            "border: 1px solid gray; background-color: #2a2a2a;"
        )
        self.preview_label.setText("Image preview will appear here")
        parent_layout.addWidget(self.preview_label)

    def _create_quantization_controls(self, parent_layout: QVBoxLayout):
        """Create color quantization controls."""
        quant_group = QGroupBox("Color Quantization")
        quant_layout = QVBoxLayout()

        # Number of colors
        colors_layout = QHBoxLayout()
        colors_layout.addWidget(QLabel("Colors:"))

        self.num_colors_slider = QSlider(Qt.Orientation.Horizontal)
        self.num_colors_slider.setRange(4, 32)
        self.num_colors_slider.setValue(8)
        self.num_colors_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.num_colors_slider.setTickInterval(4)
        colors_layout.addWidget(self.num_colors_slider)

        self.num_colors_label = QLabel("8")
        self.num_colors_label.setMinimumWidth(30)
        colors_layout.addWidget(self.num_colors_label)

        quant_layout.addLayout(colors_layout)

        # Quantization method
        method_layout = QHBoxLayout()
        method_layout.addWidget(QLabel("Method:"))

        self.quant_method_combo = QComboBox()
        self.quant_method_combo.addItems(
            [
                "K-Means (Best quality)",
                "Median Cut (Faster)",
                "Octree (Fastest)",
            ]
        )
        method_layout.addWidget(self.quant_method_combo)

        quant_layout.addLayout(method_layout)

        quant_group.setLayout(quant_layout)
        parent_layout.addWidget(quant_group)

    def _create_processing_options(self, parent_layout: QVBoxLayout):
        """Create vectorization options."""
        options_group = QGroupBox("Vectorization Options")
        options_layout = QVBoxLayout()

        # Render style selection
        style_layout = QHBoxLayout()
        style_layout.addWidget(QLabel("Render Style:"))
        self.render_style_combo = QComboBox()
        self.render_style_combo.addItems(
            [style.name.replace("_", " ").title() for style in RenderStyle]
        )
        style_layout.addWidget(self.render_style_combo)
        options_layout.addLayout(style_layout)

        # Style-specific settings container
        self.style_settings_group = QGroupBox("Style Settings")
        self.style_settings_layout = QVBoxLayout()
        self.style_settings_group.setLayout(self.style_settings_layout)
        options_layout.addWidget(self.style_settings_group)

        # Create controls for each style (will be shown/hidden dynamically)
        self._create_stipple_controls()
        self._create_hatching_controls()
        self._create_cross_hatch_controls()

        # Initially show controls for first style
        self._update_style_controls(0)

        options_group.setLayout(options_layout)
        parent_layout.addWidget(options_group)

    def _create_stipple_controls(self):
        """Create controls for stipple rendering style."""
        self.stipple_controls_widget = QWidget()
        stipple_layout = QVBoxLayout()
        stipple_layout.setContentsMargins(0, 0, 0, 0)

        # Density slider
        density_layout = QHBoxLayout()
        density_layout.addWidget(QLabel("Density:"))
        self.stipple_density_slider = QSlider(Qt.Orientation.Horizontal)
        self.stipple_density_slider.setRange(0, 100)
        self.stipple_density_slider.setValue(
            int(self.processing_config.stipple_density * 100)
        )
        self.stipple_density_slider.setToolTip(
            "Probability of drawing each dot"
        )
        density_layout.addWidget(self.stipple_density_slider)
        self.stipple_density_label = QLabel(
            f"{self.processing_config.stipple_density:.2f}"
        )
        self.stipple_density_label.setMinimumWidth(40)
        density_layout.addWidget(self.stipple_density_label)
        stipple_layout.addLayout(density_layout)

        # Max radius
        max_rad_layout = QHBoxLayout()
        max_rad_layout.addWidget(QLabel("Max Radius:"))
        self.stipple_max_radius_spin = QDoubleSpinBox()
        self.stipple_max_radius_spin.setRange(0.1, 10.0)
        self.stipple_max_radius_spin.setSingleStep(0.5)
        self.stipple_max_radius_spin.setValue(
            self.processing_config.stipple_max_radius
        )
        self.stipple_max_radius_spin.setSuffix(" mm")
        self.stipple_max_radius_spin.setToolTip(
            "Maximum dot radius in dark areas"
        )
        max_rad_layout.addWidget(self.stipple_max_radius_spin)
        stipple_layout.addLayout(max_rad_layout)

        # Min radius
        min_rad_layout = QHBoxLayout()
        min_rad_layout.addWidget(QLabel("Min Radius:"))
        self.stipple_min_radius_spin = QDoubleSpinBox()
        self.stipple_min_radius_spin.setRange(0.1, 5.0)
        self.stipple_min_radius_spin.setSingleStep(0.1)
        self.stipple_min_radius_spin.setValue(
            self.processing_config.stipple_min_radius
        )
        self.stipple_min_radius_spin.setSuffix(" mm")
        self.stipple_min_radius_spin.setToolTip(
            "Minimum dot radius in light areas"
        )
        min_rad_layout.addWidget(self.stipple_min_radius_spin)
        stipple_layout.addLayout(min_rad_layout)

        # Points per circle
        points_layout = QHBoxLayout()
        points_layout.addWidget(QLabel("Points per Circle:"))
        self.stipple_points_spin = QSpinBox()
        self.stipple_points_spin.setRange(8, 64)
        self.stipple_points_spin.setSingleStep(4)
        self.stipple_points_spin.setValue(
            self.processing_config.stipple_points_per_circle
        )
        self.stipple_points_spin.setToolTip(
            "Number of points to draw each circle"
        )
        points_layout.addWidget(self.stipple_points_spin)
        stipple_layout.addLayout(points_layout)

        # Invert checkbox
        self.stipple_invert_check = QCheckBox("Invert (dots in bright areas)")
        self.stipple_invert_check.setChecked(
            self.processing_config.stipple_invert
        )
        self.stipple_invert_check.setToolTip(
            "Draw dots in bright areas instead of dark"
        )
        stipple_layout.addWidget(self.stipple_invert_check)

        self.stipple_controls_widget.setLayout(stipple_layout)
        self.style_settings_layout.addWidget(self.stipple_controls_widget)

    def _create_hatching_controls(self):
        """Create controls for hatching rendering style."""
        self.hatching_controls_widget = QWidget()
        hatching_layout = QVBoxLayout()
        hatching_layout.setContentsMargins(0, 0, 0, 0)

        # Line spacing (dark)
        dark_spacing_layout = QHBoxLayout()
        dark_spacing_layout.addWidget(QLabel("Line Spacing (Dark):"))
        self.hatching_spacing_dark_spin = QDoubleSpinBox()
        self.hatching_spacing_dark_spin.setRange(0.5, 20.0)
        self.hatching_spacing_dark_spin.setSingleStep(0.5)
        self.hatching_spacing_dark_spin.setValue(
            self.processing_config.hatching_line_spacing_dark
        )
        self.hatching_spacing_dark_spin.setSuffix(" mm")
        self.hatching_spacing_dark_spin.setToolTip(
            "Spacing between lines in dark areas"
        )
        dark_spacing_layout.addWidget(self.hatching_spacing_dark_spin)
        hatching_layout.addLayout(dark_spacing_layout)

        # Line spacing (light)
        light_spacing_layout = QHBoxLayout()
        light_spacing_layout.addWidget(QLabel("Line Spacing (Light):"))
        self.hatching_spacing_light_spin = QDoubleSpinBox()
        self.hatching_spacing_light_spin.setRange(1.0, 50.0)
        self.hatching_spacing_light_spin.setSingleStep(1.0)
        self.hatching_spacing_light_spin.setValue(
            self.processing_config.hatching_line_spacing_light
        )
        self.hatching_spacing_light_spin.setSuffix(" mm")
        self.hatching_spacing_light_spin.setToolTip(
            "Spacing between lines in light areas"
        )
        light_spacing_layout.addWidget(self.hatching_spacing_light_spin)
        hatching_layout.addLayout(light_spacing_layout)

        # Angle slider
        angle_layout = QHBoxLayout()
        angle_layout.addWidget(QLabel("Angle:"))
        self.hatching_angle_slider = QSlider(Qt.Orientation.Horizontal)
        self.hatching_angle_slider.setRange(0, 180)
        self.hatching_angle_slider.setValue(
            int(self.processing_config.hatching_angle)
        )
        self.hatching_angle_slider.setTickPosition(
            QSlider.TickPosition.TicksBelow
        )
        self.hatching_angle_slider.setTickInterval(45)
        self.hatching_angle_slider.setToolTip("Angle of hatching lines")
        angle_layout.addWidget(self.hatching_angle_slider)
        self.hatching_angle_label = QLabel(
            f"{self.processing_config.hatching_angle:.0f}°"
        )
        self.hatching_angle_label.setMinimumWidth(40)
        angle_layout.addWidget(self.hatching_angle_label)
        hatching_layout.addLayout(angle_layout)

        # Segment max length
        seg_max_layout = QHBoxLayout()
        seg_max_layout.addWidget(QLabel("Segment Max Length:"))
        self.hatching_seg_max_spin = QDoubleSpinBox()
        self.hatching_seg_max_spin.setRange(5.0, 100.0)
        self.hatching_seg_max_spin.setSingleStep(5.0)
        self.hatching_seg_max_spin.setValue(
            self.processing_config.hatching_segment_max_length
        )
        self.hatching_seg_max_spin.setSuffix(" mm")
        self.hatching_seg_max_spin.setToolTip(
            "Max segment length in dark areas"
        )
        seg_max_layout.addWidget(self.hatching_seg_max_spin)
        hatching_layout.addLayout(seg_max_layout)

        # Segment min length
        seg_min_layout = QHBoxLayout()
        seg_min_layout.addWidget(QLabel("Segment Min Length:"))
        self.hatching_seg_min_spin = QDoubleSpinBox()
        self.hatching_seg_min_spin.setRange(1.0, 50.0)
        self.hatching_seg_min_spin.setSingleStep(1.0)
        self.hatching_seg_min_spin.setValue(
            self.processing_config.hatching_segment_min_length
        )
        self.hatching_seg_min_spin.setSuffix(" mm")
        self.hatching_seg_min_spin.setToolTip(
            "Min segment length in light areas"
        )
        seg_min_layout.addWidget(self.hatching_seg_min_spin)
        hatching_layout.addLayout(seg_min_layout)

        # Segment gap
        seg_gap_layout = QHBoxLayout()
        seg_gap_layout.addWidget(QLabel("Segment Gap:"))
        self.hatching_seg_gap_spin = QDoubleSpinBox()
        self.hatching_seg_gap_spin.setRange(0.5, 20.0)
        self.hatching_seg_gap_spin.setSingleStep(0.5)
        self.hatching_seg_gap_spin.setValue(
            self.processing_config.hatching_segment_gap
        )
        self.hatching_seg_gap_spin.setSuffix(" mm")
        self.hatching_seg_gap_spin.setToolTip("Gap between segments")
        seg_gap_layout.addWidget(self.hatching_seg_gap_spin)
        hatching_layout.addLayout(seg_gap_layout)

        self.hatching_controls_widget.setLayout(hatching_layout)
        self.style_settings_layout.addWidget(self.hatching_controls_widget)

    def _create_cross_hatch_controls(self):
        """Create controls for cross-hatch rendering style."""
        self.cross_hatch_controls_widget = QWidget()
        cross_hatch_layout = QVBoxLayout()
        cross_hatch_layout.setContentsMargins(0, 0, 0, 0)

        # Max angles (number of hatch directions)
        max_angles_layout = QHBoxLayout()
        max_angles_layout.addWidget(QLabel("Max Angles:"))
        self.cross_hatch_max_angles_spin = QSpinBox()
        self.cross_hatch_max_angles_spin.setRange(2, 4)
        self.cross_hatch_max_angles_spin.setValue(
            self.processing_config.cross_hatch_max_angles
        )
        self.cross_hatch_max_angles_spin.setToolTip(
            "Maximum number of hatch directions (progressive layers)"
        )
        max_angles_layout.addWidget(self.cross_hatch_max_angles_spin)
        cross_hatch_layout.addLayout(max_angles_layout)

        # Base angle slider
        base_angle_layout = QHBoxLayout()
        base_angle_layout.addWidget(QLabel("Base Angle:"))
        self.cross_hatch_base_angle_slider = QSlider(Qt.Orientation.Horizontal)
        self.cross_hatch_base_angle_slider.setRange(0, 180)
        self.cross_hatch_base_angle_slider.setValue(
            int(self.processing_config.cross_hatch_base_angle)
        )
        self.cross_hatch_base_angle_slider.setTickPosition(
            QSlider.TickPosition.TicksBelow
        )
        self.cross_hatch_base_angle_slider.setTickInterval(45)
        self.cross_hatch_base_angle_slider.setToolTip(
            "Starting angle (subsequent angles evenly distributed)"
        )
        base_angle_layout.addWidget(self.cross_hatch_base_angle_slider)
        self.cross_hatch_base_angle_label = QLabel(
            f"{self.processing_config.cross_hatch_base_angle:.0f}°"
        )
        self.cross_hatch_base_angle_label.setMinimumWidth(40)
        base_angle_layout.addWidget(self.cross_hatch_base_angle_label)
        cross_hatch_layout.addLayout(base_angle_layout)

        # Line spacing (dark)
        dark_spacing_layout = QHBoxLayout()
        dark_spacing_layout.addWidget(QLabel("Line Spacing (Dark):"))
        self.cross_hatch_spacing_dark_spin = QDoubleSpinBox()
        self.cross_hatch_spacing_dark_spin.setRange(0.5, 20.0)
        self.cross_hatch_spacing_dark_spin.setSingleStep(0.5)
        self.cross_hatch_spacing_dark_spin.setValue(
            self.processing_config.cross_hatch_line_spacing_dark
        )
        self.cross_hatch_spacing_dark_spin.setSuffix(" mm")
        self.cross_hatch_spacing_dark_spin.setToolTip(
            "Spacing between lines in dark areas"
        )
        dark_spacing_layout.addWidget(self.cross_hatch_spacing_dark_spin)
        cross_hatch_layout.addLayout(dark_spacing_layout)

        # Line spacing (light)
        light_spacing_layout = QHBoxLayout()
        light_spacing_layout.addWidget(QLabel("Line Spacing (Light):"))
        self.cross_hatch_spacing_light_spin = QDoubleSpinBox()
        self.cross_hatch_spacing_light_spin.setRange(1.0, 50.0)
        self.cross_hatch_spacing_light_spin.setSingleStep(1.0)
        self.cross_hatch_spacing_light_spin.setValue(
            self.processing_config.cross_hatch_line_spacing_light
        )
        self.cross_hatch_spacing_light_spin.setSuffix(" mm")
        self.cross_hatch_spacing_light_spin.setToolTip(
            "Spacing between lines in light areas"
        )
        light_spacing_layout.addWidget(self.cross_hatch_spacing_light_spin)
        cross_hatch_layout.addLayout(light_spacing_layout)

        # Segment max length
        seg_max_layout = QHBoxLayout()
        seg_max_layout.addWidget(QLabel("Segment Max Length:"))
        self.cross_hatch_seg_max_spin = QDoubleSpinBox()
        self.cross_hatch_seg_max_spin.setRange(5.0, 100.0)
        self.cross_hatch_seg_max_spin.setSingleStep(5.0)
        self.cross_hatch_seg_max_spin.setValue(
            self.processing_config.cross_hatch_segment_max_length
        )
        self.cross_hatch_seg_max_spin.setSuffix(" mm")
        self.cross_hatch_seg_max_spin.setToolTip(
            "Max segment length in dark areas"
        )
        seg_max_layout.addWidget(self.cross_hatch_seg_max_spin)
        cross_hatch_layout.addLayout(seg_max_layout)

        # Segment min length
        seg_min_layout = QHBoxLayout()
        seg_min_layout.addWidget(QLabel("Segment Min Length:"))
        self.cross_hatch_seg_min_spin = QDoubleSpinBox()
        self.cross_hatch_seg_min_spin.setRange(1.0, 50.0)
        self.cross_hatch_seg_min_spin.setSingleStep(1.0)
        self.cross_hatch_seg_min_spin.setValue(
            self.processing_config.cross_hatch_segment_min_length
        )
        self.cross_hatch_seg_min_spin.setSuffix(" mm")
        self.cross_hatch_seg_min_spin.setToolTip(
            "Min segment length in light areas"
        )
        seg_min_layout.addWidget(self.cross_hatch_seg_min_spin)
        cross_hatch_layout.addLayout(seg_min_layout)

        # Segment gap
        seg_gap_layout = QHBoxLayout()
        seg_gap_layout.addWidget(QLabel("Segment Gap:"))
        self.cross_hatch_seg_gap_spin = QDoubleSpinBox()
        self.cross_hatch_seg_gap_spin.setRange(0.5, 20.0)
        self.cross_hatch_seg_gap_spin.setSingleStep(0.5)
        self.cross_hatch_seg_gap_spin.setValue(
            self.processing_config.cross_hatch_segment_gap
        )
        self.cross_hatch_seg_gap_spin.setSuffix(" mm")
        self.cross_hatch_seg_gap_spin.setToolTip("Gap between segments")
        seg_gap_layout.addWidget(self.cross_hatch_seg_gap_spin)
        cross_hatch_layout.addLayout(seg_gap_layout)

        self.cross_hatch_controls_widget.setLayout(cross_hatch_layout)
        self.style_settings_layout.addWidget(self.cross_hatch_controls_widget)

    def _update_style_controls(self, style_index: int):
        """Show/hide controls based on selected render style."""
        # Hide all control groups
        self.stipple_controls_widget.setVisible(False)
        self.hatching_controls_widget.setVisible(False)
        self.cross_hatch_controls_widget.setVisible(False)

        style_widgets = {
            RenderStyle.STIPPLES: self.stipple_controls_widget,
            RenderStyle.HATCHING: self.hatching_controls_widget,
            RenderStyle.CROSS_HATCH: self.cross_hatch_controls_widget,
        }

        # Show controls for selected style
        style = [style for style in RenderStyle][style_index]
        if style in style_widgets:
            style_widgets[style].setVisible(True)

    def _create_action_buttons(self, parent_layout: QVBoxLayout):
        """Create main action buttons."""
        btn_layout = QHBoxLayout()

        self.process_btn = QPushButton("Process Image")
        self.process_btn.setEnabled(False)
        self.process_btn.setToolTip("Vectorize image with current settings")
        btn_layout.addWidget(self.process_btn)

        parent_layout.addLayout(btn_layout)

        # Second row of buttons
        preview_layout = QHBoxLayout()

        self.preview_btn = QPushButton("Preview in Simulation")
        self.preview_btn.setEnabled(False)
        self.preview_btn.setToolTip("Show paths in simulation canvas")
        preview_layout.addWidget(self.preview_btn)

        self.add_queue_btn = QPushButton("Add to Queue")
        self.add_queue_btn.setEnabled(False)
        self.add_queue_btn.setToolTip("Add plotter commands to queue")
        preview_layout.addWidget(self.add_queue_btn)

        parent_layout.addLayout(preview_layout)

    def _create_status_area(self, parent_layout: QVBoxLayout):
        """Create progress bar and status display."""
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        parent_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        parent_layout.addWidget(self.status_label)

    def _connect_signals(self):
        """Connect internal signals to handlers."""
        self.browse_btn.clicked.connect(self._on_browse_clicked)
        self.num_colors_slider.valueChanged.connect(self._on_colors_changed)
        self.quant_method_combo.currentIndexChanged.connect(
            self._on_method_changed
        )
        self.render_style_combo.currentIndexChanged.connect(
            self._on_render_style_changed
        )
        self.process_btn.clicked.connect(self._on_process_clicked)
        self.preview_btn.clicked.connect(self._on_preview_clicked)
        self.add_queue_btn.clicked.connect(self._on_add_queue_clicked)

        # Connect stipple controls
        self.stipple_density_slider.valueChanged.connect(
            lambda v: self._update_stipple_density(v)
        )
        self.stipple_max_radius_spin.valueChanged.connect(
            lambda v: setattr(self.processing_config, "stipple_max_radius", v)
        )
        self.stipple_min_radius_spin.valueChanged.connect(
            lambda v: setattr(self.processing_config, "stipple_min_radius", v)
        )
        self.stipple_points_spin.valueChanged.connect(
            lambda v: setattr(
                self.processing_config, "stipple_points_per_circle", v
            )
        )
        self.stipple_invert_check.toggled.connect(
            lambda checked: setattr(
                self.processing_config, "stipple_invert", checked
            )
        )

        # Connect hatching controls
        self.hatching_spacing_dark_spin.valueChanged.connect(
            lambda v: setattr(
                self.processing_config, "hatching_line_spacing_dark", v
            )
        )
        self.hatching_spacing_light_spin.valueChanged.connect(
            lambda v: setattr(
                self.processing_config, "hatching_line_spacing_light", v
            )
        )
        self.hatching_angle_slider.valueChanged.connect(
            lambda v: self._update_hatching_angle(v)
        )
        self.hatching_seg_max_spin.valueChanged.connect(
            lambda v: setattr(
                self.processing_config, "hatching_segment_max_length", v
            )
        )
        self.hatching_seg_min_spin.valueChanged.connect(
            lambda v: setattr(
                self.processing_config, "hatching_segment_min_length", v
            )
        )
        self.hatching_seg_gap_spin.valueChanged.connect(
            lambda v: setattr(
                self.processing_config, "hatching_segment_gap", v
            )
        )

        # Connect cross-hatch controls
        self.cross_hatch_max_angles_spin.valueChanged.connect(
            lambda v: setattr(
                self.processing_config, "cross_hatch_max_angles", v
            )
        )
        self.cross_hatch_base_angle_slider.valueChanged.connect(
            lambda v: self._update_cross_hatch_base_angle(v)
        )
        self.cross_hatch_spacing_dark_spin.valueChanged.connect(
            lambda v: setattr(
                self.processing_config, "cross_hatch_line_spacing_dark", v
            )
        )
        self.cross_hatch_spacing_light_spin.valueChanged.connect(
            lambda v: setattr(
                self.processing_config, "cross_hatch_line_spacing_light", v
            )
        )
        self.cross_hatch_seg_max_spin.valueChanged.connect(
            lambda v: setattr(
                self.processing_config, "cross_hatch_segment_max_length", v
            )
        )
        self.cross_hatch_seg_min_spin.valueChanged.connect(
            lambda v: setattr(
                self.processing_config, "cross_hatch_segment_min_length", v
            )
        )
        self.cross_hatch_seg_gap_spin.valueChanged.connect(
            lambda v: setattr(
                self.processing_config, "cross_hatch_segment_gap", v
            )
        )

    # === Event Handlers ===

    def _on_browse_clicked(self):
        """Handle browse button click."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.tiff);;All Files (*)",
        )
        if file_path:
            self._load_image(file_path)

    def _load_image(self, file_path: str):
        """Load and display image preview."""
        self.current_image_path = file_path

        # Update label
        file_name = Path(file_path).name
        self.file_path_label.setText(f"Selected: {file_name}")

        # Load and display preview
        try:
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                # Scale to fit preview area
                scaled = pixmap.scaled(
                    400,
                    300,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.preview_label.setPixmap(scaled)

                # Enable process button
                self.process_btn.setEnabled(True)
                self.status_label.setText("Image loaded. Ready to process.")
            else:
                self.status_label.setText("Failed to load image preview.")
        except Exception as e:
            self.status_label.setText(f"Error loading preview: {e}")

    def _on_colors_changed(self, value: int):
        """Update color count label and config."""
        self.num_colors_label.setText(str(value))
        self.processing_config.num_colors = value

    def _on_speckle_changed(self, value: int):
        """Update speckle filter config."""
        self.processing_config.filter_speckle = value

    def _on_method_changed(self, index: int):
        """Update quantization method."""
        methods = ["kmeans", "median_cut", "octree"]
        self.processing_config.quantization_method = methods[index]

    def _on_render_style_changed(self, index: int):
        """Update render style and show appropriate controls."""
        # Update config
        self.processing_config.render_style = [style for style in RenderStyle][
            index
        ]
        # Update visible controls
        self._update_style_controls(index)

    def _update_stipple_density(self, value: int):
        """Update stipple density config and label."""
        density = value / 100.0
        self.processing_config.stipple_density = density
        self.stipple_density_label.setText(f"{density:.2f}")

    def _update_hatching_angle(self, value: int):
        """Update hatching angle config and label."""
        self.processing_config.hatching_angle = float(value)
        self.hatching_angle_label.setText(f"{value}°")

    def _update_cross_hatch_base_angle(self, value: int):
        """Update cross-hatch base angle config and label."""
        self.processing_config.cross_hatch_base_angle = float(value)
        self.cross_hatch_base_angle_label.setText(f"{value}°")

    def _on_process_clicked(self):
        """Start image processing in background thread."""
        if not self.current_image_path:
            return

        # Disable buttons during processing
        self.process_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.preview_btn.setEnabled(False)
        self.add_queue_btn.setEnabled(False)

        # Show progress
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.status_label.setText("Processing image...")

        # Start background thread
        self.processing_thread = ProcessingThread(
            self.current_image_path,
            self.machine_config,
            self.processing_config,
        )
        self.processing_thread.finished.connect(self._on_processing_finished)
        self.processing_thread.error.connect(self._on_processing_error)
        self.processing_thread.progress.connect(self.progress_bar.setValue)
        self.processing_thread.start()

    def _on_processing_finished(self, result: ProcessedImage):
        """Handle completed image processing."""
        self.processed_result = result

        # Hide progress
        self.progress_bar.setVisible(False)

        # Re-enable buttons
        self.process_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.preview_btn.setEnabled(True)
        self.add_queue_btn.setEnabled(True)

        # Update status
        path_count = len(result.paths)
        total_length = result.total_path_length
        cmd_count = result.command_count
        self.status_label.setText(
            f"Success! {path_count} paths, {cmd_count} commands, "
            f"{total_length:.1f}mm total length"
        )

        # Emit signal
        self.processing_complete.emit(result)

    def _on_processing_error(self, error_msg: str):
        """Handle processing error."""
        # Hide progress
        self.progress_bar.setVisible(False)

        # Re-enable buttons
        self.process_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)

        # format error message
        pretty_msg = error_msg.replace("\n", " ").strip()

        # Show error
        self.status_label.setText(f"Error: {pretty_msg}")

    def _on_preview_clicked(self):
        """Request preview in simulation canvas."""
        if self.processed_result:
            self.preview_requested.emit(self.processed_result)
            self.status_label.setText("Preview sent to simulation canvas")

    def _on_add_queue_clicked(self):
        """Add generated commands to queue."""
        if not self.processed_result:
            return

        # Convert paths to commands
        converter = PathToCommandsConverter(self.machine_config)
        commands = converter.paths_to_commands(
            self.processed_result.paths,
            processing_style=self.processed_result.render_style,
            include_color=True,
            add_home_start=True,
            add_home_end=True,
        )

        # Save commands to file (for debugging)
        with open("debug_commands.txt", "w") as f:
            for cmd in commands:
                f.write(cmd + "\n")

        # Validate commands
        valid, errors = converter.validate_commands(commands)
        if not valid:
            error_text = "\n".join(errors[:5])  # Show first 5 errors
            self.status_label.setText(f"Validation errors:\n{error_text}")
            return

        # Emit signal with commands
        self.add_to_queue_requested.emit(commands)

        # Estimate time
        time_s = converter.estimate_execution_time(commands)
        time_m = time_s / 60
        self.status_label.setText(
            f"Added {len(commands)} commands to queue "
            f"(est. {time_m:.1f} minutes)"
        )

    # === Public Methods ===

    def update_machine_config(self, config: MachineConfig):
        """Update machine configuration (affects scaling)."""
        self.machine_config = config
        # Re-process if image already loaded
        if self.processed_result and self.current_image_path:
            self._on_process_clicked()
