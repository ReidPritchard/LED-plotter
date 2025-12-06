"""Image import and processing panel for photo-to-plotter workflow."""

from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
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
from models import ImageProcessingConfig, MachineConfig, ProcessedImage
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
            processor = ImageProcessor(self.machine_config, self.processing_config)

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

    def __init__(self, machine_config: MachineConfig, parent: QWidget | None = None):
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
        self.quant_method_combo.addItems([
            "K-Means (Best quality)",
            "Median Cut (Faster)",
            "Octree (Fastest)",
        ])
        method_layout.addWidget(self.quant_method_combo)

        quant_layout.addLayout(method_layout)

        quant_group.setLayout(quant_layout)
        parent_layout.addWidget(quant_group)

    def _create_processing_options(self, parent_layout: QVBoxLayout):
        """Create vectorization options."""
        options_group = QGroupBox("Vectorization Options")
        options_layout = QVBoxLayout()

        # Filter speckle
        speckle_layout = QHBoxLayout()
        speckle_layout.addWidget(QLabel("Min region size:"))
        self.speckle_spin = QSpinBox()
        self.speckle_spin.setRange(1, 20)
        self.speckle_spin.setValue(4)
        self.speckle_spin.setSuffix(" px")
        speckle_layout.addWidget(self.speckle_spin)
        speckle_layout.addStretch()
        options_layout.addLayout(speckle_layout)

        # Path simplification
        simplify_layout = QHBoxLayout()
        simplify_layout.addWidget(QLabel("Path simplification:"))
        self.simplify_slider = QSlider(Qt.Orientation.Horizontal)
        self.simplify_slider.setRange(1, 50)  # 0.1mm to 5.0mm
        self.simplify_slider.setValue(5)  # 0.5mm default
        simplify_layout.addWidget(self.simplify_slider)
        self.simplify_label = QLabel("0.5 mm")
        self.simplify_label.setMinimumWidth(50)
        simplify_layout.addWidget(self.simplify_label)
        options_layout.addLayout(simplify_layout)

        options_group.setLayout(options_layout)
        parent_layout.addWidget(options_group)

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
        self.simplify_slider.valueChanged.connect(self._on_simplify_changed)
        self.speckle_spin.valueChanged.connect(self._on_speckle_changed)
        self.quant_method_combo.currentIndexChanged.connect(self._on_method_changed)
        self.process_btn.clicked.connect(self._on_process_clicked)
        self.preview_btn.clicked.connect(self._on_preview_clicked)
        self.add_queue_btn.clicked.connect(self._on_add_queue_clicked)

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

    def _on_simplify_changed(self, value: int):
        """Update simplification tolerance label and config."""
        tolerance = value / 10.0
        self.simplify_label.setText(f"{tolerance:.1f} mm")
        self.processing_config.simplify_tolerance = tolerance

    def _on_speckle_changed(self, value: int):
        """Update speckle filter config."""
        self.processing_config.filter_speckle = value

    def _on_method_changed(self, index: int):
        """Update quantization method."""
        methods = ["kmeans", "median_cut", "octree"]
        self.processing_config.quantization_method = methods[index]

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

        # Show error
        self.status_label.setText(f"Error: {error_msg}")

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
            include_color=True,
            add_home_start=True,
            add_home_end=True,
        )

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
