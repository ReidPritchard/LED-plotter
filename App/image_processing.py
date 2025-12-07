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
    RenderStyle,
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

    def _scale_image_to_machine(
        self, image: Image.Image
    ) -> tuple[Image.Image, float, float, float]:
        """Scale image to fit within machine bounds while maintaining aspect ratio.

        Args:
            image: Input PIL image

        Returns:
            Tuple of (scaled_image, scale_factor, offset_x, offset_y)
            where offsets are in mm for centering in machine space

        AIDEV-NOTE: This scales the image so that when we sample pixels,
        pixel coordinates map directly to mm in machine space.
        """
        margin = self.machine_config.safe_margin
        safe_width = self.machine_config.width - 2 * margin
        safe_height = self.machine_config.height - 2 * margin

        orig_width, orig_height = image.size

        # Calculate scale to fit within safe bounds
        scale_x = safe_width / orig_width
        scale_y = safe_height / orig_height
        scale = min(scale_x, scale_y)

        # New dimensions in mm (and pixels, since 1 pixel = 1 mm after scaling)
        new_width = int(orig_width * scale)
        new_height = int(orig_height * scale)

        # Resize image
        scaled_image = image.resize(
            (new_width, new_height), Image.Resampling.LANCZOS
        )

        # Calculate centering offsets in mm
        offset_x = margin + (safe_width - new_width) / 2
        offset_y = margin + (safe_height - new_height) / 2

        return scaled_image, scale, offset_x, offset_y

    def _get_brightness(self, image: Image.Image, x: int, y: int) -> float:
        """Get brightness (0-1) at a pixel location.

        Args:
            image: Grayscale PIL image
            x: X coordinate
            y: Y coordinate

        Returns:
            Brightness value from 0 (black) to 1 (white)
        """
        width, height = image.size
        if 0 <= x < width and 0 <= y < height:
            pixel = image.getpixel((x, y))
            return pixel / 255.0
        return 1.0  # Default to white (no drawing) for out of bounds

    def _get_color(
        self, image: Image.Image, x: int, y: int
    ) -> tuple[int, int, int]:
        """Get RGB color at a pixel location.

        Args:
            image: RGB PIL image
            x: X coordinate
            y: Y coordinate

        Returns:
            RGB tuple (0-255 each channel)

        AIDEV-NOTE: Used for sampling quantized colors to assign to paths.
        Returns white for out-of-bounds pixels.
        """
        width, height = image.size
        if 0 <= x < width and 0 <= y < height:
            pixel = image.getpixel((x, y))
            if isinstance(pixel, tuple):
                return pixel[:3]  # RGB only (drop alpha if present)
            else:
                # Grayscale pixel, convert to RGB tuple
                return (pixel, pixel, pixel)
        return (255, 255, 255)  # Default to white for out of bounds

    def _render_sine_waves(
        self,
        grayscale_image: Image.Image,
        color_image: Image.Image,
        offset_x: float,
        offset_y: float,
    ) -> list[ColoredPath]:
        """Render image as horizontal sine waves with brightness-based modulation.

        Style 1: Starting from the left, draw sine waves that increase
        in frequency and amplitude based on image darkness. Creates separate
        paths for each contiguous color region.

        Args:
            grayscale_image: Grayscale PIL image for brightness sampling
            color_image: Quantized RGB PIL image for color sampling
            offset_x: X offset in mm for centering
            offset_y: Y offset in mm for centering

        Returns:
            List of ColoredPath objects representing the sine waves

        AIDEV-NOTE: Darker areas produce higher amplitude and frequency waves.
        Paths are split when colors change along a scan line, creating
        separate ColoredPath objects for each color segment.
        """
        config = self.processing_config
        width, height = grayscale_image.size

        paths = []
        line_spacing = config.wave_line_spacing
        y = 0.0

        while y < height:
            x = 0.0
            step = 0.5  # Sample every 0.5mm for smooth curves
            current_color = None
            current_points = []

            while x < width:
                # Get brightness at this position (0=black, 1=white)
                brightness = self._get_brightness(
                    grayscale_image, int(x), int(y)
                )
                darkness = 1.0 - brightness  # Invert: dark = high value

                # Sample color from quantized color image
                sampled_color = self._get_color(color_image, int(x), int(y))

                # If color changed, save current path segment and start new one
                if sampled_color != current_color:
                    # Save previous segment if it has enough points
                    if current_points and len(current_points) >= 2:
                        paths.append(
                            ColoredPath(
                                points=current_points,
                                color=current_color,  # type: ignore
                                is_closed=False,
                            )
                        )
                    # Start new segment
                    current_points = []
                    current_color = sampled_color

                # Calculate amplitude and frequency based on darkness
                amplitude = config.wave_min_amplitude + darkness * (
                    config.wave_max_amplitude - config.wave_min_amplitude
                )
                frequency = config.wave_min_frequency + darkness * (
                    config.wave_max_frequency - config.wave_min_frequency
                )

                # Calculate sine wave offset
                wave_y = amplitude * math.sin(2 * math.pi * frequency * x)

                # Convert to machine coordinates
                machine_x = x + offset_x
                machine_y = y + wave_y + offset_y

                current_points.append((machine_x, machine_y))
                x += step

            # Don't forget to save the last segment of the line
            if current_points and len(current_points) >= 2:
                paths.append(
                    ColoredPath(
                        points=current_points,
                        color=current_color,  # type: ignore
                        is_closed=False,
                    )
                )

            y += line_spacing

        return paths

    def _render_stipples(
        self,
        image: Image.Image,
        offset_x: float,
        offset_y: float,
    ) -> list[ColoredPath]:
        """Render image as stipples (dots) based on brightness.

        Style 2: Convert to dots where darker areas have more/larger dots.

        Args:
            image: Grayscale PIL image (scaled to machine size)
            offset_x: X offset in mm for centering
            offset_y: Y offset in mm for centering

        Returns:
            List of ColoredPath objects representing circles/dots

        AIDEV-NOTE: Uses grid-based sampling with jitter. Darker pixels
        produce larger dots. Each dot is a circular path.
        """
        config = self.processing_config
        width, height = image.size

        paths = []
        max_radius = config.stipple_max_radius
        min_radius = config.stipple_min_radius
        grid_size = max_radius * 2.5  # Grid spacing based on max dot size

        y = grid_size / 2
        while y < height:
            x = grid_size / 2
            while x < width:
                brightness = self._get_brightness(image, int(x), int(y))
                darkness = 1.0 - brightness

                # Skip very light areas
                if darkness < 0.1:
                    x += grid_size
                    continue

                # Calculate radius based on darkness
                radius = min_radius + darkness * (max_radius - min_radius)

                # Apply density factor - randomly skip some dots
                if darkness < config.stipple_density:
                    # Use position-based pseudo-random to be deterministic
                    if (int(x * 7 + y * 13) % 100) / 100.0 > darkness:
                        x += grid_size
                        continue

                # Generate circle points
                circle_points = []
                num_points = config.stipple_points_per_circle
                for i in range(num_points + 1):
                    angle = 2 * math.pi * i / num_points
                    cx = x + radius * math.cos(angle) + offset_x
                    cy = y + radius * math.sin(angle) + offset_y
                    circle_points.append((cx, cy))

                if len(circle_points) >= 3:
                    paths.append(
                        ColoredPath(
                            points=circle_points,
                            color=(0, 0, 0),
                            is_closed=True,
                        )
                    )

                x += grid_size
            y += grid_size

        return paths

    def _render_hatching(
        self,
        image: Image.Image,
        offset_x: float,
        offset_y: float,
    ) -> list[ColoredPath]:
        """Render image as hatching lines based on brightness.

        Style 3: Convert to parallel lines where darker areas have
        closer line spacing.

        Args:
            image: Grayscale PIL image (scaled to machine size)
            offset_x: X offset in mm for centering
            offset_y: Y offset in mm for centering

        Returns:
            List of ColoredPath objects representing hatching lines

        AIDEV-NOTE: Lines are drawn at the configured angle. Spacing
        varies based on local brightness - darker = tighter spacing.
        """
        config = self.processing_config
        width, height = image.size

        paths = []
        angle_rad = math.radians(config.hatch_angle)

        # Calculate line direction and perpendicular
        dx = math.cos(angle_rad)
        dy = math.sin(angle_rad)
        # Perpendicular direction for spacing
        px = -dy
        py = dx

        # Calculate the range we need to cover with parallel lines
        # Diagonal of the image gives max distance
        diagonal = math.sqrt(width**2 + height**2)

        # Start position offset (perpendicular to line direction)
        current_offset = -diagonal / 2
        max_offset = diagonal / 2

        while current_offset < max_offset:
            # Sample brightness along this potential line to determine spacing
            # Use the center of the image area this line would cross
            sample_x = width / 2 + current_offset * px
            sample_y = height / 2 + current_offset * py

            brightness = self._get_brightness(
                image, int(sample_x), int(sample_y)
            )
            darkness = 1.0 - brightness

            # Skip very light areas
            if darkness < 0.05:
                current_offset += config.hatch_max_spacing
                continue

            # Calculate spacing based on brightness
            spacing = config.hatch_max_spacing - darkness * (
                config.hatch_max_spacing - config.hatch_min_spacing
            )

            # Find line intersection with image bounds
            # Line passes through point: (width/2 + current_offset * px, height/2 + current_offset * py)
            # Direction: (dx, dy)
            center_x = width / 2 + current_offset * px
            center_y = height / 2 + current_offset * py

            # Find where line enters and exits the image rectangle
            line_points = self._clip_line_to_rect(
                center_x, center_y, dx, dy, 0, 0, width, height
            )

            if line_points and len(line_points) == 2:
                (x1, y1), (x2, y2) = line_points
                # Convert to machine coordinates
                machine_points = [
                    (x1 + offset_x, y1 + offset_y),
                    (x2 + offset_x, y2 + offset_y),
                ]
                paths.append(
                    ColoredPath(
                        points=machine_points,
                        color=(0, 0, 0),
                        is_closed=False,
                    )
                )

            current_offset += spacing

        return paths

    def _clip_line_to_rect(
        self,
        cx: float,
        cy: float,
        dx: float,
        dy: float,
        x_min: float,
        y_min: float,
        x_max: float,
        y_max: float,
    ) -> list[tuple[float, float]] | None:
        """Clip an infinite line to a rectangle using parametric intersection.

        Args:
            cx, cy: Point on the line
            dx, dy: Direction vector of the line
            x_min, y_min, x_max, y_max: Rectangle bounds

        Returns:
            List of two intersection points, or None if line doesn't intersect
        """
        t_min = float("-inf")
        t_max = float("inf")

        # Check intersection with vertical edges
        if abs(dx) > 1e-10:
            t1 = (x_min - cx) / dx
            t2 = (x_max - cx) / dx
            if t1 > t2:
                t1, t2 = t2, t1
            t_min = max(t_min, t1)
            t_max = min(t_max, t2)
        else:
            # Line is vertical
            if cx < x_min or cx > x_max:
                return None

        # Check intersection with horizontal edges
        if abs(dy) > 1e-10:
            t1 = (y_min - cy) / dy
            t2 = (y_max - cy) / dy
            if t1 > t2:
                t1, t2 = t2, t1
            t_min = max(t_min, t1)
            t_max = min(t_max, t2)
        else:
            # Line is horizontal
            if cy < y_min or cy > y_max:
                return None

        if t_min > t_max:
            return None

        # Calculate intersection points
        p1 = (cx + t_min * dx, cy + t_min * dy)
        p2 = (cx + t_max * dx, cy + t_max * dy)

        return [p1, p2]

    def process(self, file_path: str | Path) -> ProcessedImage:
        """Execute complete image processing pipeline.

        Args:
            file_path: Path to input image

        Returns:
            ProcessedImage with all extracted paths and metadata

        AIDEV-NOTE: Pipeline steps:
        1. Load and convert to grayscale
        2. Scale to fit machine bounds (1 pixel = 1 mm)
        3. Render using selected style (sine waves, stipples, or hatching)
        4. Paths are already in machine coordinates after rendering
        """
        # Load image
        print("Loading image...")
        image = self.load_image(file_path)
        original_width, original_height = image.size
        print(
            f"Original image size: {original_width}x{original_height} pixels"
        )

        # Step 1: Scale image to fit within machine bounds while maintaining aspect ratio
        print("Scaling image to machine bounds...")
        scaled_image, scale, offset_x, offset_y = self._scale_image_to_machine(
            image
        )
        scaled_width, scaled_height = scaled_image.size
        print(f"Scaled image size: {scaled_width}x{scaled_height} mm")
        print(
            f"Scale factor: {scale:.4f}, offset: ({offset_x:.1f}, {offset_y:.1f}) mm"
        )

        # Quantize colors to a limited palette
        print(f"Quantizing to {self.processing_config.num_colors} colors...")
        quantized_image, palette = self.quantize_colors(scaled_image)
        print(f"Palette: {palette}")

        # Convert to grayscale for brightness-based rendering
        # (use quantized image for consistency)
        grayscale_image = quantized_image.convert("L")

        # Step 2: Convert to paths using the selected rendering style
        # Currently only sine waves (style 1) is implemented
        style = self.processing_config.render_style
        print(f"Rendering with style: {style.value}")

        if style == RenderStyle.SINE_WAVES:
            # Style 1: Sine waves with brightness-based amplitude/frequency
            # Pass both grayscale (for brightness) and color (for segmentation)
            paths = self._render_sine_waves(
                grayscale_image=grayscale_image,
                color_image=quantized_image,
                offset_x=offset_x,
                offset_y=offset_y,
            )
        elif style == RenderStyle.STIPPLES:
            # Style 2: Not yet implemented
            raise NotImplementedError("Stipple rendering not yet implemented")
        elif style == RenderStyle.HATCHING:
            # Style 3: Not yet implemented
            raise NotImplementedError("Hatching rendering not yet implemented")
        else:
            # Default to sine waves
            paths = self._render_sine_waves(
                grayscale_image, quantized_image, offset_x, offset_y
            )

        # Step 3: Paths are already in machine coordinates (mm)
        # with colors assigned from the quantized palette

        # debug: save paths to SVG with colors
        with open("debug_rendered_paths.svg", "w") as f:
            f.write(
                '<svg xmlns="http://www.w3.org/2000/svg" '
                f'width="{self.machine_config.width}mm" '
                f'height="{self.machine_config.height}mm" '
                'viewBox="0 0 '
                f"{self.machine_config.width} "
                f'{self.machine_config.height}">\n'
            )
            for path in paths:
                path_data = "M " + " L ".join(
                    f"{x:.2f} {y:.2f}" for x, y in path.points
                )
                # Convert RGB tuple to hex color
                r, g, b = path.color
                hex_color = f"#{r:02x}{g:02x}{b:02x}"
                f.write(
                    f'<path d="{path_data}" '
                    f'stroke="{hex_color}" fill="none" stroke-width="0.1"/>\n'
                )
            f.write("</svg>\n")
            print("Saved debug_rendered_paths.svg for inspection.")

        # Step 4: Calculate statistics for the generated paths
        print("Calculating statistics...")
        total_length = self.calculate_total_length(paths)
        command_count = self.count_commands(paths)
        print(f"Total path length: {total_length:.1f} mm")
        print(f"Total commands: {command_count}")

        # Palette already extracted from quantize_colors() above
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
