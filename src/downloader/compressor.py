import io
from pathlib import Path
from PIL import Image
from src.utils.logging import logger


def compress_to_jpeg(
    image_path: Path,
    quality: int = 85,
) -> tuple[bytes, int, int]:
    """
    Compress an image to JPEG format.

    Returns (jpeg_bytes, original_width, original_height).
    Records ORIGINAL dimensions before any processing.
    """
    with Image.open(image_path) as img:
        # Record original dimensions
        original_width, original_height = img.size

        # Convert RGBA/P to RGB with black background
        if img.mode in ("RGBA", "P", "LA", "PA"):
            background = Image.new("RGB", img.size, (0, 0, 0))
            if img.mode == "P":
                img = img.convert("RGBA")
            if img.mode in ("RGBA", "LA", "PA"):
                background.paste(img, mask=img.split()[-1])
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Compress to JPEG
        buffer = io.BytesIO()
        img.save(
            buffer,
            format="JPEG",
            quality=quality,
            optimize=True,
            subsampling=0,  # 4:4:4 chroma
        )
        jpeg_bytes = buffer.getvalue()

        logger.info(
            f"Compressed {image_path.name}: {original_width}x{original_height}, "
            f"{len(jpeg_bytes) / 1024:.0f}KB JPEG (quality={quality})"
        )

        return jpeg_bytes, original_width, original_height


def generate_filename(source_site: str, img_hash: str, width: int, height: int) -> str:
    """Generate a standardized filename for the compressed JPEG."""
    # Clean the source site name
    site_clean = source_site.replace(".", "_").replace("/", "_")[:30]
    return f"{site_clean}_{img_hash}_{width}x{height}.jpg"
