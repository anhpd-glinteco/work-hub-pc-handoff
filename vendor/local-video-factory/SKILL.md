---
name: local-video-factory
description: Turn a verified Vietnamese local-business brief into a resumable 10–60 second vertical-video production job, including scripts, retention plans, media/audio preparation, rendering, manual-post packages, and offline performance learning. Use for homemade-food or milk-tea TikTok, Instagram Reels, and YouTube Shorts work; do not use for auto-posting or viral predictions.
---

# Local Video Factory

Collect one factual brief, then run the deterministic CLI. Do not invent prices, offers, products, delivery terms, hours, health claims, or content rights.

## Route the job

- For `profile: homemade`, read [references/homemade.md](references/homemade.md).
- For `profile: milk-tea`, read [references/milk-tea.md](references/milk-tea.md).
- Before platform packaging, AI media, TTS, or rendering, read [references/platforms.md](references/platforms.md).

## Run the workflow

Use `python scripts/video_factory.py` with one of these subcommands:

- `new`: initialize `.env.example`, `briefs/`, `outputs/`, and one non-overwriting brief.
- `dry-run`: validate and print the production plan without writing outputs or making network requests.
- `run --review`: generate, gate, judge, and revise scripts, then stop at `waiting_review`.
- `run --auto`: continue only when a candidate passes every hard gate and the editorial threshold.
- `resume`: reuse valid fingerprints, select a reviewed candidate, or regenerate only stale work.
- `learn`: analyze a manual metrics export offline; never call an API.

Every network-backed stage requires the user to pass `--allow-paid` for that invocation. Missing authorization, credentials, models, media, rights, timing, or FFmpeg must become `needs_input`; never silently substitute fabricated content or a placeholder final video.

Keep posting manual. Describe scores as editorial quality, comparisons as observed and directional, and never promise reach, recommendation, trending, or virality.
