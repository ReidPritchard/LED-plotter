"""Main image processor orchestrating the complete pipeline.

AIDEV-NOTE: This module handles the complete pipeline from photograph
to plotter paths. Uses modular components for quantization, rendering,
and path extraction.
"""

from pathlib import Path

from PIL import Image

from models import (
    ImageProcessingConfig,
    MachineConfig,
    ProcessedImage,
    RenderStyle,
)

from .quantization import quantize_colors
from .rendering import render_hatching, render_stipples
from .svg_parser import colored_paths_to_svg, extract_paths
from .utils import (
    calculate_total_length,
    count_commands,
    scale_image_to_machine,
    scale_paths_to_machine,
)


class ImageProcessor:
    """Processes images into colored paths suitable for plotting."""

    def __init__(
        self,
        machine_config: MachineConfig,
        processing_config: ImageProcessingConfig | None = None,
    ):
        self.machine_config = machine_config
        self.processing_config = processing_config or ImageProcessingConfig()

    def load_image(self, file_path: str | Path) -> Image.Image:
        """Load and validate an image file.

        Args:
            file_path: Path to image file (PNG, JPG, etc.)

        Returns:
            PIL Image in RGBA mode

        Raises:
            ValueError: If file cannot be loaded or is invalid
        """
        try:
            image = Image.open(file_path)
            # AIDEV-NOTE: Always convert to RGBA for consistent processing
            if image.mode != "RGBA":
                image = image.convert("RGBA")
            return image
        except Exception as e:
            raise ValueError(f"Failed to load image: {e}") from e

    def quantize_colors(
        self,
        image: Image.Image,
        num_colors: int | None = None,
        method: str | None = None,
    ) -> "tuple[Image.Image, list[tuple[int, int, int]]]":
        """Reduce image to a limited color palette.

        Args:
            image: Input image (RGBA)
            num_colors: Target number of colors (4-32),
                uses config default if None
            method: Quantization method, uses config default if None

        Returns:
            Tuple of (quantized image in RGB mode, palette list)
        """
        num_colors = num_colors or self.processing_config.num_colors
        method = method or self.processing_config.quantization_method
        return quantize_colors(image, num_colors, method)

    def extract_paths(self, svg_content: str):
        """Parse SVG and extract paths with colors.

        Args:
            svg_content: SVG string from vectorization

        Returns:
            List of ColoredPath objects with points in pixel coordinates
        """
        return extract_paths(svg_content)

    def scale_paths_to_machine(
        self,
        paths,
        image_width: int,
        image_height: int,
    ):
        """Scale paths from pixel coordinates to machine mm coordinates.

        Args:
            paths: List of paths in pixel coordinates
            image_width: Original image width in pixels
            image_height: Original image height in pixels

        Returns:
            Tuple of (scaled paths, scale_factor, offset_x, offset_y)
        """
        return scale_paths_to_machine(
            paths, image_width, image_height, self.machine_config
        )

    def calculate_total_length(self, paths) -> float:
        """Calculate total path length in mm."""
        return calculate_total_length(paths)

    def count_commands(self, paths) -> int:
        """Count total number of commands that will be generated."""
        return count_commands(paths)

    def process(self, file_path: str | Path) -> ProcessedImage:
        """Execute complete image processing pipeline.

        Args:
            file_path: Path to input image

        Returns:
            ProcessedImage with all extracted paths and metadata
        """
        print("Starting image processing pipeline...")

        print("Loading image...")
        # Load image
        image = self.load_image(file_path)
        orig_width, orig_height = image.size
        print(f"Loaded image with size: {orig_width}x{orig_height} pixels.")

        print("Scaling image to fit machine...")
        # Scale down image to both fit machine and reduce processing load
        scaled_image, scale_factor, offset_x, offset_y = scale_image_to_machine(
            image, self.machine_config
        )
        print(
            f"Scaled image to {scaled_image.size[0]}x{scaled_image.size[1]} "
            f"pixels for machine fit."
        )

        # Check rendering style
        style = self.processing_config.render_style
        if style == RenderStyle.STIPPLES:
            print("Rendering stipple style...")
            paths = render_stipples(
                scaled_image,
                offset_x,
                offset_y,
                self.processing_config,
                invert=self.processing_config.stipple_invert,
            )
        elif style == RenderStyle.HATCHING:
            print("Rendering hatching style...")
            paths = render_hatching(
                scaled_image, offset_x, offset_y, self.processing_config
            )
        else:
            # just error for now
            raise NotImplementedError(
                f"Render style {style} not implemented in this snippet."
            )

        # DEBUG: Save intermediate SVG for inspection
        debug_svg = colored_paths_to_svg(
            paths,
            svg_width=int(self.machine_config.width),
            svg_height=int(self.machine_config.height),
        )
        with open("debug_output.svg", "w") as f:
            f.write(debug_svg)

        print("Saved debug_output.svg for inspection.")

        # If the style is stipple, the commands should be to move to the
        # center of each stipple and display it's color (brightness based on
        # the stipple size)

        # Return processed image data
        print("Image processing complete.")
        print(f"Total paths extracted: {len(paths)}")
        total_length = self.calculate_total_length(paths)
        print(f"Total path length: {total_length:.2f} mm")
        command_count = self.count_commands(paths)
        print(f"Total commands to be generated: {command_count}")

        return ProcessedImage(
            paths=paths,
            palette=[],
            render_style=style,
            scale_factor=scale_factor,
            offset_x=offset_x,
            offset_y=offset_y,
            original_width=orig_width,
            original_height=orig_height,
            total_path_length=total_length,
            command_count=command_count,
        )
