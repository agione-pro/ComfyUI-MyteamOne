"""
MyteamOne API client — submit a video generation task, poll for completion,
download the result.

Endpoints (third-party reseller of ByteDance Seedance):
  Create: POST {base_url}{create_path}
  Poll:   GET  {poll_path}, with {taskid}/{task_id} substituted in

Defensive response parsing — the backend has shipped slightly different
shapes over time. Both these forms are supported:

  Create response:
    {"requestId": "...", "data": [{"taskId": "cgt-..."}]}
    {"taskId": "cgt-..."}

  Poll response (in-progress):
    {"result": {"data": [], "message": "Task queued!"}, "status": 200, ...}

  Poll response (finished):
    {"result": {"data": [{"url": "https://...mp4"}], "message": "Task executed successfully"}, ...}

Notes
-----
* The create endpoint is slow — even small payloads can take 60–180 seconds
  before returning a task id. The read timeout is set generously.
* On Windows, asyncio sometimes logs `ConnectionResetError [WinError 10054]`
  during connection teardown *after* a successful response. Harmless; ignore.
"""

import json
import os
import time

import requests


class MyteamOneClient:
    def __init__(self, api_key, base_url, create_path, poll_path):
        self.api_key     = api_key
        self.base_url    = base_url.rstrip("/")
        self.create_path = create_path if create_path.startswith("/") else "/" + create_path
        self.poll_path   = poll_path  # full URL template; {taskid} or {task_id} placeholder

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
        })

    # ------------------------------------------------------------------ create

    def create_task(self, payload):
        """Submit a generation task. Returns the task_id (string)."""
        url  = self.base_url + self.create_path
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        print(f"[MyteamOne] POST {url}")
        print(f"[MyteamOne] payload ~{len(body) // 1024} KB")

        resp = self.session.post(
            url,
            data=body,
            timeout=(30, 300),  # (connect, read) — create endpoint is slow
        )

        # Always log the raw response — it's the most useful debugging info
        # when the request fails.
        try:
            raw_text = resp.text
        except Exception:
            raw_text = "<could not read response body>"
        print(f"[MyteamOne] create raw response (status={resp.status_code}): {raw_text}")

        resp.raise_for_status()

        data = resp.json()
        task_id = self._extract_task_id(data)
        if not task_id:
            raise RuntimeError(f"Could not find task_id in response: {data}")
        print(f"[MyteamOne] task_id={task_id}")
        return task_id

    @staticmethod
    def _extract_task_id(data):
        """Find a task id in a few likely shapes."""
        if not isinstance(data, dict):
            return None
        d = data.get("data")
        if isinstance(d, list) and d and isinstance(d[0], dict):
            for key in ("taskId", "task_id", "id"):
                if key in d[0]:
                    return d[0][key]
        for key in ("taskId", "task_id", "id"):
            if key in data:
                return data[key]
        return None

    # -------------------------------------------------------------------- poll

    def poll_task(self, task_id, interval=5, max_wait=900):
        """Poll until success. Returns a dict {'video_url', 'message', 'raw'}."""
        url = self.poll_path.replace("{taskid}", task_id).replace("{task_id}", task_id)
        print(f"[MyteamOne] poll URL: {url}")

        start = time.time()
        first = True
        while True:
            elapsed = int(time.time() - start)
            if elapsed > max_wait:
                raise TimeoutError(
                    f"task {task_id} did not finish within {max_wait}s "
                    f"(last check at {elapsed}s)"
                )

            try:
                resp = self.session.get(url, timeout=(30, 60))
                resp.raise_for_status()
                body = resp.json()
            except requests.exceptions.RequestException as e:
                print(f"[MyteamOne] poll error (will retry): {e}")
                time.sleep(interval)
                continue

            if first:
                print(f"[MyteamOne] first poll body: {body}")
                first = False

            result = body.get("result") if isinstance(body, dict) else None
            if not isinstance(result, dict):
                result = body if isinstance(body, dict) else {}

            video_url = self._first_video_url(result)
            message   = result.get("message", "")

            if video_url:
                print(f"[MyteamOne] succeeded -> {video_url}")
                return {"video_url": video_url, "message": message, "raw": body}

            print(f"[MyteamOne] task={task_id} pending... elapsed={elapsed}s  msg='{message}'")
            time.sleep(interval)

    @staticmethod
    def _first_video_url(result_dict):
        if not isinstance(result_dict, dict):
            return None
        d = result_dict.get("data")
        if isinstance(d, list) and d and isinstance(d[0], dict):
            for key in ("url", "video_url", "videoUrl"):
                if key in d[0]:
                    return d[0][key]
        for key in ("url", "video_url", "videoUrl"):
            if key in result_dict:
                return result_dict[key]
        return None

    # ---------------------------------------------------------------- download

    def download_video(self, video_url, dst_path, timeout=600):
        """Stream-download the finished video to disk."""
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        with self.session.get(video_url, stream=True, timeout=(30, timeout)) as r:
            r.raise_for_status()
            with open(dst_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=256 * 1024):
                    if chunk:
                        f.write(chunk)
        return dst_path
