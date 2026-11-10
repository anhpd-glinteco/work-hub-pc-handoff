"""Transcribe a video locally with faster-whisper.

Extracts mono 16kHz audio via ffmpeg and writes word-level timestamps to
<edit_dir>/transcripts/<video_stem>.json. No audio leaves this machine.

Cached: if the output file already exists, inference is skipped.

Usage:
    python helpers/transcribe.py <video_path>
    python helpers/transcribe.py <video_path> --edit-dir /custom/edit
    python helpers/transcribe.py <video_path> --language en
"""

from __future__ import annotations

import argparse
import array
from functools import lru_cache
import json
import math
import os
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

import numpy as np

WHISPER_MODEL = Path(os.environ.get(
    "VIDEO_USE_WHISPER_MODEL",
    "D:/Codex/downloads/whisper-models/small-direct",
))


def count_audio_tracks(video_path: Path) -> int:
    """How many audio streams the container holds."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=index", "-of", "csv=p=0", str(video_path)],
        capture_output=True, text=True,
    )
    return len([ln for ln in out.stdout.splitlines() if ln.strip()])


def peak_dbfs(wav_path: Path) -> float:
    """Peak level of a 16-bit PCM wav, in dBFS. -inf for digital silence."""
    peak = 0
    with wave.open(str(wav_path), "rb") as w:
        # A chunk at a time: batch mode runs several of these at once, and a two-hour
        # take is 230 MB of 16 kHz mono before the array copy doubles it.
        while frames := w.readframes(1 << 16):
            samples = array.array("h", frames)
            peak = max(peak, max(samples), -min(samples))
    return 20 * math.log10(peak / 32768) if peak > 0 else float("-inf")


def extract_audio(video_path: Path, dest: Path, audio_track: int = 0) -> None:
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-map", f"0:a:{audio_track}",
        "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
        str(dest),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def read_audio(wav_path: Path) -> np.ndarray:
    with wave.open(str(wav_path), "rb") as audio:
        if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) != (1, 2, 16000):
            raise RuntimeError("Expected extracted mono 16 kHz, 16-bit PCM audio")
        pcm = audio.readframes(audio.getnframes())
    return np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0


@lru_cache(maxsize=1)
def whisper_model():
    if not (WHISPER_MODEL / "model.bin").is_file():
        raise FileNotFoundError(
            f"Whisper model not found at {WHISPER_MODEL}; set VIDEO_USE_WHISPER_MODEL "
            "to a local faster-whisper model directory. Models are not downloaded automatically."
        )
    from faster_whisper import WhisperModel
    # shortcut: small CPU model has no diarization and may miss fillers; upgrade to a local diarizing model when speaker labels matter.
    return WhisperModel(str(WHISPER_MODEL), device="cpu", compute_type="int8", cpu_threads=6)


def call_whisper(audio_path: Path, language: str | None = None) -> dict:
    segments, info = whisper_model().transcribe(
        read_audio(audio_path), language=language, beam_size=1, word_timestamps=True, vad_filter=True,
    )
    segments = list(segments)
    words = [
        {"text": word.word.strip(), "start": word.start, "end": word.end, "type": "word"}
        for segment in segments
        for word in (segment.words or [])
        if word.word.strip()
    ]
    if any(segment.text.strip() for segment in segments) and not words:
        raise RuntimeError("Whisper returned speech without word timestamps; refusing imprecise cuts")
    return {
        "text": " ".join(segment.text.strip() for segment in segments).strip(),
        "language": info.language,
        "duration": info.duration,
        "words": words,
        "segments": [
            {"start": s.start, "end": s.end, "text": s.text.strip()}
            for s in segments
        ],
        "provider": "faster-whisper-local",
    }


def transcript_path(edit_dir: Path, video: Path, audio_track: int = 0) -> Path:
    """Where a video's transcript lands.

    The track belongs in the name, or a rerun with --audio-track hands back the transcript of
    the track it is meant to replace. Track 0 keeps the plain name, so transcripts made before
    the flag existed stay valid. Batch mode tests its cache with this too — one function, so
    the two cannot drift apart.
    """
    suffix = "" if audio_track == 0 else f".track{audio_track}"
    return edit_dir / "transcripts" / f"{video.stem}{suffix}.json"


def transcribe_one(
    video: Path,
    edit_dir: Path,
    language: str | None = None,
    verbose: bool = True,
    audio_track: int = 0,
) -> Path:
    """Transcribe a single video. Returns path to transcript JSON.

    Cached: returns existing path immediately if the transcript already exists.
    """
    transcripts_dir = edit_dir / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    out_path = transcript_path(edit_dir, video, audio_track)

    if out_path.exists():
        if verbose:
            print(f"cached: {out_path.name}")
        return out_path

    if verbose:
        print(f"  extracting audio from {video.name}", flush=True)

    n_tracks = count_audio_tracks(video)
    if n_tracks > 1 and verbose:
        print(f"  note: {video.name} has {n_tracks} audio tracks, using track "
              f"{audio_track + 1} (--audio-track to change)", flush=True)

    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        audio = Path(tmp) / f"{video.stem}.wav"
        extract_audio(video, audio, audio_track)

        # Avoid wasting local inference on a silent or incorrectly selected track.
        peak = peak_dbfs(audio)
        if peak < -60.0:
            raise RuntimeError(
                f"track {audio_track + 1} of {video.name} is silent "
                f"(peak {peak:.1f} dBFS) - not transcribing. "
                + (f"The file has {n_tracks} audio tracks; try --audio-track "
                   + " or ".join(str(i) for i in range(n_tracks) if i != audio_track) + "."
                   if n_tracks > 1 else "Check the source audio.")
            )

        size_mb = audio.stat().st_size / (1024 * 1024)
        if verbose:
            print(f"  transcribing locally with faster-whisper ({size_mb:.1f} MB audio)", flush=True)
        payload = call_whisper(audio, language)

    out_path.write_text(json.dumps(payload, indent=2))
    dt = time.time() - t0

    if verbose:
        kb = out_path.stat().st_size / 1024
        print(f"  saved: {out_path.name} ({kb:.1f} KB) in {dt:.1f}s")
        if isinstance(payload, dict) and "words" in payload:
            print(f"    words: {len(payload['words'])}")

    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description="Transcribe a video locally with faster-whisper")
    ap.add_argument("video", type=Path, help="Path to video file")
    ap.add_argument(
        "--edit-dir",
        type=Path,
        default=None,
        help="Edit output directory (default: <video_parent>/edit)",
    )
    ap.add_argument(
        "--language",
        type=str,
        default=None,
        help="Optional ISO language code (e.g., 'en'). Omit to auto-detect.",
    )
    ap.add_argument(
        "--audio-track",
        type=int,
        default=0,
        help="Zero-based audio track to transcribe. OBS writes the game on track 0 "
             "and the mic on track 1; without this ffmpeg applies its default audio "
             "stream selection, which picks the track with the most channels.",
    )
    args = ap.parse_args()

    video = args.video.resolve()
    if not video.exists():
        sys.exit(f"video not found: {video}")

    edit_dir = (args.edit_dir or (video.parent / "edit")).resolve()

    transcribe_one(
        video=video,
        edit_dir=edit_dir,
        language=args.language,
        audio_track=args.audio_track,
    )


if __name__ == "__main__":
    main()
