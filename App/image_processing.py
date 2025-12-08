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
    ) -> "tuple[Image.Image, list[tuple[int, int, int]]]":
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
    ) -> "tuple[Image.Image, list[tuple[int, int, int]]]":
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
    ) -> "tuple[Image.Image, list[tuple[int, int, int]]]":
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

    def extract_paths(self, svg_content: str) -> "list[ColoredPath]":
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

    def _sample_path_points(self, path) -> "list[tuple[float, float]]":
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
        paths: "list[ColoredPath]",
        image_width: int,
        image_height: int,
    ) -> "tuple[list[ColoredPath], float, float, float]":
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

    def calculate_total_length(self, paths: "list[ColoredPath]") -> float:
        """Calculate total path length in mm."""
        total = 0.0
        for path in paths:
            for i in range(1, len(path.points)):
                x1, y1 = path.points[i - 1]
                x2, y2 = path.points[i]
                total += math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        return total

    def count_commands(self, paths: "list[ColoredPath]") -> int:
        """Count total number of commands that will be generated."""
        return sum(len(path.points) for path in paths)

    def _scale_image_to_machine(
        self, image: Image.Image
    ) -> "tuple[Image.Image, float, float, float]":
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

        # if scale is greater than 1, we don't want to upscale
        if scale > 7.0:
            scale = 7.0

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
            if isinstance(pixel, tuple):
                # RGB image, convert to brightness
                r, g, b = pixel[:3]
                brightness = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
                return brightness
            elif isinstance(pixel, int) or isinstance(pixel, float):
                # Grayscale pixel
                return pixel / 255.0
        return 1.0  # Default to white (no drawing) for out of bounds

    def _get_color(
        self, image: Image.Image, x: int, y: int
    ) -> "tuple[int, int, int]":
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

    def _get_average_color_circle(
        self,
        image: Image.Image,
        center_x: int,
        center_y: int,
        radius: int,
    ) -> "tuple[int, int, int]":
        """Get average RGB color within a circular area.

        Args:
            image: RGB PIL image
            center_x: Center X coordinate
            center_y: Center Y coordinate
            radius: Radius of circle

        Returns:
            Average RGB color tuple (0-255 each channel)

        AIDEV-NOTE: Samples pixels within the circle to compute average.
        """
        width, height = image.size
        r_squared = radius * radius
        total_r = total_g = total_b = count = 0

        for y in range(center_y - radius, center_y + radius + 1):
            for x in range(center_x - radius, center_x + radius + 1):
                if 0 <= x < width and 0 <= y < height:
                    dx = x - center_x
                    dy = y - center_y
                    if dx * dx + dy * dy <= r_squared:
                        pixel = image.getpixel((x, y))
                        if isinstance(pixel, tuple):
                            r, g, b = pixel[:3]
                        else:
                            r = g = b = pixel

                        if r is None or g is None or b is None:
                            continue

                        r = int(r)
                        g = int(g)
                        b = int(b)

                        total_r += r
                        total_g += g
                        total_b += b
                        count += 1

        if count == 0:
            return (255, 255, 255)  # Default to white

        return (
            total_r // count,
            total_g // count,
            total_b // count,
        )

    def _render_stipples(
        self,
        image: Image.Image,
        offset_x: float,
        offset_y: float,
        invert: bool = False,
    ) -> "list[ColoredPath]":
        """Render image as stipples (dots) based on brightness.

        Style 2: Convert to dots where darker areas have more/larger dots.

        Args:
            image: Grayscale PIL image (scaled to machine size)
            offset_x: X offset in mm for centering
            offset_y: Y offset in mm for centering
            invert: More dots in lighter areas if True (correct mapping for LED)

        Returns:
            List of ColoredPath objects representing circles/dots
        """
        config = self.processing_config
        width, height = image.size

        paths = []
        max_radius = config.stipple_max_radius
        min_radius = config.stipple_min_radius
        grid_size = max_radius * 2.5  # Grid spacing based on max dot size

        # Precompute values for efficiency
        num_points = config.stipple_points_per_circle
        get_brightness = self._get_brightness
        get_avg_color = self._get_average_color_circle
        append_path = paths.append
        int_x = int
        int_y = int

        y = grid_size / 2
        while y < height:
            x = grid_size / 2
            while x < width:
                brightness = get_brightness(image, int_x(x), int_y(y))
                darkness = 1.0 - brightness

                if invert:
                    darkness = 1.0 - darkness

                # Skip very light areas
                if darkness < 0.1:
                    x += grid_size
                    continue

                # Calculate radius based on darkness
                radius = min_radius + darkness * (max_radius - min_radius)

                # Apply density factor - randomly skip some dots
                if darkness < config.stipple_density:
                    # Use position-based pseudo-random to be deterministic
                    if (int_x(x * 7 + y * 13) % 100) / 100.0 > darkness:
                        x += grid_size
                        continue

                # Generate circle points using list comprehension
                circle_points = [
                    (
                        x + radius * math.cos(angle) + offset_x,
                        y + radius * math.sin(angle) + offset_y,
                    )
                    for angle in (
                        2 * math.pi * i / num_points
                        for i in range(num_points + 1)
                    )
                ]

                # get the color of the stipple
                average_color = get_avg_color(
                    image, int_x(x), int_y(y), int(radius)
                )

                # If not inverted, invert all the colors
                if not invert and len(average_color) == 3:
                    average_color = tuple(255 - c for c in average_color)

                # Scale the color by darkness to make lighter dots for lighter areas
                average_color = tuple(
                    max(0, min(255, int(c * darkness))) for c in average_color
                )

                if len(circle_points) >= 3 and len(average_color) == 3:
                    append_path(
                        ColoredPath(
                            points=circle_points,
                            color=average_color,
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
    ) -> "list[ColoredPath]":
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
        scaled_image, scale_factor, offset_x, offset_y = (
            self._scale_image_to_machine(image)
        )
        print(
            f"Scaled image to {scaled_image.size[0]}x{scaled_image.size[1]} "
            f"pixels for machine fit."
        )

        # Check rendering style
        style = self.processing_config.render_style
        if style == RenderStyle.STIPPLES:
            print("Rendering stipple style...")
            paths = self._render_stipples(
                scaled_image,
                offset_x,
                offset_y,
                invert=self.processing_config.stipple_invert,
            )
        elif style == RenderStyle.HATCHING:
            print("Rendering hatching style...")
            # Convert to grayscale for brightness sampling
            gray_image = scaled_image.convert("L")
            paths = self._render_hatching(gray_image, offset_x, offset_y)
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


def colored_paths_to_svg(
    colored_paths: "list[ColoredPath]",
    svg_width: int,
    svg_height: int,
) -> str:
    """Convert colored paths to SVG string.

    Args:
        colored_paths: List of ColoredPath objects
        svg_width: Width of SVG canvas
        svg_height: Height of SVG canvas

    Returns:
        SVG content as string
    """
    svg_elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{svg_width}" height="{svg_height}">'
    ]

    for path in colored_paths:
        # Convert color to hex
        r, g, b = path.color
        color_hex = f"#{r:02x}{g:02x}{b:02x}"

        # Create path data
        path_data = "M " + " L ".join(
            f"{x:.2f} {y:.2f}" for x, y in path.points
        )
        if path.is_closed:
            path_data += " Z"

        svg_elements.append(
            f'<path d="{path_data}" fill="{color_hex}" stroke="none"/>'
        )

    svg_elements.append("</svg>")
    return "\n".join(svg_elements)
