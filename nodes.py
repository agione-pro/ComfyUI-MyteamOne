"""
ComfyUI nodes for MyteamOne — Seedance 2.0 video generation.

Nodes:
  - MyteamOne API Client                 : holds api key / endpoints
  - MyteamOne Seedance 2.0 Text to Video : prompt -> video
  - MyteamOne Seedance 2.0 Image to Video: image(s) + prompt -> video
  - MyteamOne Seedance 2.0 Video to Video: video + prompt -> video
"""

import os
import folder_paths

from .api_client import MyteamOneClient
from .media_utils import image_to_data_uri, video_to_data_uri

try:
    from comfy_api.input_impl import VideoFromFile  # type: ignore
    HAS_VIDEO_TYPE = True
except Exception:
    HAS_VIDEO_TYPE = False


# ---- Model IDs (from MyteamOne video model docs) ----
MODEL_MAP = {
    "Seedance 2.0":      "bytedance/dreamina-seedance-2-0-260128/78337",
    "Seedance 2.0 Fast": "bytedance/dreamina-seedance-2-0-fast-260128/4a4b8",
}

RESOLUTIONS = ["480p", "720p", "1080p"]   # Fast does NOT support 1080p
RATIOS      = ["adaptive", "16:9", "9:16", "1:1", "4:3", "3:4", "21:9"]

DEFAULT_BASE_URL    = "https://zh.agione.co/hyperone/xapi/api/v1"
DEFAULT_CREATE_PATH = "/videos"
DEFAULT_POLL_URL    = "https://agione.cc/hyperone/xapi/api/videos/generations/task/{taskid}"

_VIDEO_RETURN_TYPE = ("VIDEO",) if HAS_VIDEO_TYPE else ("STRING",)
_VIDEO_RETURN_NAME = ("video",) if HAS_VIDEO_TYPE else ("video_path",)


def _check_fast_resolution(model: str, resolution: str) -> None:
    """Seedance 2.0 Fast does not support 1080p. Fail fast so we don't waste
    a doomed request on the server."""
    if model == "Seedance 2.0 Fast" and resolution == "1080p":
        raise ValueError(
            "Seedance 2.0 Fast does not support 1080p. "
            "Use 720p (or 480p), or switch to the standard 'Seedance 2.0' model."
        )


def _save_result(client, result, task_id):
    """Download the finished video and wrap it as a ComfyUI VIDEO output."""
    video_url = result.get("video_url")
    if not video_url:
        raise RuntimeError(f"No video URL in success response: {result}")

    output_dir = folder_paths.get_output_directory()
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"myteamone_seedance_{task_id}.mp4")
    client.download_video(video_url, output_path)
    print(f"[MyteamOne] saved -> {output_path}")

    if HAS_VIDEO_TYPE:
        return (VideoFromFile(output_path),)
    return (output_path,)


# ============================================================
# Node 1: API Client
# ============================================================

class MyteamOneClientNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "api_key":     ("STRING", {"default": "", "multiline": False}),
                "base_url":    ("STRING", {"default": DEFAULT_BASE_URL, "multiline": False}),
                "create_path": ("STRING", {"default": DEFAULT_CREATE_PATH, "multiline": False}),
                "poll_path":   ("STRING", {"default": DEFAULT_POLL_URL, "multiline": False}),
            }
        }

    RETURN_TYPES = ("MYTEAMONE_CLIENT",)
    RETURN_NAMES = ("client",)
    FUNCTION = "build"
    CATEGORY = "MyteamOne"

    def build(self, api_key, base_url, create_path, poll_path):
        if not api_key.strip():
            raise ValueError("Please set your MyteamOne API key.")
        return (
            MyteamOneClient(
                api_key=api_key.strip(),
                base_url=base_url,
                create_path=create_path,
                poll_path_template=poll_path,
            ),
        )


# ============================================================
# Node 2: Text to Video
# ============================================================

class MyteamOneSeedance20T2V:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "client":         ("MYTEAMONE_CLIENT",),
                "prompt":         ("STRING", {"multiline": True, "default": "A cinematic shot of a cat walking in a sunlit garden"}),
                "model":          (list(MODEL_MAP.keys()), {"default": "Seedance 2.0 Fast"}),
                "resolution":     (RESOLUTIONS, {"default": "720p"}),
                "ratio":          (RATIOS, {"default": "16:9"}),
                "duration":       ("INT", {"default": 5, "min": 4, "max": 15, "step": 1}),
                "generate_audio": ("BOOLEAN", {"default": True}),
                "watermark":      ("BOOLEAN", {"default": False}),
                "seed":           ("INT", {"default": 0, "min": 0, "max": 2**31 - 1}),
            }
        }

    RETURN_TYPES = _VIDEO_RETURN_TYPE
    RETURN_NAMES = _VIDEO_RETURN_NAME
    FUNCTION = "generate"
    CATEGORY = "MyteamOne/Seedance"

    def generate(self, client, prompt, model, resolution, ratio, duration,
                 generate_audio, watermark, seed):
        _check_fast_resolution(model, resolution)
        payload = {
            "model": MODEL_MAP[model],
            "prompt": prompt,
            "resolution": resolution,
            "ratio": ratio,
            "duration": duration,
            "generate_audio": generate_audio,
            "watermark": watermark,
        }
        if seed > 0:
            payload["seed"] = seed

        task_id = client.create_task(payload)
        result  = client.poll_task(task_id)
        return _save_result(client, result, task_id)


# ============================================================
# Node 3: Image to Video
# ============================================================

class MyteamOneSeedance20I2V:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "client":         ("MYTEAMONE_CLIENT",),
                "prompt":         ("STRING", {"multiline": True, "default": "The subject comes alive, gentle camera push-in"}),
                "model":          (list(MODEL_MAP.keys()), {"default": "Seedance 2.0 Fast"}),
                "resolution":     (RESOLUTIONS, {"default": "720p"}),
                "ratio":          (RATIOS, {"default": "adaptive"}),
                "duration":       ("INT", {"default": 5, "min": 4, "max": 15, "step": 1}),
                "generate_audio": ("BOOLEAN", {"default": True}),
                "watermark":      ("BOOLEAN", {"default": False}),
                "seed":           ("INT", {"default": 0, "min": 0, "max": 2**31 - 1}),
            },
            "optional": {
                # Wire a ComfyUI IMAGE (sent as base64) OR fill a public URL.
                "image":          ("IMAGE",),
                "last_frame":     ("IMAGE",),
                "image_url":      ("STRING", {"default": "", "multiline": False}),
                "last_frame_url": ("STRING", {"default": "", "multiline": False}),
            },
        }

    RETURN_TYPES = _VIDEO_RETURN_TYPE
    RETURN_NAMES = _VIDEO_RETURN_NAME
    FUNCTION = "generate"
    CATEGORY = "MyteamOne/Seedance"

    def generate(self, client, prompt, model, resolution, ratio, duration,
                 generate_audio, watermark, seed,
                 image=None, last_frame=None, image_url="", last_frame_url=""):
        _check_fast_resolution(model, resolution)
        # ---- First frame (required) ----
        if image is not None:
            first_url = image_to_data_uri(image)
        elif image_url.strip():
            first_url = image_url.strip()
        else:
            raise ValueError(
                "Image-to-Video needs a first frame: either wire an IMAGE into "
                "'image', or fill 'image_url' with a public image URL."
            )

        # Use the official content[] format (best base64 compatibility).
        content = []
        if prompt and prompt.strip():
            content.append({"type": "text", "text": prompt})
        content.append({
            "type": "image_url",
            "image_url": {"url": first_url},
            "role": "first_frame",
        })

        # ---- Last frame (optional) ----
        last_url = None
        if last_frame is not None:
            last_url = image_to_data_uri(last_frame)
        elif last_frame_url.strip():
            last_url = last_frame_url.strip()
        if last_url:
            content.append({
                "type": "image_url",
                "image_url": {"url": last_url},
                "role": "last_frame",
            })

        payload = {
            "model": MODEL_MAP[model],
            "content": content,
            "resolution": resolution,
            "ratio": ratio,
            "duration": duration,
            "generate_audio": generate_audio,
            "watermark": watermark,
        }
        if seed > 0:
            payload["seed"] = seed

        task_id = client.create_task(payload)
        result  = client.poll_task(task_id)
        return _save_result(client, result, task_id)


# ============================================================
# Node 4: Video to Video
# ============================================================

class MyteamOneSeedance20V2V:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "client":         ("MYTEAMONE_CLIENT",),
                "prompt":         ("STRING", {"multiline": True, "default": "Restyle the video while keeping the motion and composition"}),
                "model":          (list(MODEL_MAP.keys()), {"default": "Seedance 2.0 Fast"}),
                "resolution":     (RESOLUTIONS, {"default": "720p"}),
                "ratio":          (RATIOS, {"default": "adaptive"}),
                "duration":       ("INT", {"default": 5, "min": 4, "max": 15, "step": 1}),
                "generate_audio": ("BOOLEAN", {"default": True}),
                "watermark":      ("BOOLEAN", {"default": False}),
                "seed":           ("INT", {"default": 0, "min": 0, "max": 2**31 - 1}),
            },
            "optional": {
                # A public video URL is the reliable path. A wired VIDEO is
                # converted to base64 (best effort — may be rejected/too large).
                "video_url":           ("STRING", {"default": "", "multiline": False}),
                "video":               ("VIDEO",),
                "reference_image":     ("IMAGE",),
                "reference_image_url": ("STRING", {"default": "", "multiline": False}),
            },
        }

    RETURN_TYPES = _VIDEO_RETURN_TYPE
    RETURN_NAMES = _VIDEO_RETURN_NAME
    FUNCTION = "generate"
    CATEGORY = "MyteamOne/Seedance"

    def generate(self, client, prompt, model, resolution, ratio, duration,
                 generate_audio, watermark, seed,
                 video_url="", video=None, reference_image=None, reference_image_url=""):
        _check_fast_resolution(model, resolution)
        # ---- Source video (required) — MUST be a hosted HTTP/HTTPS URL ----
        # MyteamOne's `media[].url` only accepts real URLs. base64 data URIs
        # for video are NOT supported (they time out / 500). So we fail fast
        # instead of wasting minutes uploading a doomed request.
        if video_url.strip():
            src_url = video_url.strip()
        elif video is not None:
            raise ValueError(
                "MyteamOne only accepts a hosted HTTP/HTTPS video URL for "
                "Video-to-Video. Sending a wired VIDEO as base64 is NOT "
                "supported — it times out or returns a server error.\n\n"
                "Fix: upload your video to any host that gives a direct link "
                "(Aliyun OSS, Tencent COS, etc.), paste that URL into the "
                "'video_url' field, and leave the 'video' input unwired."
            )
        else:
            raise ValueError(
                "Video-to-Video needs a source video. Fill 'video_url' with a "
                "public HTTP/HTTPS video URL."
            )

        media = [{"type": "video", "url": src_url}]

        # ---- Optional reference image ----
        if reference_image is not None:
            media.append({"type": "image", "url": image_to_data_uri(reference_image)})
        elif reference_image_url.strip():
            media.append({"type": "image", "url": reference_image_url.strip()})

        payload = {
            "model": MODEL_MAP[model],
            "prompt": prompt,
            "media": media,
            "resolution": resolution,
            "ratio": ratio,
            "duration": duration,
            "generate_audio": generate_audio,
            "watermark": watermark,
        }
        if seed > 0:
            payload["seed"] = seed

        task_id = client.create_task(payload)
        result  = client.poll_task(task_id)
        return _save_result(client, result, task_id)


# ============================================================
# Node 6: Seedance 2.0 Multi-Modal Reference
# ============================================================
#
# Seedance 2.0's own multi-reference mode:
#   - reference materials are described in NATURAL LANGUAGE in the prompt
#     (e.g. "参考图片中的人物，结合视频中的动作节奏"), NOT as 图1/图2
#   - can mix images + video + audio
#   - keeps Seedance params: resolution (lowercase p), ratio (incl. adaptive),
#     generate_audio, watermark, seed
#
# Images are sent as base64 via the official content[] format (proven to work
# in I2V). Video/audio references must be hosted HTTP/HTTPS URLs (base64 video
# does not work with this API).

class MyteamOneSeedance20MultiRef:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "client":         ("MYTEAMONE_CLIENT",),
                "prompt":         ("STRING", {
                    "multiline": True,
                    "default": "参考图片中的角色，在温暖的室内场景中自然对话，镜头缓慢推进",
                }),
                "model":          (list(MODEL_MAP.keys()), {"default": "Seedance 2.0"}),
                "resolution":     (RESOLUTIONS, {"default": "720p"}),
                "ratio":          (RATIOS,      {"default": "9:16"}),
                "duration":       ("INT", {"default": 5, "min": 4, "max": 15, "step": 1}),
                "generate_audio": ("BOOLEAN", {"default": True}),
                "watermark":      ("BOOLEAN", {"default": False}),
                "seed":           ("INT", {"default": 0, "min": 0, "max": 2**31 - 1}),
            },
            "optional": {
                # Reference images (base64). Describe them in the prompt with
                # natural language, e.g. "参考图片中的人物 / 第一张图的服装".
                "image_1":   ("IMAGE",),
                "image_2":   ("IMAGE",),
                "image_3":   ("IMAGE",),
                "image_4":   ("IMAGE",),
                "image_5":   ("IMAGE",),
                # Optional reference video / audio — MUST be hosted URLs.
                "video_url": ("STRING", {"default": "", "multiline": False}),
                "audio_url": ("STRING", {"default": "", "multiline": False}),
            },
        }

    RETURN_TYPES = _VIDEO_RETURN_TYPE
    RETURN_NAMES = _VIDEO_RETURN_NAME
    FUNCTION = "generate"
    CATEGORY = "MyteamOne/Seedance2.0"

    def generate(self, client, prompt, model, resolution, ratio, duration,
                 generate_audio, watermark, seed,
                 image_1=None, image_2=None, image_3=None, image_4=None, image_5=None,
                 video_url="", audio_url=""):
        _check_fast_resolution(model, resolution)

        # media[] format — the correct shape for multi-reference. Each image
        # is {"type":"image","url":...} with NO role (content[] would demand a
        # role and only allows first_frame/last_frame). prompt is top-level.
        media = []

        ref_images = [image_1, image_2, image_3, image_4, image_5]
        for idx, img in enumerate(ref_images, start=1):
            if img is None:
                continue
            print(f"[MyteamOne] Seedance MultiRef: encoding image_{idx}")
            media.append({"type": "image", "url": image_to_data_uri(img)})

        if video_url.strip():
            print(f"[MyteamOne] Seedance MultiRef: using video_url {video_url.strip()}")
            media.append({"type": "video", "url": video_url.strip()})

        if audio_url.strip():
            print(f"[MyteamOne] Seedance MultiRef: using audio_url {audio_url.strip()}")
            media.append({"type": "audio", "url": audio_url.strip()})

        if not media:
            raise ValueError(
                "Seedance Multi-Reference needs at least one reference. Wire an "
                "IMAGE into image_1~5, or fill video_url / audio_url. "
                "(For pure text-to-video use the T2V node instead.)"
            )

        payload = {
            "model":          MODEL_MAP[model],
            "prompt":         prompt,
            "media":          media,
            "resolution":     resolution,
            "ratio":          ratio,
            "duration":       duration,
            "generate_audio": generate_audio,
            "watermark":      watermark,
        }
        if seed > 0:
            payload["seed"] = seed

        task_id = client.create_task(payload)
        result  = client.poll_task(task_id)
        return _save_result(client, result, task_id)


# ============================================================
# Registration
# ============================================================

NODE_CLASS_MAPPINGS = {
    "MyteamOneClient":        MyteamOneClientNode,
    "MyteamOneSeedance20T2V": MyteamOneSeedance20T2V,
    "MyteamOneSeedance20I2V": MyteamOneSeedance20I2V,
    "MyteamOneSeedance20V2V": MyteamOneSeedance20V2V,
    "MyteamOneSeedance20MultiRef": MyteamOneSeedance20MultiRef,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MyteamOneClient":        "MyteamOne API Client",
    "MyteamOneSeedance20T2V": "MyteamOne · Seedance 2.0 (Text to Video)",
    "MyteamOneSeedance20I2V": "MyteamOne · Seedance 2.0 (Image to Video)",
    "MyteamOneSeedance20V2V": "MyteamOne · Seedance 2.0 (Video to Video)",
    "MyteamOneSeedance20MultiRef": "MyteamOne · Seedance 2.0 (Multi-Reference)",
}
