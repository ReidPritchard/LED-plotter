"""Image processing pipeline for photo-to-plotter conversion.

AIDEV-NOTE: This package handles the complete pipeline from photograph
to plotter paths. Organized into modular components:
- processor: Main ImageProcessor orchestrator
- quantization: Color palette reduction
- svg_parser: SVG parsing and path extraction
- rendering: Different rendering styles (stipples, hatching)
- utils: Scaling, color, and geometric utilities
"""

from .processor import ImageProcessor
from .svg_parser import colored_paths_to_svg

__all__ = ["ImageProcessor", "colored_paths_to_svg"]
