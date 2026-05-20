"""
ComfyUI nodes for MyteamOne Seedance 2.0.
"""

import os

from .api_client import MyteamOneClient

try:
    from comfy_api.input_impl import VideoFromFile  # type: ignore
    HAS_VIDEO_TYPE = True
except Exception:
    HAS_VIDEO_TYPE = False


MODEL_MAP = {
    "Seedance 2.0":      "bytedance/dreamina-seedance-2-0-260128/f29d3",       # TODO: verify
    "Seedance 2.0 Fast": "bytedance/dreamina-seedance-2-0-fast-260128/f29d3",  # confirmed
}


DEFAULT_BASE_URL    = "https://zh.agione.co/hyperone/xapi/api/v1"
DEFAULT_CREATE_PATH = "/videos"
DEFAULT_POLL_URL    = "https://agione.cc/hyperone/xapi/api/videos/generations/task/{taskid}"


# ---------- Node 1: client ----------

class MyteamOneClientNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "api_key":     ("STRING", {"default": "mto_xxxxxxxxxxxx", "multiline": False}),
                "base_url":    ("STRING", {"default": DEFAULT_BASE_URL,    "multiline": False}),
                "create_path": ("STRING", {"default": DEFAULT_CREATE_PATH, "multiline": False}),
                "poll_path":   ("STRING", {"default": DEFAULT_POLL_URL,    "multiline": False}),
            }
        }

    RETURN_TYPES = ("MYTEAMONE_CLIENT",)
    RETURN_NAMES = ("client",)
    FUNCTION = "build"
    CATEGORY = "MyteamOne"

    def build(self, api_key, base_url, create_path, poll_path):
        if not api_key or api_key.startswith("mto_xxx"):
            raise ValueError("Please set a real MyteamOne API key.")
        return (
            MyteamOneClient(
                api_key=api_key,
                base_url=base_url,
                create_path=create_path,
                poll_path_template=poll_path,
            ),
        )


# ---------- Node 2: Seedance 2.0 Text-to-Video ----------

class MyteamOneSeedance20T2V:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "client":         ("MYTEAMONE_CLIENT",),
                "prompt":         ("STRING", {"multiline": True, "default": "A cinematic shot of a cat walking in a sunlit garden"}),
                "model":          (list(MODEL_MAP.keys()), {"default": "Seedance 2.0 Fast"}),
                "resolution":     (["480p", "720p", "1080p"], {"default": "720p"}),
                "ratio":          (["16:9", "9:16", "1:1", "4:3", "3:4", "21:9"], {"default": "16:9"}),
                "duration":       ("INT", {"default": 5, "min": 5, "max": 15, "step": 5}),
                "generate_audio": ("BOOLEAN", {"default": True}),
                "seed":           ("INT", {"default": 0, "min": 0, "max": 2**31 - 1}),
            }
        }

    RETURN_TYPES = ("VIDEO",) if HAS_VIDEO_TYPE else ("STRING",)
    RETURN_NAMES = ("video",) if HAS_VIDEO_TYPE else ("video_path",)
    FUNCTION = "generate"
    CATEGORY = "MyteamOne/Seedance"

    def generate(self, client, prompt, model, resolution, ratio, duration, generate_audio, seed):
        api_model = MODEL_MAP[model]

        payload = {
            "model": api_model,
            "prompt": prompt,
            "resolution": resolution,
            "ratio": ratio,
            "duration": duration,
            "generate_audio": generate_audio,
        }
        if seed > 0:
            payload["seed"] = seed

        task_id = client.create_task(payload)
        result  = client.poll_task(task_id)

        video_url = result.get("video_url")
        if not video_url:
            raise RuntimeError(f"No video URL in success response: {result}")

        import folder_paths
        output_dir = folder_paths.get_output_directory()
        os.makedirs(output_dir, exist_ok=True)
        filename = f"myteamone_seedance_{task_id}.mp4"
        output_path = os.path.join(output_dir, filename)
        client.download_video(video_url, output_path)
        print(f"[MyteamOne] saved → {output_path}")

        if HAS_VIDEO_TYPE:
            return (VideoFromFile(output_path),)
        return (output_path,)


NODE_CLASS_MAPPINGS = {
    "MyteamOneClient":        MyteamOneClientNode,
    "MyteamOneSeedance20T2V": MyteamOneSeedance20T2V,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MyteamOneClient":        "MyteamOne API Client",
    "MyteamOneSeedance20T2V": "MyteamOne · Seedance 2.0 (Text to Video)",
}
