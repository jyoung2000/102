"""Pre-download BLIP-base model during Docker build."""
from transformers import BlipProcessor, BlipForConditionalGeneration
import torch
from PIL import Image

print("Downloading BLIP-base model weights...")
processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
model = BlipForConditionalGeneration.from_pretrained(
    "Salesforce/blip-image-captioning-base",
    torch_dtype=torch.float32
)
print(f"Model: {sum(p.numel() for p in model.parameters()) / 1e6:.0f}M parameters")

# Smoke test
dummy = Image.new("RGB", (384, 384), color=(128, 128, 128))
inputs = processor(dummy, return_tensors="pt")
with torch.no_grad():
    out = model.generate(**inputs, max_new_tokens=10)
caption = processor.decode(out[0], skip_special_tokens=True)
print(f"Smoke test passed: '{caption}'")
