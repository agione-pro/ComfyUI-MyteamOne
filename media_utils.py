"""
Conversion helpers — turn ComfyUI image/video objects into base64 data URIs
the MyteamOne API can ingest.

NOTE on video: base64-encoding a video into `media[].url` is **not supported**
by the MyteamOne backend (the endpoint wants HTTP/HTTPS URLs). Helpers that
try to do it are kept here for completeness but are not used by any node —
the V2V node fails fast and asks the user to provide a hosted URL instead.
"""

import base64
import io
import os

import numpy as np
from PIL import Image


def image_to_data_uri(image_tensor, fmt: str = "jpeg", quality: int = 95) -> str:
    """
    Convert a ComfyUI IMAGE tensor (B, H, W, C float 0-1) to a base64 data URI.
    Defaults to JPEG q95 because PNG encoding of high-res images produces
    payloads several MB in size that the create endpoint struggles to ingest.
    """
    # Handle batched tensors — take the first image.
    arr = image_tensor
    if hasattr(arr, "cpu"):
        arr = arr.cpu().numpy()
    if hasattr(arr, "shape") and len(arr.shape) == 4:
        arr = arr[0]

    arr = np.asarray(arr)
    arr = np.clip(arr * 255.0, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr)

    buf = io.BytesIO()
    if fmt.lower() in ("jpg", "jpeg"):
        img = img.convert("RGB")
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        mime = "image/jpeg"
    else:
        img.save(buf, format="PNG", optimize=True)
        mime = "image/png"

    data = buf.getvalue()
    b64 = base64.b64encode(data).decode("ascii")
    print(f"[MyteamOne] image -> data URI ({len(data) // 1024} KB, {mime})")
    return f"data:{mime};base64,{b64}"


def video_to_data_uri(video_obj) -> str:
    """
    Best-effort: turn a ComfyUI VIDEO into a base64 data URI.

    Kept for completeness — the MyteamOne backend rejects/times-out base64
    video payloads, so node code should not actually call this. The V2V
    node now fails fast with a clear message asking for a hosted URL.
    """
    candidate_paths = []
    for attr in ("file_path", "_path", "path", "filename", "file"):
        v = getattr(video_obj, attr, None)
        if isinstance(v, str) and os.path.isfile(v):
            candidate_paths.append(v)
            break

    if not candidate_paths:
        raise RuntimeError(
            "Could not extract a file path from the ComfyUI VIDEO object. "
            "Please use 'video_url' with a hosted HTTP/HTTPS URL instead."
        )

    path = candidate_paths[0]
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode("ascii")
    print(f"[MyteamOne] video -> data URI ({size / (1024 * 1024):.1f} MB)")
    return f"data:video/mp4;base64,{b64}"
