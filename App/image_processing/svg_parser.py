"""SVG parsing and path extraction functionality.

AIDEV-NOTE: This module handles SVG parsing, path extraction, and color parsing
using svgpathtools. Complex numbers represent coordinates (real=x, imag=y).
"""

import io
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models import ColoredPath

# Import svgpathtools - may not be installed yet
try:
    import svgpathtools
except ImportError:
    svgpathtools = None  # type: ignore[assignment]


def extract_paths(svg_content: str) -> "list[ColoredPath]":
    """Parse SVG and extract paths with colors.

    Args:
        svg_content: SVG string from vectorization

    Returns:
        List of ColoredPath objects with points in pixel coordinates

    AIDEV-NOTE: Uses svgpathtools to parse SVG paths. Complex numbers
    represent coordinates (real=x, imag=y).
    """
    from models import ColoredPath

    if svgpathtools is None:
        raise RuntimeError("svgpathtools is not installed. Run: pixi install")

    # Parse SVG from string
    paths, attributes = svgpathtools.svg2paths(io.StringIO(svg_content), False)

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
        color = parse_color(attrs)
        if color is None:
            continue  # Skip paths with no fill (outlines only)

        # Sample points along path
        print(f"Sampling points for path with color {color}...")
        points = sample_path_points(path)
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
            f"Added colored path with color {color} and {len(points)} points."
        )

        colored_paths.append(new_colored_path)

    print(f"Extracted {len(colored_paths)} colored paths from SVG.")

    return colored_paths


def parse_color(attrs: dict) -> "tuple[int, int, int] | None":
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
    match = re.match(r"rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", fill)
    if match:
        return (
            int(match.group(1)),
            int(match.group(2)),
            int(match.group(3)),
        )

    return None


def sample_path_points(path) -> "list[tuple[float, float]]":
    """Sample points along an SVG path.

    AIDEV-NOTE: svgpathtools uses complex numbers for coordinates.
    Real part = x, imaginary part = y.
    """
    points = []
    path_length = path.length()

    # Calculate number of samples based on path length
    # More points for longer paths, but cap to avoid too many commands
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
        path_data = "M " + " L ".join(f"{x:.2f} {y:.2f}" for x, y in path.points)
        if path.is_closed:
            path_data += " Z"

        svg_elements.append(
            f'<path d="{path_data}" fill="{color_hex}" stroke="none"/>'
        )

    svg_elements.append("</svg>")
    return "\n".join(svg_elements)
