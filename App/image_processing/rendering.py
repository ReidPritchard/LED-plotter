"""Rendering methods for different drawing styles.

AIDEV-NOTE: This module contains different rendering strategies for converting
images to plotter paths: stipples (dots), hatching (parallel lines), etc.
"""

import math
from typing import TYPE_CHECKING

from PIL import Image

from .utils import (
    clip_line_to_rect,
    get_average_color_circle,
    get_brightness,
    get_color,
)

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
    invert: bool = False,
) -> "list[ColoredPath]":
    """Render image as hatching lines based on brightness.

    Style 3: Convert to parallel segmented lines where darker areas have
    closer line spacing and longer segments. Each line is broken into
    segments with gaps, where segment length varies by local brightness.

    Args:
        image: RGB or grayscale PIL image (scaled to machine size)
        offset_x: X offset in mm for centering
        offset_y: Y offset in mm for centering
        processing_config: Image processing configuration
        invert: If True, draw lines in light areas instead of dark areas

    Returns:
        List of ColoredPath objects representing hatching line segments

    AIDEV-NOTE: Lines are drawn at the configured angle and broken into segments.
    Parallel line spacing varies based on average brightness - darker = tighter spacing.
    Each segment's length varies by local brightness - darker = longer segments.
    Color is sampled from the image at each segment's midpoint.
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
        # Find line intersection with image bounds first
        # Line passes through point: (width/2 + current_offset * px, height/2 + current_offset * py)
        # Direction: (dx, dy)
        center_x = width / 2 + current_offset * px
        center_y = height / 2 + current_offset * py

        # Find where line enters and exits the image rectangle
        line_points = clip_line_to_rect(
            center_x, center_y, dx, dy, 0, 0, width, height
        )

        if not line_points or len(line_points) != 2:
            # Line doesn't intersect image, skip to next
            current_offset += processing_config.hatching_line_spacing_light
            continue

        (x1, y1), (x2, y2) = line_points

        # AIDEV-NOTE: Calculate total line length and direction vector for segmentation
        line_length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        if line_length < 0.1:
            current_offset += processing_config.hatching_line_spacing_light
            continue

        # Normalized direction vector for this line
        dir_x = (x2 - x1) / line_length
        dir_y = (y2 - y1) / line_length

        # AIDEV-NOTE: Sample brightness at multiple points along the full line
        # to determine average darkness for line spacing calculation
        num_samples = 10
        total_brightness = 0.0
        for i in range(num_samples):
            t = i / (num_samples - 1) if num_samples > 1 else 0.5
            sample_x = int(x1 + t * (x2 - x1))
            sample_y = int(y1 + t * (y2 - y1))
            total_brightness += get_brightness(image, sample_x, sample_y)

        avg_brightness = total_brightness / num_samples
        avg_darkness = 1.0 - avg_brightness

        # Apply invert: if invert is True, swap brightness/darkness logic
        if invert:
            avg_darkness = avg_brightness

        # Skip very light areas (or very dark if inverted)
        if avg_darkness < 0.05:
            current_offset += processing_config.hatching_line_spacing_light
            continue

        # Calculate spacing to next parallel line based on average darkness
        spacing = (
            processing_config.hatching_line_spacing_light
            - avg_darkness
            * (
                processing_config.hatching_line_spacing_light
                - processing_config.hatching_line_spacing_dark
            )
        )

        # AIDEV-NOTE: Break line into segments with varying lengths based on local brightness
        # Darker areas get longer segments, lighter areas get shorter segments
        current_distance = 0.0
        segment_gap = processing_config.hatching_segment_gap

        while current_distance < line_length:
            # Calculate segment start position
            seg_start_x = x1 + current_distance * dir_x
            seg_start_y = y1 + current_distance * dir_y

            # Sample brightness at segment start to determine segment length
            sample_x = int(seg_start_x)
            sample_y = int(seg_start_y)
            brightness = get_brightness(image, sample_x, sample_y)
            darkness = 1.0 - brightness

            if invert:
                darkness = brightness

            # Skip very light segments
            if darkness < 0.05:
                current_distance += segment_gap
                continue

            # Calculate segment length based on darkness
            # Darker = longer segments (up to max), lighter = shorter segments (down to min)
            segment_length = (
                processing_config.hatching_segment_min_length
                + darkness
                * (
                    processing_config.hatching_segment_max_length
                    - processing_config.hatching_segment_min_length
                )
            )

            # Clamp segment to not exceed remaining line length
            segment_length = min(
                segment_length, line_length - current_distance
            )

            # Calculate segment end position
            seg_end_x = seg_start_x + segment_length * dir_x
            seg_end_y = seg_start_y + segment_length * dir_y

            # Sample color at segment midpoint
            mid_seg_x = int((seg_start_x + seg_end_x) / 2)
            mid_seg_y = int((seg_start_y + seg_end_y) / 2)
            segment_color = get_color(image, mid_seg_x, mid_seg_y)

            # Convert to machine coordinates and add segment
            machine_points = [
                (seg_start_x + offset_x, seg_start_y + offset_y),
                (seg_end_x + offset_x, seg_end_y + offset_y),
            ]
            paths.append(
                ColoredPath(
                    points=machine_points,
                    color=segment_color,
                    is_closed=False,
                )
            )

            # Move to next segment position (segment length + gap)
            current_distance += segment_length + segment_gap

        current_offset += spacing

    return paths


def render_cross_hatch(
    image: Image.Image,
    offset_x: float,
    offset_y: float,
    processing_config: "ImageProcessingConfig",
) -> "list[ColoredPath]":
    """Render image as cross-hatching with progressive angle layers.

    Style 4: Multiple overlapping hatch angles where darker areas get more
    layers. Creates richer tonal depth through layer stacking.

    Args:
        image: RGB or grayscale PIL image (scaled to machine size)
        offset_x: X offset in mm for centering
        offset_y: Y offset in mm for centering
        processing_config: Image processing configuration

    Returns:
        List of ColoredPath objects representing cross-hatch line segments

    AIDEV-NOTE: Progressive layers - darker areas get more hatch angles:
    Layer 0 (base angle): visible in 75%+ dark areas
    Layer 1: visible in 50%+ dark areas
    Layer 2: visible in 25%+ dark areas
    Layer 3: visible in 10%+ dark areas
    """

    paths = []
    max_angles = processing_config.cross_hatch_max_angles
    base_angle = processing_config.cross_hatch_base_angle

    # Generate angle set evenly distributed across 180°
    # e.g., 4 angles with base 45° → [45°, 90°, 135°, 180°]
    angle_step = 180.0 / max_angles
    angles = [base_angle + i * angle_step for i in range(max_angles)]

    # For each potential angle layer
    for layer_idx, angle in enumerate(angles):
        # Calculate darkness threshold for this layer
        # Layer 0: threshold=0.25 (drawn in areas with darkness >= 0.25)
        # Layer 1: threshold=0.50 (drawn in areas with darkness >= 0.50)
        # Layer 2: threshold=0.75 (drawn in areas with darkness >= 0.75)
        # Layer 3: threshold=0.90 (drawn in areas with darkness >= 0.90)
        layer_threshold = 0.25 + (layer_idx * 0.25)

        # Render hatching for this angle with threshold filtering
        layer_paths = _render_hatch_layer_with_threshold(
            image,
            offset_x,
            offset_y,
            processing_config,
            angle,
            layer_threshold,
        )
        paths.extend(layer_paths)

    return paths


def _render_hatch_layer_with_threshold(
    image: Image.Image,
    offset_x: float,
    offset_y: float,
    processing_config: "ImageProcessingConfig",
    angle: float,
    darkness_threshold: float,
) -> "list[ColoredPath]":
    """Helper: Render single hatch layer, skipping areas below darkness threshold.

    This is the core hatching logic extracted for reuse by both render_hatching()
    and render_cross_hatch(). It uses cross-hatch config parameters.

    Args:
        image: RGB or grayscale PIL image
        offset_x: X offset in mm
        offset_y: Y offset in mm
        processing_config: Configuration object
        angle: Angle of hatching lines in degrees
        darkness_threshold: Minimum darkness (0-1) to draw segments

    Returns:
        List of ColoredPath objects for this layer
    """
    from models import ColoredPath

    width, height = image.size
    paths = []
    angle_rad = math.radians(angle)

    # Calculate line direction and perpendicular
    dx = math.cos(angle_rad)
    dy = math.sin(angle_rad)
    px = -dy  # Perpendicular direction for spacing
    py = dx

    # Calculate the range we need to cover with parallel lines
    diagonal = math.sqrt(width**2 + height**2)
    current_offset = -diagonal / 2
    max_offset = diagonal / 2

    # Use cross-hatch config parameters
    line_spacing_dark = processing_config.cross_hatch_line_spacing_dark
    line_spacing_light = processing_config.cross_hatch_line_spacing_light
    segment_max_length = processing_config.cross_hatch_segment_max_length
    segment_min_length = processing_config.cross_hatch_segment_min_length
    segment_gap = processing_config.cross_hatch_segment_gap

    while current_offset < max_offset:
        # Find line intersection with image bounds
        center_x = width / 2 + current_offset * px
        center_y = height / 2 + current_offset * py

        line_points = clip_line_to_rect(
            center_x, center_y, dx, dy, 0, 0, width, height
        )

        if not line_points or len(line_points) != 2:
            current_offset += line_spacing_light
            continue

        (x1, y1), (x2, y2) = line_points

        # Calculate line length and direction
        line_length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        if line_length < 0.1:
            current_offset += line_spacing_light
            continue

        dir_x = (x2 - x1) / line_length
        dir_y = (y2 - y1) / line_length

        # Sample brightness at multiple points to determine spacing
        num_samples = 10
        total_brightness = 0.0
        for i in range(num_samples):
            t = i / (num_samples - 1) if num_samples > 1 else 0.5
            sample_x = int(x1 + t * (x2 - x1))
            sample_y = int(y1 + t * (y2 - y1))
            total_brightness += get_brightness(image, sample_x, sample_y)

        avg_brightness = total_brightness / num_samples
        avg_darkness = 1.0 - avg_brightness

        # Skip this line entirely if average darkness below threshold
        if avg_darkness < darkness_threshold:
            current_offset += line_spacing_light
            continue

        # Calculate spacing to next parallel line based on darkness
        spacing = line_spacing_light - avg_darkness * (
            line_spacing_light - line_spacing_dark
        )

        # Break line into segments with varying lengths
        current_distance = 0.0

        while current_distance < line_length:
            # Calculate segment start position
            seg_start_x = x1 + current_distance * dir_x
            seg_start_y = y1 + current_distance * dir_y

            # Sample brightness at segment start
            sample_x = int(seg_start_x)
            sample_y = int(seg_start_y)
            brightness = get_brightness(image, sample_x, sample_y)
            darkness = 1.0 - brightness

            # Skip segments below threshold
            if darkness < darkness_threshold:
                current_distance += segment_gap
                continue

            # Calculate segment length based on darkness
            segment_length = segment_min_length + darkness * (
                segment_max_length - segment_min_length
            )

            # Clamp to remaining line length
            segment_length = min(
                segment_length, line_length - current_distance
            )

            # Calculate segment end position
            seg_end_x = seg_start_x + segment_length * dir_x
            seg_end_y = seg_start_y + segment_length * dir_y

            # Sample color at segment midpoint
            mid_seg_x = int((seg_start_x + seg_end_x) / 2)
            mid_seg_y = int((seg_start_y + seg_end_y) / 2)
            segment_color = get_color(image, mid_seg_x, mid_seg_y)

            # Convert to machine coordinates and add segment
            machine_points = [
                (seg_start_x + offset_x, seg_start_y + offset_y),
                (seg_end_x + offset_x, seg_end_y + offset_y),
            ]
            paths.append(
                ColoredPath(
                    points=machine_points,
                    color=segment_color,
                    is_closed=False,
                )
            )

            # Move to next segment position
            current_distance += segment_length + segment_gap

        current_offset += spacing

    return paths


"""TODO

Other rendering styles to implement:
 - Dithered: Use dithering techniques to create texture based on brightness.
 - Outline
 - Particles (DrawingBalls)
 - Reaction Diffusion
 - Traveling Salesman
 - Norwegian spiral
 - Posterize and Infill

Most of these styles have example images here:
    https://github.com/euphy/polargraph/wiki/Vector-Drawing-Styles

Make sure to update ImageProcessingConfig with any new parameters
needed and RenderStyle with the new style option (in models.py).

"""
