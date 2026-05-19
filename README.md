# ComfyUI-MyteamOne

> Reliable, on-demand **Seedance 2.0** video generation for ComfyUI — powered by [MyteamOne](https://myteamone.com).

[![Registry](https://img.shields.io/badge/ComfyUI-Registry-blue)](https://registry.comfy.org/nodes/comfyui-myteamone)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

No queue. No throttling. Cinema-quality video directly inside your workflow.

## Features

- 🎬 Seedance 2.0 Text-to-Video (Seedance 2.0 / Seedance 2.0 Fast)
- 🔊 Native audio-video sync with lip-sync support
- 📐 480p / 720p / 1080p, 16:9 / 9:16 / 1:1 / 4:3 / 3:4 / 21:9
- ⚡ Async tasks with progress logged in console
- 🔌 Drop-in compatible with native Save Video and VHS nodes

## Install

### Via ComfyUI Manager (recommended)

1. Open ComfyUI Manager
2. Custom Nodes Manager → search **MyteamOne** → Install
3. Restart ComfyUI

### Via Git

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/YOUR_GH_USER/ComfyUI-MyteamOne
cd ComfyUI-MyteamOne
pip install -r requirements.txt
```

## Quick Start

1. Get an API key at [myteamone.com](https://myteamone.com) (starts with `mto_…`)
2. Right-click canvas → Add Node → MyteamOne → MyteamOne API Client, paste your key
3. Add Node → MyteamOne/Seedance → MyteamOne · Seedance 2.0 (Text to Video)
4. Wire `client → client`, then wire `video` to Save Video
5. Write your prompt and run

## License

MIT — see [LICENSE](LICENSE).
