"""SVG parsing and path extraction functionality."""

from itertools import chain

import svg

from models import ColoredPath


def colored_paths_to_svg(
    colored_paths: list[ColoredPath],
) -> str:
    """Convert colored paths to SVG string.

    Args:
        colored_paths: List of ColoredPath objects

    Returns:
        SVG content as string
    """
    if not colored_paths:
        # Return empty SVG if no paths
        return svg.SVG(viewBox=svg.ViewBoxSpec(0, 0, 100, 100), elements=[]).as_str()

    elements: list[svg.Element] = []

    # Calculate bounding box from all coordinates
    min_x = float("inf")
    max_x = float("-inf")
    min_y = float("inf")
    max_y = float("-inf")

    for path in colored_paths:
        r, g, b = path.color

        # Skip any paths that are darker than a threshold (e.g., RGB all below 10)
        threshold = 10
        if r < threshold and g < threshold and b < threshold:
            continue

        points = list(path.points)
        if path.is_closed and points:
            points.append(points[0])  # Close the path

        # Flatten points for SVG Polyline
        # Cast to list to satisfy type checker (svg library uses list[Number])
        path_points: list[float] = list(chain.from_iterable(points))

        svg_element = svg.Polyline(
            points=path_points,  # type: ignore[arg-type]
            stroke=f"rgb({r},{g},{b})",
            fill="none" if not path.is_closed else f"rgb({r},{g},{b})",
            stroke_width=1,
        )
        elements.append(svg_element)

        # Update bounding box for all points
        for x, y in points:
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)

    # Add small padding to prevent edge clipping
    padding = 5
    viewbox_x = min_x - padding
    viewbox_y = min_y - padding
    viewbox_width = (max_x - min_x) + (2 * padding)
    viewbox_height = (max_y - min_y) + (2 * padding)

    final_svg = svg.SVG(
        viewBox=svg.ViewBoxSpec(viewbox_x, viewbox_y, viewbox_width, viewbox_height),
        elements=elements,
    )
    return final_svg.as_str()
