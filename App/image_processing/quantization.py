"""Color quantization methods for reducing image color palettes.

AIDEV-NOTE: This module handles color quantization using K-means clustering
and PIL's built-in methods. K-means provides best results for photographs.
"""

import numpy as np
from PIL import Image
from sklearn.cluster import KMeans


def quantize_colors(
    image: Image.Image,
    num_colors: int,
    method: str = "kmeans",
) -> "tuple[Image.Image, list[tuple[int, int, int]]]":
    """Reduce image to a limited color palette.

    Args:
        image: Input image (RGBA or RGB)
        num_colors: Target number of colors (4-32)
        method: Quantization method ('kmeans', 'median_cut', or 'octree')

    Returns:
        Tuple of (quantized image in RGB mode, palette list)

    AIDEV-NOTE: K-means provides best results for photographs but is
    slower. Median cut is faster for simpler images.
    """
    # Convert to RGB (drop alpha for color clustering)
    rgb_image = image.convert("RGB")

    if method == "kmeans":
        return quantize_kmeans(rgb_image, num_colors)
    elif method == "median_cut":
        return quantize_pillow(rgb_image, num_colors, method=Image.Quantize.MEDIANCUT)
    elif method == "octree":
        return quantize_pillow(
            rgb_image, num_colors, method=Image.Quantize.FASTOCTREE
        )
    else:
        # Default to kmeans
        return quantize_kmeans(rgb_image, num_colors)


def quantize_kmeans(
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
    quantized_array = quantized_pixels.reshape(original_shape).astype(np.uint8)

    # Convert back to PIL Image
    quantized_image = Image.fromarray(quantized_array, mode="RGB")

    return quantized_image, palette


def quantize_pillow(
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
