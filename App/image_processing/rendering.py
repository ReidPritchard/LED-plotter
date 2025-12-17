"""Rendering methods for different drawing styles.

AIDEV-NOTE: This module contains different rendering strategies for converting
images to plotter paths: stipples (dots), hatching (parallel lines), etc.
"""

import math
from typing import TYPE_CHECKING

from PIL import Image

from .utils import clip_line_to_rect, get_average_color_circle, get_brightness

if TYPE_CHECKING:
    from models import ColoredPath, ImageProcessingConfig


def render_stipples(
    image: Image.Image,
    offset_x: float,
    offset_y: float,
    processing_config: "ImageProcessingConfig",
    invert: bool = False,
) -> "list[ColoredPath]":
    """Render image as stipples (dots) based on brightness.

    Style 2: Convert to dots where darker areas have more/larger dots.

    Args:
        image: Grayscale PIL image (scaled to machine size)
        offset_x: X offset in mm for centering
        offset_y: Y offset in mm for centering
        processing_config: Image processing configuration
        invert: More dots in lighter areas if True (correct mapping for LED)

    Returns:
        List of ColoredPath objects representing circles/dots
    """
    from models import ColoredPath

    width, height = image.size

    paths = []
    max_radius = processing_config.stipple_max_radius
    min_radius = processing_config.stipple_min_radius
    grid_size = max_radius * 2.5  # Grid spacing based on max dot size

    # Precompute values for efficiency
    num_points = processing_config.stipple_points_per_circle
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
            if darkness < processing_config.stipple_density:
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
                    2 * math.pi * i / num_points for i in range(num_points + 1)
                )
            ]

            # get the color of the stipple
            average_color = get_average_color_circle(
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


def render_hatching(
    image: Image.Image,
    offset_x: float,
    offset_y: float,
    processing_config: "ImageProcessingConfig",
) -> "list[ColoredPath]":
    """Render image as hatching lines based on brightness.

    Style 3: Convert to parallel lines where darker areas have
    closer line spacing.

    Args:
        image: Grayscale PIL image (scaled to machine size)
        offset_x: X offset in mm for centering
        offset_y: Y offset in mm for centering
        processing_config: Image processing configuration

    Returns:
        List of ColoredPath objects representing hatching lines

    AIDEV-NOTE: Lines are drawn at the configured angle. Spacing
    varies based on local brightness - darker = tighter spacing.
    """
    from models import ColoredPath

    width, height = image.size

    paths = []
    angle_rad = math.radians(processing_config.hatching_angle)

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

        brightness = get_brightness(image, int(sample_x), int(sample_y))
        darkness = 1.0 - brightness

        # Skip very light areas
        if darkness < 0.05:
            current_offset += processing_config.hatching_line_spacing_light
            continue

        # Calculate spacing based on brightness
        spacing = processing_config.hatching_line_spacing_light - darkness * (
            processing_config.hatching_line_spacing_light
            - processing_config.hatching_line_spacing_dark
        )

        # Find line intersection with image bounds
        # Line passes through point: (width/2 + current_offset * px, height/2 + current_offset * py)
        # Direction: (dx, dy)
        center_x = width / 2 + current_offset * px
        center_y = height / 2 + current_offset * py

        # Find where line enters and exits the image rectangle
        line_points = clip_line_to_rect(
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
