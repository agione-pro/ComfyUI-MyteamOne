# ComfyUI-MyteamOne

ComfyUI custom nodes for **ByteDance Seedance 2.0** video generation, backed by
the [MyteamOne](https://myteamone.agione.pro/) API — a third-party reseller
that offers Seedance 2.0 (standard + Fast) at lower cost than the official
Volcengine pricing.

## ✨ Features

- **Text → Video** (T2V)
- **Image → Video** (I2V, with optional last frame)
- **Video → Video** (V2V, experimental — see notes below)
- **Multi-Reference → Video** — up to 5 images + reference video + reference audio in one shot

All five nodes wrap the Seedance 2.0 / Seedance 2.0 Fast models behind one
shared `MyteamOne API Client` node, so you only configure your key and
endpoints once per workflow.

## 📦 Install

### Option A — ComfyUI Manager

Search for `MyteamOne` in ComfyUI Manager and install. (Available once the
node is published to the ComfyUI Registry.)

### Option B — Manual

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/YOUR_GH_USERNAME/ComfyUI-MyteamOne
cd ComfyUI-MyteamOne
pip install -r requirements.txt
```

Restart ComfyUI. The five nodes appear under `Add Node → MyteamOne/Seedance2.0`.

## 🔑 Setup

1. Register at [myteamone.agione.pro](https://myteamone.agione.pro/) and get
   an API key (looks like `ak-xxxxxxxx...`).
2. In your workflow, drop a **MyteamOne API Client** node and fill in:
   - `api_key`  — your `ak-...` key
   - `base_url` — `https://myteamone.agione.pro/hyperone/xapi/api/v1`
   - `create_path` — `/videos`
   - `poll_path`  — `https://myteamone.agione.pro/hyperone/xapi/api/videos/generations/task/{taskid}`
3. Wire the `client` output into any of the four generation nodes.

> Endpoints may change. If the Client node returns 404, check the latest
> URL with MyteamOne support.

## 🎬 The five nodes

| Node | Use case |
| --- | --- |
| `MyteamOne API Client` | Configure key/endpoints once per workflow |
| `Seedance 2.0 (Text to Video)` | Pure prompt → video |
| `Seedance 2.0 (Image to Video)` | First frame (+ optional last frame) → video |
| `Seedance 2.0 (Video to Video)` | Reference video → restyled video. **Experimental — see notes** |
| `Seedance 2.0 (Multi-Reference)` | Up to 5 character/scene images + reference video + reference audio in natural-language prompt |

## 🧠 Tips

### Multi-Reference prompts use natural language
Seedance 2.0's multi-reference mode does **not** use "图1/图2" style
ordinals. Describe the references naturally in the prompt — *"参考第一张图
的角色，在第二张图的场景里…"* — and the model figures out which is which.

### Keep reference images clean
Never feed storyboard frames with arrows, callouts, or labels drawn on them.
The model will faithfully reproduce those annotations *as on-screen graphics*
in the generated video. Use bare character / scene art only.

### Real-person video is blocked
ByteDance content policy rejects videos containing real, identifiable
people when accessed via third-party APIs (you'll see
`InputVideoSensitiveContentDetected.PrivacyInformation`). This is a hard
limit at the model layer, not a node bug. For drama production, use
**AI-generated** characters end-to-end.

### Seedance 2.0 Fast does not support 1080p
The nodes fail fast with a clear message if you pick Fast + 1080p. Use
720p (or 480p) with Fast, or switch to standard Seedance 2.0 for 1080p.

### Reference videos and audio must be hosted URLs
The `media[].url` field accepts HTTP/HTTPS URLs only — base64 video doesn't
work. Host your videos / audio on Aliyun OSS, Tencent COS, Qiniu, etc., and
paste the direct link into `video_url` / `audio_url`. Reference *images*
work fine via base64 (wire a ComfyUI IMAGE directly).

## 📝 Changelog

### 0.3.0
- Added **Seedance 2.0 Multi-Reference** node (up to 5 images + ref video + ref audio)
- Switched all multi-modal nodes to the documented `media[]` payload format
- Fast + 1080p now fails fast with a clear error message
- Updated model IDs to current dreamina values

### 0.2.0
- Text-to-Video, Image-to-Video, Video-to-Video nodes
- API Client node with configurable endpoints

## ⚖️ License

MIT — see [LICENSE](LICENSE).

## 🙏 Acknowledgements

- ByteDance for the Seedance 2.0 model
- MyteamOne for the API access
- The ComfyUI community
