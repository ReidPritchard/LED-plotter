"""Image processing pipeline for photo-to-plotter conversion.

AIDEV-NOTE: This module handles the complete pipeline from photograph
to plotter paths. Color quantization is critical for reducing the
number of distinct paths while preserving visual fidelity.
"""

import io
import math
import re
from pathlib import Path

import numpy as np
from PIL import Image
from sklearn.cluster import KMeans

from models import (
    ColoredPath,
    ImageProcessingConfig,
    MachineConfig,
    ProcessedImage,
)

# Import vtracer and svgpathtools - these may not be installed yet
try:
    import vtracer
except ImportError:
    vtracer = None  # type: ignore[assignment]

try:
    import svgpathtools
except ImportError:
    svgpathtools = None  # type: ignore[assignment]


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
    ) -> tuple[Image.Image, list[tuple[int, int, int]]]:
        """Reduce image to a limited color palette.

        Args:
            image: Input image (RGBA)
            num_colors: Target number of colors (4-32),
                uses config default if None
            method: Quantization method, uses config default if None

        Returns:
            Tuple of (quantized image in RGB mode, palette list)

        AIDEV-NOTE: K-means provides best results for photographs but is
        slower. Median cut is faster for simpler images.
        """
        num_colors = num_colors or self.processing_config.num_colors
        method = method or self.processing_config.quantization_method

        # Convert to RGB (drop alpha for color clustering)
        rgb_image = image.convert("RGB")

        if method == "kmeans":
            return self._quantize_kmeans(rgb_image, num_colors)
        elif method == "median_cut":
            return self._quantize_pillow(
                rgb_image, num_colors, method=Image.Quantize.MEDIANCUT
            )
        elif method == "octree":
            return self._quantize_pillow(
                rgb_image, num_colors, method=Image.Quantize.FASTOCTREE
            )
        else:
            # Default to kmeans
            return self._quantize_kmeans(rgb_image, num_colors)

    def _quantize_kmeans(
        self,
        image: Image.Image,
        num_colors: int,
    ) -> tuple[Image.Image, list[tuple[int, int, int]]]:
        """K-means color quantization implementation.

        AIDEV-NOTE: More accurate than PIL's built-in quantization for
        photographs. Uses scikit-learn KMeans clustering.
        """
        # Convert to numpy array
        img_array = np.array(image)
        original_shape = img_array.shape
        pixels = img_array.reshape(-1, 3).astype(np.float64)

        # Fit KMeans
        kmeans = KMeans(n_clusters=num_colors, random_state=42, n_init=10)
        kmeans.fit(pixels)

        # Get cluster centers as palette
        centers = kmeans.cluster_centers_.astype(np.uint8)
        palette = [tuple(int(c) for c in color) for color in centers]

        # Assign each pixel to nearest cluster
        labels = kmeans.labels_
        quantized_pixels = centers[labels]
        quantized_array = quantized_pixels.reshape(original_shape).astype(
            np.uint8
        )

        # Convert back to PIL Image
        quantized_image = Image.fromarray(quantized_array, mode="RGB")

        return quantized_image, palette

    def _quantize_pillow(
        self,
        image: Image.Image,
        num_colors: int,
        method: Image.Quantize,
    ) -> tuple[Image.Image, list[tuple[int, int, int]]]:
        """Pillow-based color quantization."""
        # Quantize returns a palette image
        quantized = image.quantize(colors=num_colors, method=method)

        # Extract palette
        palette_data = quantized.getpalette()
        if palette_data is None:
            palette = [(128, 128, 128)]  # Fallback gray
        else:
            palette = [
                (palette_data[i], palette_data[i + 1], palette_data[i + 2])
                for i in range(0, num_colors * 3, 3)
            ]

        # Convert back to RGB
        rgb_image = quantized.convert("RGB")

        return rgb_image, palette

    def vectorize_image(self, image: Image.Image) -> str:
        """Convert raster image to SVG using VTracer.

        Args:
            image: Quantized PIL Image (RGB mode)

        Returns:
            SVG string content

        Raises:
            RuntimeError: If vtracer is not available

        AIDEV-NOTE: VTracer handles the actual raster-to-vector conversion.
        We pre-quantize colors to control the number of output regions.
        """
        if vtracer is None:
            raise RuntimeError("vtracer is not installed. Run: pixi install")

        # Convert PIL image to bytes
        img_bytes = io.BytesIO()
        print("Converting image to PNG bytes for vtracer...")
        image.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        # Use vtracer to convert
        print("Running vtracer for vectorization...")
        svg_content = vtracer.convert_raw_image_to_svg(
            img_bytes.read(),
            img_format="png",
            colormode="color",
            filter_speckle=self.processing_config.filter_speckle,
            color_precision=self.processing_config.color_precision,
            corner_threshold=60,
            length_threshold=4.0,
            max_iterations=10,
            splice_threshold=45,
            path_precision=3,
        )

        print("Vectorization complete.")

        # for debug: save SVG to file
        with open("debug_svg_output.svg", "w") as f:
            f.write(svg_content)

        return svg_content

    def extract_paths(self, svg_content: str) -> list[ColoredPath]:
        """Parse SVG and extract paths with colors.

        Args:
            svg_content: SVG string from vectorization

        Returns:
            List of ColoredPath objects with points in pixel coordinates

        AIDEV-NOTE: Uses svgpathtools to parse SVG paths. Complex numbers
        represent coordinates (real=x, imag=y).
        """
        if svgpathtools is None:
            raise RuntimeError(
                "svgpathtools is not installed. Run: pixi install"
            )

        # Parse SVG from string
        paths, attributes = svgpathtools.svg2paths(
            io.StringIO(svg_content), False
        )

        print(f"Found {len(paths)} paths in SVG.")

        colored_paths = []
        for path, attrs in zip(paths, attributes):
            if (
                path is None
                or attrs is None
                or path.length() is None
                or path.length() <= 1  # Skip very short paths
            ):
                continue

            # Extract fill color
            color = self._parse_color(attrs)
            if color is None:
                continue  # Skip paths with no fill (outlines only)

            # Sample points along path
            print(f"Sampling points for path with color {color}...")
            points = self._sample_path_points(path)
            if len(points) < 2:
                continue

            # Check if path is closed
            is_closed = path.isclosed() if hasattr(path, "isclosed") else False

            print(f"Extracted {len(points)} points for path.")

            new_colored_path = ColoredPath(
                points=points,
                color=color,
                is_closed=is_closed,
            )
            print(
                f"Added colored path with color {color} and "
                f"{len(points)} points."
            )

            colored_paths.append(new_colored_path)

        print(f"Extracted {len(colored_paths)} colored paths from SVG.")

        return colored_paths

    def _parse_color(self, attrs: dict) -> tuple[int, int, int] | None:
        """Parse color from SVG path attributes."""

        # Check fill attribute
        fill = attrs.get("fill", "")

        # Handle style attribute
        if not fill and "style" in attrs:
            style = attrs["style"]
            match = re.search(r"fill:\s*([^;]+)", style)
            if match:
                fill = match.group(1).strip()

        if not fill or fill == "none":
            return None

        # Parse hex color
        if fill.startswith("#"):
            print(f"Parsing hex color: {fill}")
            if len(fill) == 7:  # #RRGGBB
                r = int(fill[1:3], 16)
                g = int(fill[3:5], 16)
                b = int(fill[5:7], 16)
                return (r, g, b)
            elif len(fill) == 4:  # #RGB
                r = int(fill[1] * 2, 16)
                g = int(fill[2] * 2, 16)
                b = int(fill[3] * 2, 16)
                return (r, g, b)

        # Parse rgb() format
        match = re.match(
            r"rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", fill
        )
        if match:
            return (
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3)),
            )

        return None

    def _sample_path_points(self, path) -> list[tuple[float, float]]:
        """Sample points along an SVG path.

        AIDEV-NOTE: svgpathtools uses complex numbers for coordinates.
        Real part = x, imaginary part = y.
        """
        points = []
        path_length = path.length()

        # Calculate number of samples based on path length
        # More points for longer paths, but cap to avoid too many commands
        # num_samples = max(10, min(200, int(path_length / 2)))
        num_samples = max(10, int(path_length / 1))

        for i in range(num_samples + 1):
            t = i / num_samples
            try:
                point = path.point(t)
                # Complex number: real=x, imag=y
                x = point.real
                y = point.imag
                points.append((x, y))
            except Exception:
                continue

        return points

    def scale_paths_to_machine(
        self,
        paths: list[ColoredPath],
        image_width: int,
        image_height: int,
    ) -> tuple[list[ColoredPath], float, float, float]:
        """Scale paths from pixel coordinates to machine mm coordinates.

        Args:
            paths: List of paths in pixel coordinates
            image_width: Original image width in pixels
            image_height: Original image height in pixels

        Returns:
            Tuple of (scaled paths, scale_factor, offset_x, offset_y)

        AIDEV-NOTE: Paths are scaled to fit within safe margins while
        maintaining aspect ratio. Centered in drawing area.
        """
        margin = self.machine_config.safe_margin
        safe_width = self.machine_config.width - 2 * margin
        safe_height = self.machine_config.height - 2 * margin

        # Calculate scale factor (maintain aspect ratio)
        scale_x = safe_width / image_width
        scale_y = safe_height / image_height
        scale = min(scale_x, scale_y)

        # Calculate centering offsets
        scaled_width = image_width * scale
        scaled_height = image_height * scale
        offset_x = margin + (safe_width - scaled_width) / 2
        offset_y = margin + (safe_height - scaled_height) / 2

        # Scale all paths
        scaled_paths = []
        for path in paths:
            scaled_points = [
                (x * scale + offset_x, y * scale + offset_y)
                for x, y in path.points
            ]
            scaled_paths.append(
                ColoredPath(
                    points=scaled_points,
                    color=path.color,
                    is_closed=path.is_closed,
                )
            )

        return scaled_paths, scale, offset_x, offset_y

    def simplify_paths(
        self,
        paths: list[ColoredPath],
        tolerance: float | None = None,
    ) -> list[ColoredPath]:
        """Simplify paths using Douglas-Peucker algorithm.

        AIDEV-NOTE: Reduces number of points while preserving shape.
        Critical for reducing command count and execution time.
        """
        tolerance = tolerance or self.processing_config.simplify_tolerance

        simplified_paths = []
        for path in paths:
            simplified_points = douglas_peucker(path.points, tolerance)

            # Only keep paths with at least 2 points
            if len(simplified_points) >= 2:
                simplified_paths.append(
                    ColoredPath(
                        points=simplified_points,
                        color=path.color,
                        is_closed=path.is_closed,
                    )
                )

        return simplified_paths

    def calculate_total_length(self, paths: list[ColoredPath]) -> float:
        """Calculate total path length in mm."""
        total = 0.0
        for path in paths:
            for i in range(1, len(path.points)):
                x1, y1 = path.points[i - 1]
                x2, y2 = path.points[i]
                total += math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        return total

    def count_commands(self, paths: list[ColoredPath]) -> int:
        """Count total number of commands that will be generated."""
        return sum(len(path.points) for path in paths)

    def process(self, file_path: str | Path) -> ProcessedImage:
        """Execute complete image processing pipeline.

        Args:
            file_path: Path to input image

        Returns:
            ProcessedImage with all extracted paths and metadata
        """
        # Load image
        print("Loading image...")
        image = self.load_image(file_path)
        original_width, original_height = image.size

        # # Quantize colors
        # print("Quantizing colors...")
        # quantized, palette = self.quantize_colors(image)

        # # Vectorize
        # print("Vectorizing image...")
        # svg_content = self.vectorize_image(quantized)

        # # Extract paths
        # print("Extracting paths...")
        # paths = self.extract_paths(svg_content)

        # Rather than the above approach, we will go about this differently
        # Options: 



        # Scale to machine coordinates
        print("Scaling paths to machine coordinates...")
        paths, scale, offset_x, offset_y = self.scale_paths_to_machine(
            paths, original_width, original_height
        )

        # Simplify paths
        print("Simplifying paths...")
        paths = self.simplify_paths(paths)

        # Calculate statistics
        print("Calculating statistics...")
        total_length = self.calculate_total_length(paths)
        command_count = self.count_commands(paths)

        return ProcessedImage(
            paths=paths,
            palette=palette,
            scale_factor=scale,
            offset_x=offset_x,
            offset_y=offset_y,
            original_width=original_width,
            original_height=original_height,
            total_path_length=total_length,
            command_count=command_count,
        )


def douglas_peucker(
    points: list[tuple[float, float]],
    tolerance: float,
) -> list[tuple[float, float]]:
    """Douglas-Peucker path simplification algorithm.

    AIDEV-NOTE: Reduces point count while maintaining shape within
    tolerance. Essential for reducing plotter command count.

    Args:
        points: List of (x, y) coordinates
        tolerance: Maximum distance tolerance in mm

    Returns:
        Simplified list of points
    """
    if len(points) <= 2:
        return points

    # Find the point with the maximum distance from the line
    # between the first and last points
    start = points[0]
    end = points[-1]

    max_dist = 0.0
    max_idx = 0

    for i in range(1, len(points) - 1):
        dist = perpendicular_distance(points[i], start, end)
        if dist > max_dist:
            max_dist = dist
            max_idx = i

    # If max distance is greater than tolerance, recursively simplify
    if max_dist > tolerance:
        # Recursive call
        left = douglas_peucker(points[: max_idx + 1], tolerance)
        right = douglas_peucker(points[max_idx:], tolerance)

        # Combine results (avoiding duplicate at junction)
        return left[:-1] + right
    else:
        # All points between start and end can be removed
        return [start, end]


def perpendicular_distance(
    point: tuple[float, float],
    line_start: tuple[float, float],
    line_end: tuple[float, float],
) -> float:
    """Calculate perpendicular distance from point to line segment."""
    x, y = point
    x1, y1 = line_start
    x2, y2 = line_end

    # Handle case where line is actually a point
    dx = x2 - x1
    dy = y2 - y1
    line_length_sq = dx * dx + dy * dy

    if line_length_sq == 0:
        return math.sqrt((x - x1) ** 2 + (y - y1) ** 2)

    # Calculate perpendicular distance using cross product formula
    # |AB × AC| / |AB|
    numerator = abs(dy * x - dx * y + x2 * y1 - y2 * x1)
    denominator = math.sqrt(line_length_sq)

    return numerator / denominator
