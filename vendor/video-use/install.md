---
name: video-use-install
description: Set up the local video-use editor and its faster-whisper transcription dependency.
---

# video-use install

Read this only for first-time install or reconnect. For editing, read `SKILL.md` and the scripts in `helpers/`.

## Requirements

- Python 3.10+ and `uv`
- `ffmpeg` and `ffprobe` on `PATH`
- A local faster-whisper model directory containing `model.bin`
- The whole repo discoverable as a skill, with `helpers/` beside `SKILL.md`

This Work Hub uses `D:/Codex/downloads/whisper-models/small-direct`. The model is already cached. Do not download another model automatically. Override the path with `VIDEO_USE_WHISPER_MODEL` if needed.

## Setup

```powershell
uv sync
ffmpeg -version
ffprobe -version
uv run python helpers/transcribe.py --help
```

For this workspace, the repo is at `D:/Codex/work/local-tools/video-use` and registered through `.agents/skills/video-use`. Transcription runs on CPU with int8 quantization. Audio stays local; no API key is required. VoiceStudio may be used separately to generate narration, but is not the ASR provider for this helper.

Do not transcribe footage during installation. On the first actual job, transcribe only the user's selected footage and save results under that footage folder's `edit/` directory.

## Use

Open the Work Hub workspace, point `video-use` at a folder containing the source clips, and ask it to inventory the footage and propose a strategy. Wait for the user's approval before cutting. All project and render outputs belong in `<videos_dir>/edit/`.
