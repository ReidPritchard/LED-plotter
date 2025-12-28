"""Utility functions for image processing and coordinate transformations.

AIDEV-NOTE: This module contains helper functions for scaling, color operations,
and path calculations used throughout the image processing pipeline.
"""

import math
from typing import TYPE_CHECKING

from PIL import Image

if TYPE_CHECKING:
    from models import ColoredPath, MachineConfig


def scale_paths_to_machine(
    paths: "list[ColoredPath]",
    image_width: int,
    image_height: int,
    machine_config: "MachineConfig",
) -> "tuple[list[ColoredPath], float, float, float]":
    """Scale paths from pixel coordinates to machine mm coordinates.

    Args:
        paths: List of paths in pixel coordinates
        image_width: Original image width in pixels
        image_height: Original image height in pixels
        machine_config: Machine configuration with dimensions and margins

    Returns:
        Tuple of (scaled paths, scale_factor, offset_x, offset_y)

    AIDEV-NOTE: Paths are scaled to fit within safe margins while
    maintaining aspect ratio. Centered in drawing area.
    """
    from models import ColoredPath

    margin = machine_config.safe_margin
    safe_width = machine_config.width - 2 * margin
    safe_height = machine_config.height - 2 * margin

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
        scaled_points = [(x * scale + offset_x, y * scale + offset_y) for x, y in path.points]
        scaled_paths.append(
            ColoredPath(
                points=scaled_points,
                color=path.color,
                is_closed=path.is_closed,
            )
        )

    return scaled_paths, scale, offset_x, offset_y


def scale_image_to_machine(
    image: Image.Image, machine_config: "MachineConfig"
) -> "tuple[Image.Image, float, float, float]":
    """Scale image to fit within machine bounds while maintaining aspect ratio.

    Args:
        image: Input PIL image
        machine_config: Machine configuration with dimensions and margins

    Returns:
        Tuple of (scaled_image, scale_factor, offset_x, offset_y)
        where offsets are in mm for centering in machine space

    AIDEV-NOTE: This scales the image so that when we sample pixels,
    pixel coordinates map directly to mm in machine space.
    """
    margin = machine_config.safe_margin
    safe_width = machine_config.width - 2 * margin
    safe_height = machine_config.height - 2 * margin

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
    scaled_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # Calculate centering offsets in mm
    offset_x = margin + (safe_width - new_width) / 2
    offset_y = margin + (safe_height - new_height) / 2

    return scaled_image, scale, offset_x, offset_y


def calculate_total_length(paths: "list[ColoredPath]") -> float:
    """Calculate total path length in mm."""
    total = 0.0
    for path in paths:
        for i in range(1, len(path.points)):
            x1, y1 = path.points[i - 1]
            x2, y2 = path.points[i]
            total += math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    return total


def count_commands(paths: "list[ColoredPath]") -> int:
    """Count total number of commands that will be generated."""
    return sum(len(path.points) for path in paths)


def get_brightness(image: Image.Image, x: int, y: int) -> float:
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


def get_color(image: Image.Image, x: int, y: int) -> "tuple[int, int, int]":
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
            r, g, b = pixel[:3]
            return (int(r), int(g), int(b))  # RGB only (drop alpha if present)
        else:
            # Grayscale pixel, convert to RGB tuple
            gray_int = int(pixel) if pixel is not None else 255
            return (gray_int, gray_int, gray_int)
    return (255, 255, 255)  # Default to white for out of bounds


def get_average_color_circle(
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


def clip_line_to_rect(
    center_x: float,
    center_y: float,
    dx: float,
    dy: float,
    x_min: float,
    y_min: float,
    x_max: float,
    y_max: float,
) -> "list[tuple[float, float]] | None":
    """Clip a line to a rectangular boundary.

    Args:
        center_x: Line center X coordinate
        center_y: Line center Y coordinate
        dx: Line direction X component
        dy: Line direction Y component
        x_min: Rectangle minimum X
        y_min: Rectangle minimum Y
        x_max: Rectangle maximum X
        y_max: Rectangle maximum Y

    Returns:
        List of two points [(x1, y1), (x2, y2)] or None if line doesn't intersect
    """
    # Find parametric t values where line intersects rectangle edges
    t_values = []

    # Avoid division by zero
    if abs(dx) > 1e-10:
        # Left edge (x = x_min)
        t = (x_min - center_x) / dx
        y = center_y + t * dy
        if y_min <= y <= y_max:
            t_values.append((t, x_min, y))

        # Right edge (x = x_max)
        t = (x_max - center_x) / dx
        y = center_y + t * dy
        if y_min <= y <= y_max:
            t_values.append((t, x_max, y))

    if abs(dy) > 1e-10:
        # Top edge (y = y_min)
        t = (y_min - center_y) / dy
        x = center_x + t * dx
        if x_min <= x <= x_max:
            t_values.append((t, x, y_min))

        # Bottom edge (y = y_max)
        t = (y_max - center_y) / dy
        x = center_x + t * dx
        if x_min <= x <= x_max:
            t_values.append((t, x, y_max))

    if len(t_values) < 2:
        return None

    # Sort by t parameter and get first two intersection points
    t_values.sort(key=lambda x: x[0])
    return [(t_values[0][1], t_values[0][2]), (t_values[1][1], t_values[1][2])]
