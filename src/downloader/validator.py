from pathlib import Path
from PIL import Image
from src.utils.aspect_ratio import classify_aspect_ratio, is_mobile, meets_minimum_resolution
from src.utils.logging import logger


class ValidationResult:
    """Result of image validation."""
    def __init__(
        self,
        valid: bool,
        width: int = 0,
        height: int = 0,
        aspect_ratio: str = "unknown",
        is_portrait: bool = False,
        rejection_reason: str = "",
    ):
        self.valid = valid
        self.width = width
        self.height = height
        self.aspect_ratio = aspect_ratio
        self.is_portrait = is_portrait
        self.rejection_reason = rejection_reason


def validate_image(
    image_path: Path,
    min_width: int = 1920,
    min_height: int = 1080,
    allowed_ratios: list[str] | None = None,
) -> ValidationResult:
    """
    Validate an image file for wallpaper suitability.
    Checks: valid image, dimensions, aspect ratio.
    """
    try:
        with Image.open(image_path) as img:
            img.verify()
    except Exception as e:
        return ValidationResult(valid=False, rejection_reason=f"Invalid image: {e}")

    # Re-open after verify (verify closes the file)
    try:
        with Image.open(image_path) as img:
            width, height = img.size
    except Exception as e:
        return ValidationResult(valid=False, rejection_reason=f"Cannot read image: {e}")

    # Check minimum resolution
    # For portrait images, swap the min requirements
    if is_mobile(width, height):
        check_w, check_h = min(min_width, min_height), max(min_width, min_height)
    else:
        check_w, check_h = min_width, min_height

    if not meets_minimum_resolution(width, height, check_w, check_h):
        return ValidationResult(
            valid=False,
            width=width,
            height=height,
            rejection_reason=f"Too small: {width}x{height} (need {check_w}x{check_h})"
        )

    # Check aspect ratio if specified
    ratio = classify_aspect_ratio(width, height)
    if allowed_ratios and ratio not in allowed_ratios:
        # Check if it's close enough to any allowed ratio
        return ValidationResult(
            valid=False,
            width=width,
            height=height,
            aspect_ratio=ratio,
            is_portrait=is_mobile(width, height),
            rejection_reason=f"Aspect ratio {ratio} not in allowed list"
        )

    return ValidationResult(
        valid=True,
        width=width,
        height=height,
        aspect_ratio=ratio,
        is_portrait=is_mobile(width, height),
    )


def get_dominant_colors(image_path: Path, num_colors: int = 5) -> list[str]:
    """Extract dominant colors from an image for fallback tagging."""
    try:
        with Image.open(image_path) as img:
            # Resize for speed
            img = img.convert("RGB").resize((100, 100), Image.LANCZOS)
            pixels = list(img.getdata())

            # Simple color binning
            color_names = {
                "red": (255, 0, 0),
                "green": (0, 128, 0),
                "blue": (0, 0, 255),
                "yellow": (255, 255, 0),
                "orange": (255, 165, 0),
                "purple": (128, 0, 128),
                "pink": (255, 192, 203),
                "brown": (139, 69, 19),
                "black": (0, 0, 0),
                "white": (255, 255, 255),
                "gray": (128, 128, 128),
                "cyan": (0, 255, 255),
                "teal": (0, 128, 128),
            }

            counts = {name: 0 for name in color_names}
            for pixel in pixels:
                closest = min(
                    color_names.items(),
                    key=lambda c: sum((a - b) ** 2 for a, b in zip(pixel, c[1]))
                )
                counts[closest[0]] += 1

            sorted_colors = sorted(counts.items(), key=lambda x: x[1], reverse=True)
            return [c[0] for c in sorted_colors[:num_colors] if c[1] > 0]
    except Exception:
        return ["colorful"]
