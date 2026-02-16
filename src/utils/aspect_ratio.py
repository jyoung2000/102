from math import gcd

# Known aspect ratios with their minimum resolutions
KNOWN_RATIOS = {
    (16, 9): (1920, 1080),
    (9, 16): (1080, 1920),
    (21, 9): (2560, 1080),
    (4, 3): (1600, 1200),
    (3, 2): (1920, 1280),
    (1, 1): (1080, 1080),
    (32, 9): (3840, 1080),
}

TOLERANCE = 0.02  # ±2%


def calculate_aspect_ratio(width: int, height: int) -> tuple[int, int]:
    """Calculate the simplified aspect ratio using GCD."""
    if width <= 0 or height <= 0:
        return (0, 0)
    divisor = gcd(width, height)
    return (width // divisor, height // divisor)


def classify_aspect_ratio(width: int, height: int) -> str:
    """Classify into a known aspect ratio string with ±2% tolerance."""
    if width <= 0 or height <= 0:
        return "unknown"

    actual_ratio = width / height

    for (rw, rh), _ in KNOWN_RATIOS.items():
        target_ratio = rw / rh
        if abs(actual_ratio - target_ratio) / target_ratio <= TOLERANCE:
            return f"{rw}:{rh}"

    # Fallback to simplified ratio
    ratio = calculate_aspect_ratio(width, height)
    return f"{ratio[0]}:{ratio[1]}"


def is_mobile(width: int, height: int) -> bool:
    """True if portrait orientation (height > width)."""
    return height > width


def meets_minimum_resolution(width: int, height: int, min_w: int = 1920, min_h: int = 1080) -> bool:
    """Check if dimensions meet minimum resolution requirements."""
    return width >= min_w and height >= min_h


def get_minimum_for_ratio(ratio_str: str) -> tuple[int, int]:
    """Get minimum resolution for a known aspect ratio string."""
    parts = ratio_str.split(":")
    if len(parts) == 2:
        try:
            key = (int(parts[0]), int(parts[1]))
            return KNOWN_RATIOS.get(key, (1920, 1080))
        except ValueError:
            pass
    return (1920, 1080)
