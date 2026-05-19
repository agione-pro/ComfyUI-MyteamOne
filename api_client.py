"""
MyteamOne API client.

Endpoints (all configurable from the ComfyUI client node):
  POST  {base_url}{create_path}
  GET   {poll_path}        # may be a full URL with {task_id} / {taskid} placeholder
"""

import re
import time
import requests


def _unwrap(data):
    """Single-level unwrap of {"data": {...}} or single-item list envelopes."""
    if isinstance(data, list):
        if not data:
            return {}
        return _unwrap(data[0])
    if isinstance(data, dict):
        inner = data.get("data")
        if isinstance(inner, (dict, list)):
            return _unwrap(inner)
        return data
    return {}


def _first(data: dict, *keys):
    for k in keys:
        v = data.get(k)
        if v:
            return v
    return None


# Case-insensitive {task_id} / {taskid} / {taskId} substitution.
_TASK_ID_RE = re.compile(r"\{task[_-]?id\}", re.IGNORECASE)


class MyteamOneClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://zh.agione.co/hyperone/xapi/api/v1",
        create_path: str = "/videos",
        poll_path_template: str = "https://agione.cc/hyperone/xapi/api/videos/generations/task/{taskid}",
        timeout: float = 30.0,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.create_path = "/" + create_path.strip("/")
        self.poll_path_template = poll_path_template.strip()
        self.timeout = timeout

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
        )

    # ---------- task lifecycle ----------

    def create_task(self, payload: dict) -> str:
        url = self.base_url + self.create_path
        print(f"[MyteamOne] POST {url}")
        print(f"[MyteamOne] payload={payload}")

        resp = self.session.post(url, json=payload, timeout=self.timeout)
        print(f"[MyteamOne] create raw response (status={resp.status_code}): {resp.text}")
        resp.raise_for_status()

        data = _unwrap(resp.json())
        task_id = _first(
            data,
            "taskId", "task_id", "id",
            "videoId", "video_id",
            "jobId", "job_id",
        )
        if not task_id:
            raise RuntimeError(f"No task id in response (after unwrap): {data}")
        print(f"[MyteamOne] task_id={task_id}")
        return task_id

    def _build_poll_url(self, task_id: str) -> str:
        template = self.poll_path_template
        # If the template doesn't include a placeholder, append /{task_id}
        if not _TASK_ID_RE.search(template):
            template = template.rstrip("/") + "/{task_id}"
        # Substitute placeholder (case-insensitive)
        path = _TASK_ID_RE.sub(task_id, template)
        # Full URL? Use as is. Otherwise prepend base_url.
        if path.startswith("http://") or path.startswith("https://"):
            return path
        if not path.startswith("/"):
            path = "/" + path
        return self.base_url + path

    def poll_task(self, task_id: str, interval: float = 5.0, max_wait: float = 1800.0) -> dict:
        url = self._build_poll_url(task_id)
        print(f"[MyteamOne] poll URL: {url}")

        started = time.time()
        first_dump = True
        while True:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code >= 400:
                print(f"[MyteamOne] poll {resp.status_code} body: {resp.text}")
            resp.raise_for_status()
            raw = resp.json()

            if first_dump:
                print(f"[MyteamOne] first poll body: {raw}")
                first_dump = False

            # ---- Extract video URL from MyteamOne's nested structure ----
            # Successful response shape:
            # {
            #   "result": {
            #     "data": [ { "url": "..." } ],
            #     "message": "Task executed successfully"
            #   },
            #   "status": 200,
            #   ...
            # }
            video_url = None
            result_obj = (raw.get("result") if isinstance(raw, dict) else None) or {}
            data_list = result_obj.get("data") or []
            if isinstance(data_list, list) and data_list:
                first_item = data_list[0] or {}
                if isinstance(first_item, dict):
                    video_url = (
                        first_item.get("url")
                        or first_item.get("video_url")
                        or first_item.get("videoUrl")
                    )

            # Fallbacks for other possible shapes
            if not video_url and isinstance(raw, dict):
                video_url = (
                    raw.get("url")
                    or raw.get("video_url")
                    or raw.get("videoUrl")
                )

            if video_url:
                print(f"[MyteamOne] succeeded → {video_url}")
                return {"video_url": video_url, "raw": raw}

            # Check for explicit failure indicators
            message = (result_obj.get("message") or "").lower()
            if any(kw in message for kw in ("fail", "error", "denied", "rejected")):
                raise RuntimeError(f"Task failed: {raw}")

            elapsed = int(time.time() - started)
            print(f"[MyteamOne] task={task_id} pending... elapsed={elapsed}s  msg={result_obj.get('message')!r}")

            if time.time() - started > max_wait:
                raise TimeoutError(f"Task {task_id} exceeded {max_wait}s")
            time.sleep(interval)

    def download_video(self, url: str, output_path: str) -> str:
        with self.session.get(url, stream=True, timeout=300) as resp:
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
        return output_path
