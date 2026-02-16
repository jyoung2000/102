import re
import asyncio
from pathlib import Path

import torch
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration

from src.utils.logging import logger


class WallpaperCaptioner:
    """BLIP-base AI captioner for wallpaper images. CPU-only, float32."""

    def __init__(self):
        logger.info("Loading BLIP-base model...")
        self.processor = BlipProcessor.from_pretrained(
            "Salesforce/blip-image-captioning-base"
        )
        self.model = BlipForConditionalGeneration.from_pretrained(
            "Salesforce/blip-image-captioning-base",
            torch_dtype=torch.float32,  # CPU requires float32
        )
        self.model.eval()
        logger.info("BLIP-base model loaded successfully")

    def _prepare_image(self, image_path: Path) -> Image.Image:
        """Load and resize image to BLIP's native 384x384."""
        img = Image.open(image_path).convert("RGB")
        img = img.resize((384, 384), Image.LANCZOS)
        return img

    def _generate_caption(self, image: Image.Image, prompt: str = "", max_tokens: int = 50) -> str:
        """Generate a caption with torch.no_grad()."""
        if prompt:
            inputs = self.processor(image, prompt, return_tensors="pt")
        else:
            inputs = self.processor(image, return_tensors="pt")

        with torch.no_grad():
            out = self.model.generate(**inputs, max_new_tokens=max_tokens)

        caption = self.processor.decode(out[0], skip_special_tokens=True)
        return caption.strip()

    def generate_title(self, image_path: Path) -> str:
        """Generate a creative wallpaper title (3-8 words, title case)."""
        try:
            image = self._prepare_image(image_path)

            # Use a prompt to guide title generation
            caption = self._generate_caption(image, "a photograph of")

            # Post-process into a title
            title = _caption_to_title(caption)
            return title
        except Exception as e:
            logger.error(f"Title generation failed: {e}")
            return "Beautiful Wallpaper"

    def generate_alt_text(self, image_path: Path) -> str:
        """Generate accessibility alt text (1-2 sentences)."""
        try:
            image = self._prepare_image(image_path)
            caption = self._generate_caption(image, max_tokens=75)

            # Clean up
            alt = caption.strip()
            if not alt.endswith("."):
                alt += "."
            # Capitalize first letter
            alt = alt[0].upper() + alt[1:] if alt else "A high-resolution wallpaper image."
            return alt
        except Exception as e:
            logger.error(f"Alt text generation failed: {e}")
            return "A high-resolution wallpaper image."

    def generate_tags(self, image_path: Path, existing_tags: list[str] = None) -> str:
        """Generate 10-20 comma-separated tags, Instagram/Tumblr style."""
        try:
            image = self._prepare_image(image_path)
            caption = self._generate_caption(image, max_tokens=50)

            tags = _caption_to_tags(caption, existing_tags or [])
            return ", ".join(tags)
        except Exception as e:
            logger.error(f"Tag generation failed: {e}")
            return "wallpaper, desktop, background, aesthetic"

    async def process_image(self, image_path: Path, existing_tags: list[str] = None) -> dict:
        """Generate all captions for an image. Runs in executor to avoid blocking."""
        loop = asyncio.get_event_loop()

        title = await loop.run_in_executor(None, self.generate_title, image_path)
        alt_text = await loop.run_in_executor(None, self.generate_alt_text, image_path)
        tags = await loop.run_in_executor(
            None, self.generate_tags, image_path, existing_tags or []
        )

        return {
            "title": title,
            "alt_text": alt_text,
            "tags": tags,
        }


def _caption_to_title(caption: str) -> str:
    """Convert a BLIP caption into a creative wallpaper title."""
    # Remove common BLIP prefixes
    prefixes = [
        "a photograph of ", "a photo of ", "a picture of ",
        "an image of ", "a painting of ", "a view of ",
        "a close up of ", "a closeup of ", "arafed ",
        "there is ", "this is ", "image of ",
    ]
    text = caption.lower().strip()
    for prefix in prefixes:
        if text.startswith(prefix):
            text = text[len(prefix):]
            break

    # Remove trailing articles
    text = re.sub(r'\ba\b$', '', text).strip()

    # Title case
    words = text.split()

    # Aim for 3-8 words
    if len(words) > 8:
        words = words[:8]
    if len(words) < 3:
        words.extend(["Light", "Scene"])

    title = " ".join(w.capitalize() for w in words if w)

    # Strip any remaining weird artifacts
    title = re.sub(r'[^\w\s\'-]', '', title).strip()

    return title if title else "Beautiful Scenery"


def _caption_to_tags(caption: str, existing_tags: list[str]) -> list[str]:
    """Generate tags from a caption + existing tags."""
    tags = set()

    # Always include these base tags
    base_tags = ["wallpaper", "desktop", "background", "aesthetic", "hd"]
    tags.update(base_tags)

    # Extract words from caption
    words = re.findall(r'\b[a-zA-Z]{3,}\b', caption.lower())
    # Filter out stop words
    stop_words = {
        "the", "and", "for", "are", "but", "not", "you", "all",
        "can", "had", "her", "was", "one", "our", "out", "has",
        "have", "with", "that", "this", "from", "they", "been",
        "said", "each", "which", "their", "will", "other", "about",
        "many", "then", "them", "some", "very", "when", "come",
        "could", "would", "make", "like", "into", "than", "its",
        "over", "such", "after", "also", "most", "what", "just",
        "where", "made", "there", "image", "photo", "picture",
        "photograph", "arafed",
    }
    meaningful = [w for w in words if w not in stop_words and len(w) > 2]
    tags.update(meaningful[:10])

    # Add existing tags
    for tag in existing_tags:
        clean = tag.lower().strip()
        if clean and len(clean) > 1:
            tags.add(clean)

    # Add contextual tags based on keywords
    caption_lower = caption.lower()
    context_map = {
        "sunset": ["golden hour", "dusk", "evening sky"],
        "mountain": ["landscape", "nature", "peaks"],
        "ocean": ["sea", "water", "waves", "coastal"],
        "forest": ["trees", "woods", "nature", "green"],
        "city": ["urban", "skyline", "architecture"],
        "night": ["dark", "stars", "nighttime"],
        "flower": ["floral", "botanical", "garden"],
        "sky": ["clouds", "atmosphere", "heavens"],
        "snow": ["winter", "cold", "frost"],
        "beach": ["sand", "tropical", "summer"],
    }
    for keyword, related in context_map.items():
        if keyword in caption_lower:
            tags.update(related[:2])

    # Convert to sorted list, aim for 10-20 tags
    tag_list = sorted(tags)
    if len(tag_list) < 10:
        # Pad with generic tags
        fillers = ["4k", "high resolution", "stunning", "beautiful", "photography",
                    "art", "creative", "design", "digital", "visual"]
        for filler in fillers:
            if len(tag_list) >= 15:
                break
            if filler not in tag_list:
                tag_list.append(filler)

    return tag_list[:20]
