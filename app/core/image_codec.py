"""Image encoding helpers for Meshy requests."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ImagePayload:
    """Container for image bytes and metadata."""

    data: bytes
    filename: str
    mime_type: str


def _detect_mime_type(path: Path, header: bytes) -> str:
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    suffix = path.suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg"}:
        return "image/png" if suffix == ".png" else "image/jpeg"
    raise ValueError("Unsupported image format. Use PNG or JPEG.")


def encode_image(path: str) -> ImagePayload:
    """Load and encode an image for upload."""
    file_path = Path(path)
    data = file_path.read_bytes()
    mime_type = _detect_mime_type(file_path, data[:8])
    return ImagePayload(data=data, filename=file_path.name, mime_type=mime_type)


def encode_image_to_data_uri(path: str) -> str:
    """Return a base64 data URI for a supported image file."""
    payload = encode_image(path)
    encoded = base64.b64encode(payload.data).decode("utf-8")
    return f"data:{payload.mime_type};base64,{encoded}"
