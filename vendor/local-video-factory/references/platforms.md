# Current platform and provider references

Verified: **2026-08-31**. Re-check these official sources before changing API payloads or platform checklists. Rules and UI labels can change.

## OpenAI

- Codex skills: https://developers.openai.com/codex/skills
- Structured Outputs: https://developers.openai.com/api/docs/guides/structured-outputs
- Image generation: https://developers.openai.com/api/docs/guides/image-generation
- Model catalog: https://developers.openai.com/api/docs/models/all

Require `OPENAI_TEXT_MODEL` and `OPENAI_IMAGE_MODEL` only for the stages that use them. Do not hard-code a default model or assume account access. Use strict JSON Schema for text artifacts. Generate a supported portrait image and normalize it to 1080×1920 during rendering.

## ElevenLabs

- Model overview: https://elevenlabs.io/docs/overview/models
- Model IDs: https://elevenlabs.io/docs/help-center/technical/how-do-i-find-the-model-id
- TTS with timestamps: https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps/
- Forced alignment: https://elevenlabs.io/docs/api-reference/forced-alignment/create/

`eleven_flash_v2_5` is verified and supports Vietnamese. Prefer `/with-timestamps` so subtitles follow generated audio. For external voiceovers, require supplied SRT timing or paid forced alignment. Never clone or imitate a local accent.

## TikTok

- Commercial Music Library: https://ads.tiktok.com/resources/help/article/how-to-use-the-commercial-music-library?lang=en-GB
- Commercial-content disclosure: https://support.tiktok.com/en/business-and-creator/creator-and-business-accounts/promoting-a-brand-product-or-service
- AI-generated content: https://support.tiktok.com/en/using-tiktok/creating-videos/ai-generated-content
- In-feed specifications/safe zones: https://ads.tiktok.com/resources/help/article/tiktok-auction-in-feed-ads

Treat commercial music rights as verified only for the applicable region/placement or when the user supplies a license. Do not hard-code a universal pixel safe zone; require current overlay/device preview. Include commercial and AI disclosure checks without claiming they guarantee distribution.

## Instagram Reels

- Recommendation guidelines: https://about.fb.com/news/2020/08/recommendation-guidelines/
- Recommendation eligibility: https://help.instagram.com/313829416281232
- Originality: https://about.fb.com/br/news/2024/04/ajudando-o-criador-de-conteudo-a-encontrar-novos-publicos/
- AI labels: https://about.fb.com/news/2024/04/metas-approach-to-labeling-ai-generated-content-and-manipulated-media/

Require original or licensed media, no imported platform watermark, an Account Status check, and current in-app AI disclosure when applicable. Eligibility is a checklist, not a recommendation promise.

## YouTube Shorts

- Upload Shorts: https://support.google.com/youtube/answer/12779649
- Audience setting: https://support.google.com/youtube/answer/9527654
- Altered/synthetic disclosure: https://support.google.com/youtube/answer/14328491

Keep titles at or below 100 characters. The posting checklist must make the publisher choose Made for Kids or Not Made for Kids; never guess. Require altered/synthetic disclosure when realistic generated or materially altered content qualifies.

## FFmpeg

- FFmpeg: https://ffmpeg.org/ffmpeg.html
- ffprobe: https://ffmpeg.org/ffprobe.html
- Filters: https://ffmpeg.org/ffmpeg-filters.html
- MP4/faststart: https://ffmpeg.org/ffmpeg-formats.html

Preflight must find `ffmpeg` and `ffprobe` plus H.264/AAC encoders. Use ffprobe for streams/container metadata, and FFmpeg `blackdetect`/`silencedetect` for content QC.
