"""Offline word-level ASR for video-use, using the cached faster-whisper model."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

MODEL = Path("D:/Codex/downloads/whisper-models/small-direct")
PYTHON = Path("D:/Codex/work/video-tools/.venv/Scripts/python.exe")


def run(command: list[str]) -> bytes:
    result = subprocess.run(command, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace")[-2000:])
    return result.stdout


def transcript(video: Path, edit_dir: Path, track: int, language: str | None) -> Path:
    if not video.is_file():
        raise FileNotFoundError(f"video not found: {video}")
    if track < 0:
        raise ValueError("audio track must be zero or greater")
    if not (MODEL / "model.bin").is_file():
        raise FileNotFoundError(f"local Whisper model missing: {MODEL}")
    target_dir = edit_dir / "transcripts"
    target_dir.mkdir(parents=True, exist_ok=True)
    suffix = "" if track == 0 else f".track{track}"
    output = target_dir / f"{video.stem}{suffix}.json"
    if output.exists():
        print(f"cached: {output}")
        return output

    with tempfile.TemporaryDirectory() as temp_dir:
        audio = Path(temp_dir) / "audio.wav"
        run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(video),
             "-map", f"0:a:{track}", "-vn", "-ac", "1", "-ar", "16000",
             "-c:a", "pcm_s16le", str(audio)])
        import numpy as np
        from faster_whisper import WhisperModel

        import wave
        with wave.open(str(audio), "rb") as wav:
            pcm = wav.readframes(wav.getnframes())
        samples = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768
        if not samples.size or not np.any(samples):
            raise RuntimeError(f"audio track {track} is silent")
        model = WhisperModel(str(MODEL), device="cpu", compute_type="int8", cpu_threads=6)
        segments, info = model.transcribe(
            samples, language=language, beam_size=1, word_timestamps=True,
            vad_filter=True,
        )
        words = []
        for segment in segments:
            for word in segment.words or []:
                if words and word.start > words[-1]["end"]:
                    words.append({"start": words[-1]["end"], "end": word.start,
                                  "text": " ", "type": "spacing", "speaker_id": None})
                words.append({"start": word.start, "end": word.end,
                              "text": word.word, "type": "word", "speaker_id": None})
        payload = {"text": "".join(w["text"] for w in words),
                   "language_code": info.language, "words": words}
        temp_output = output.with_suffix(".json.tmp")
        temp_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_output.replace(output)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline local word-level video transcription")
    parser.add_argument("video", type=Path)
    parser.add_argument("--edit-dir", type=Path)
    parser.add_argument("--audio-track", type=int, default=0, help="Zero-based track index")
    parser.add_argument("--language", default=None, help="ISO code, such as vi. Omit to auto-detect.")
    args = parser.parse_args()
    video = args.video.resolve()
    edit_dir = (args.edit_dir or video.parent / "edit").resolve()
    started = time.time()
    try:
        out = transcript(video, edit_dir, args.audio_track, args.language)
        print(f"saved {out} in {time.time() - started:.1f}s")
    except Exception as exc:
        sys.exit(str(exc))


if __name__ == "__main__":
    main()
