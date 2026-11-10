# Prompt v3 — Xây dựng Codex skill `local-video-factory`

## 0. Vai trò và mục tiêu

Bạn là Senior Python Engineer, Codex Skill Author, Prompt Engineer và Producer video dọc ngắn cho doanh nghiệp địa phương tại Việt Nam.

Hãy xây dựng, kiểm thử và cài một Codex skill cá nhân tên `local-video-factory`.

Đây là meta-prompt yêu cầu xây một workflow chạy được. Không trả lời bằng một kịch bản video mẫu và không tạo web app.

Skill nhận brief một lần và điều phối toàn bộ quy trình:

Brief → Ý tưởng → Hook 0–3 giây → Kịch bản → Retention Plan → Storyboard → Media/Audio → Phụ đề → Render → Gói đăng thủ công → Học từ metrics thật.

Mục tiêu là tăng xác suất người đúng tệp dừng xem, tiếp tục xem và thực hiện một hành động có giá trị. Không tuyên bố hoặc ngụ ý rằng workflow, AI score hay format có thể bảo đảm viral/trending.

Thứ tự ưu tiên khi chỉ dẫn xung đột:

1. An toàn, trung thực và quyền sử dụng nội dung.
2. Không bịa dữ liệu thương mại.
3. Output chạy được, kiểm tra được và resume được.
4. Retention, platform fit và khả năng sản xuất.
5. Chi phí thấp và cấu trúc tối giản.

## 1. Phạm vi

Hỗ trợ video dọc 9:16, dài 10–60 giây, cho:

- `homemade`: đồ ăn homemade; chiến dịch đầu tiên là bánh Trung thu.
- `milk-tea`: quán trà sữa có chỗ ngồi, đồ ăn vặt và giao hàng trong xã trước ca tối.

Mỗi job chỉ có một nền tảng:

- `tiktok`
- `instagram-reels`
- `youtube-shorts`

Mỗi job có một `distribution_mode`:

- `organic`
- `paid`
- `boosted`

Không dùng hướng dẫn quảng cáo trả phí như một tuyên bố chắc chắn về phân phối organic.

Ngoài phạm vi MVP:

- Video dài trên 60 giây.
- Web app, server, database, queue hoặc plugin.
- Tự đăng video lên mạng xã hội.
- Tự tải video/audio từ nội dung tham chiếu.
- Voice cloning.
- Tự thu thập dữ liệu người xem từ API nền tảng.
- Dự đoán lượt xem hoặc xác suất viral.

## 2. Cách thực hiện

- Đọc `AGENTS.md` áp dụng cho workspace.
- Kiểm tra code hoặc skill tương tự trước khi viết.
- Dùng skill `skill-creator` nếu có.
- Dùng Python CLI duy nhất để điều phối.
- Ưu tiên thư viện chuẩn và dependency đã cài.
- Trước khi dùng OpenAI, ElevenLabs hoặc quy tắc nền tảng, xác minh tài liệu chính thức hiện hành.
- Ghi URL nguồn và ngày xác minh trong `references/platforms.md`.
- Không hard-code model name chưa được xác minh.
- Không ghi secret hoặc nội dung `.env` vào source, prompt, log, report hay Git.
- Không gọi API trả phí trong lúc xây và test.
- Runtime chỉ được gọi API trả phí khi người dùng truyền `--allow-paid`.
- `dry-run` tuyệt đối không request mạng.

## 3. Cấu trúc skill

```text
local-video-factory/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── scripts/
│   ├── video_factory.py
│   └── test_video_factory.py
└── references/
    ├── homemade.md
    ├── milk-tea.md
    └── platforms.md
```

Không tạo README, package Python, web UI hoặc file dự phòng “cho tương lai”.

Core pipeline không được chứa logic nội dung rải rác theo niche. Quy tắc niche nằm trong các reference tương ứng.

## 4. Workspace của job

Mỗi lệnh nhận:

```text
--workspace <path>
```

Nếu không truyền, dùng thư mục hiện tại.

```text
<workspace>/
├── .env.example
├── briefs/
└── outputs/
```

Tạo `.env.example` nếu chưa tồn tại; không ghi đè file có sẵn và không tự tạo `.env`.

```env
OPENAI_API_KEY=
OPENAI_TEXT_MODEL=
OPENAI_IMAGE_ENABLED=false
OPENAI_IMAGE_MODEL=
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=
ELEVENLABS_MODEL=eleven_flash_v2_5
VIDEO_BGM_PATH=
SUBTITLE_FONT_PATH=
VIDEO_FPS=30
```

## 5. CLI

```powershell
python scripts/video_factory.py new `
  --profile homemade `
  --platform tiktok `
  --variants 3 `
  --topic "Bánh Trung thu homemade cho gia đình" `
  --workspace ".\local-video-work"

python scripts/video_factory.py run `
  --brief ".\local-video-work\briefs\brief.json" `
  --review `
  --allow-paid

python scripts/video_factory.py run `
  --brief ".\local-video-work\briefs\brief.json" `
  --auto `
  --allow-paid

python scripts/video_factory.py resume `
  --job ".\local-video-work\outputs\<job-id>" `
  --candidate-id "<candidate-id>" `
  --allow-paid

python scripts/video_factory.py resume `
  --job ".\local-video-work\outputs\<job-id>" `
  --candidate-id "<candidate-id>" `
  --voiceover-dir ".\recorded-voice"

python scripts/video_factory.py dry-run `
  --brief ".\local-video-work\briefs\brief.json"

python scripts/video_factory.py learn `
  --job ".\local-video-work\outputs\<job-id>" `
  --metrics ".\metrics-after-72h.json"
```

Quy ước:

- `candidate_count` luôn là 4 ứng viên biên tập nội bộ.
- `--variants` là số biến thể sản xuất/thử nghiệm, chỉ nhận `1` hoặc `3`.
- Không gọi hai khái niệm này bằng cùng một tên trong code hoặc report.
- `new` chỉ tạo brief.
- `dry-run` chỉ kiểm tra và lập kế hoạch.
- `run --review` dừng sau Script Gate.
- `run --auto` chỉ đi tiếp khi có ứng viên hợp lệ.
- Không cho phép đồng thời `--auto` và `--review`.
- `--force` chỉ hợp lệ với `resume --candidate-id`.
- `--force` có thể bỏ qua ngưỡng điểm biên tập, nhưng không bao giờ bỏ qua lỗi facts, quyền sử dụng, CTA sai hoặc safety.
- Nếu thiếu `--allow-paid`, mọi bước cần API chuyển thành `needs_input`, không tự request.

## 6. Brief đầu vào

```json
{
  "profile": "homemade",
  "platform": "tiktok",
  "distribution_mode": "organic",
  "campaign_goal": "reach",
  "primary_metric": "shares_per_view",
  "variant_count": 3,
  "duration_range_seconds": {"min": 15, "max": 35},

  "topic": "",
  "brand_name": "",
  "location": "",
  "target_customer": "",
  "audience_problem_or_desire": "",
  "single_promise": "",
  "tone": "",
  "pace_profile": "auto",
  "allow_goal_fallback": false,

  "featured_products": [],
  "menu": [],
  "prices": [],
  "real_selling_points": [],
  "proof_available": [],

  "promotion": {
    "name": "",
    "details": "",
    "conditions": "",
    "deadline": ""
  },

  "delivery": {
    "area": "",
    "order_time": "",
    "delivery_time": "",
    "fee": ""
  },

  "shop": {
    "address": "",
    "opening_hours": "",
    "has_dine_in": false
  },

  "order_method": "",
  "contact": "",

  "search_context": {
    "primary_keyword": "",
    "secondary_keywords": []
  },

  "trend_context": {
    "mode": "evergreen",
    "region": "VN",
    "observed_at": "",
    "references": [
      {
        "url": "",
        "description": "",
        "pattern_to_adapt": "",
        "sound_name": "",
        "audio_allowed_use": ""
      }
    ]
  },

  "available_media": [
    {
      "path": "media/mooncake-cut.jpg",
      "type": "image",
      "description": "Bánh thật đã cắt, thấy phần nhân",
      "product": "bánh Trung thu",
      "allowed_use": "advertising"
    }
  ],

  "voiceover_preference": "auto",
  "notes": ""
}
```

Quy tắc:

- Không bịa giá, món, ưu đãi, deadline, giờ mở cửa, giao hàng, claim sức khỏe hoặc chất lượng.
- Mọi fact thương mại phải trỏ về một `brief_path` không rỗng.
- Media phải tồn tại, đọc được và có `allowed_use: advertising`.
- Không suy luận nội dung ảnh chỉ từ tên file.
- `trend_context.mode=referenced-trend` chỉ hợp lệ khi có nguồn và thời điểm quan sát.
- Trend reference không đồng nghĩa với quyền tải lại hình hoặc audio.
- Khi thiếu dữ liệu bắt buộc cho mục tiêu bán hàng, trả `needs_input`.
- Chỉ đổi sang awareness khi `allow_goal_fallback=true`; phải ghi rõ mục tiêu đã thay đổi và lý do.
- `duration_range_seconds` nằm trong 10–60 giây.
- `primary_metric` phải phù hợp mục tiêu và có thể đo được.

## 7. Pipeline và manifest

Pipeline:

1. `preflight_and_normalize`
2. `generate_candidates`
3. `script_hard_gate`
4. `editorial_judge_and_revision`
5. `select_or_review`
6. `create_experiment_variants`
7. `create_variant_production_plans`
8. `prepare_media_and_audio`
9. `subtitles_and_render`
10. `technical_qc`
11. `post_package`
12. `learn` — tùy chọn sau khi đăng thủ công

Trạng thái:

- `pending`
- `completed`
- `failed`
- `waiting_review`
- `needs_input`

Manifest không lưu secret. Mỗi output có fingerprint đủ để phát hiện file bị mất hoặc hỏng.

`resume`:

- Bỏ qua output còn hợp lệ.
- Chạy lại bước hỏng.
- Invalidate đúng các bước phụ thuộc phía sau.
- Không tạo lại asset hợp lệ.
- Không giữ `learn` ở trạng thái pending của production job.

## 8. Hợp đồng sáng tạo và retention

Các quy tắc dưới đây là production heuristics để tạo đầu ra nhất quán, không được mô tả như bí mật thuật toán.

### 8.1 Hook 0–3 giây

Mỗi ứng viên phải có:

```json
{
  "hook_plan": {
    "first_frame_vi": "",
    "visual_hook_vi": "",
    "spoken_hook_vi": "",
    "on_screen_hook_vi": "",
    "audio_hook_vi": "",
    "single_promise_vi": "",
    "hook_mechanism": "result-first|curiosity|problem-solution|sensory|local-relevance|offer",
    "works_without_sound": true,
    "proof_or_payoff_due_at_second": 0
  }
}
```

Hard rules:

- First frame phải cho thấy sản phẩm, hành động, kết quả, chi tiết cảm giác hoặc vấn đề liên quan.
- Không mở bằng logo-only, lời chào, giới thiệu tên thương hiệu hoặc setup chưa có giá trị.
- Người xem phải hiểu video đem lại điều gì trước hoặc tại giây 3.
- Visual, lời nói và text phải cùng một promise.
- Ít nhất hai trong ba lớp visual, audio và text phải hỗ trợ Hook.
- Video phải hiểu được khi tắt tiếng; audio phải bổ sung giá trị khi bật tiếng.
- Không dùng clickbait mà payoff không đáp ứng.

### 8.2 Retention beats

Không cố định 6–8 cảnh cho mọi độ dài. Số beat phải phát sinh từ nội dung, thời lượng và `pace_profile`.

Mỗi beat có:

```json
{
  "beat_id": "B01",
  "start_s": 0,
  "end_s": 2.4,
  "retention_role": "hook|context|proof|progress|re_hook|payoff|cta",
  "viewer_question_vi": "",
  "new_information_vi": "",
  "visual_action_vi": "",
  "audio_cue_vi": "",
  "retention_device_vi": "",
  "fact_refs": []
}
```

Quy tắc:

- Timestamp phải liên tục, không chồng nhau và phủ đúng toàn video.
- Mỗi beat phải thêm thông tin, bằng chứng, hành động hoặc cảm xúc mới.
- Beat chỉ dùng để “nối cảnh” hoặc lặp lại lời thoại bị loại.
- Video trên 20 giây phải có ít nhất một `re_hook` trong khoảng 35–65% thời lượng.
- Open loop nếu dùng phải có `payoff` trước CTA.
- Pattern interrupt phải hỗ trợ câu chuyện; chuyển cảnh ngẫu nhiên không được tính.
- Payoff phải trả đúng promise của Hook.
- CTA không được biến thành đoạn outro tĩnh kéo dài.
- Natural loop chỉ dùng khi ending nối hợp lý với first frame; không cắt mất payoff.

`pace_profile`:

- `fast`: nhiều thao tác, reveal hoặc cut-on-action.
- `conversational`: ưu tiên người thật và lời nói tự nhiên.
- `sensory`: cho phép shot dài hơn để thấy texture, hơi nóng, rót nước hoặc âm thanh món ăn.
- `auto`: chọn một profile và ghi lý do.

Không hard-code một tốc độ cắt duy nhất như “mỗi 1 giây phải đổi cảnh”.

### 8.3 Engagement plan

```json
{
  "engagement_plan": {
    "primary_action": "keep_watching|share|save|comment|profile_visit|message|order",
    "earned_reason_vi": "",
    "cta_vi": ""
  }
}
```

Chỉ có một primary action:

- `shares_per_view`: tạo tình huống cụ thể khiến người xem muốn gửi cho một người phù hợp.
- `saves_per_view`: cung cấp thông tin có giá trị dùng lại và đã được brief xác nhận.
- `comments`: đặt câu hỏi lựa chọn thật, liên quan trực tiếp nội dung.
- `messages` hoặc `orders`: CTA thương mại ngắn, đúng phương thức đặt hàng.
- `viewed_vs_swiped` hoặc retention: không bắt buộc thêm CTA tương tác.

Cấm CTA stacking như “like, share, comment, follow và đặt hàng ngay”.

## 9. Tạo và chấm ứng viên

Tạo đúng bốn ứng viên:

1. `product-first`
2. `story-first`
3. `process-first`
4. `offer-first` nếu promotion đầy đủ; nếu không dùng `local-life-first`

Các ứng viên phải khác nhau về:

- Hook mechanism.
- First frame.
- Promise.
- Mạch dẫn tới payoff.

Không chỉ thay từ đồng nghĩa.

AI judge:

- Không sửa kịch bản trong lượt chấm.
- Ẩn angle và xáo trộn thứ tự.
- Chỉ nhận JSON hợp lệ.
- Score là `editorial_quality_score`, không phải dự đoán trending.

Thang 100:

- Hook và first-frame clarity: 20.
- Retention architecture và pacing: 20.
- Proof/payoff: 15.
- Rõ ràng: 10.
- Khả năng làm sản phẩm hấp dẫn: 10.
- Chân thật và fact grounding: 10.
- Visual/audio feasibility: 10.
- CTA và platform fit: 5.

Ứng viên đạt khi:

- Tổng điểm từ 78.
- Không tiêu chí nào dưới 6/10.
- Không có hard/safety error.

Dùng tên:

```json
{
  "recommended_candidate_id": "",
  "recommendation_passed": true
}
```

Không dùng `winner_candidate_id`.

Cho tối đa hai vòng sửa. Sau mỗi vòng phải chạy lại hard gate và judge.

## 10. Biến thể thử nghiệm

`variant_count=1` vẫn tạo `experiment.json`.

Với ba biến thể, chọn một trong hai chế độ:

### `hook-package`

Được thay đồng thời:

- First frame.
- Spoken/text/audio Hook.
- Hình và nhịp 0–5 giây.
- Cover text.

Kết luận chỉ được nói biến thể Hook package nào có kết quả quan sát tốt hơn; không quy nguyên nhân cho một thành phần riêng.

### `single-variable`

Chỉ thay đúng một trường đã khai báo, ví dụ:

- Spoken opening line.
- First-frame shot.
- On-screen Hook.
- Cover text.

Mọi thứ khác phải giữ cố định.

Cả hai chế độ phải giữ:

- Facts.
- Offer.
- CTA.
- Promise và payoff cốt lõi.
- Body sau phần thử nghiệm.
- Duration gần tương đương.
- Platform, goal và primary metric.
- Điều kiện đăng gần tương đương nhất có thể.

Không đăng các biến thể gần giống nhau đồng thời.

## 11. Production plan theo biến thể

Mỗi biến thể có file riêng:

```text
variants/<variant-id>/production-plan.json
```

Schema mỗi shot:

```json
{
  "shot_id": "S01",
  "start_s": 0,
  "end_s": 1.2,
  "retention_role": "hook",

  "voiceover_vi": "",
  "on_screen_text_vi": "",

  "visual": {
    "source": "real-video|real-image|ai-image|missing",
    "asset_path": "",
    "subject_vi": "",
    "action_vi": "",
    "framing_vi": "",
    "camera_motion_vi": "",
    "lighting_vi": "",
    "continuity_notes_vi": "",
    "image_prompt_en": "",
    "negative_prompt_en": ""
  },

  "audio": {
    "voice_direction_vi": "",
    "natural_sound_vi": "",
    "sfx_vi": "",
    "music_cue_vi": ""
  },

  "edit": {
    "transition_vi": "hard-cut",
    "change_from_previous_vi": "",
    "subtitle_emphasis_vi": ""
  },

  "fact_refs": []
}
```

Quy tắc Visual Prompt:

- Ưu tiên media sản phẩm thật.
- Không dùng AI để giả sản phẩm, cửa hàng, nhân viên hoặc khách hàng thật.
- AI chỉ dùng cho B-roll, background hoặc minh họa không tạo claim sai.
- Prompt phải mô tả subject, action, composition, lighting, camera, palette và mục đích cảnh.
- Khung hình dọc 9:16.
- Không yêu cầu text, logo hoặc watermark.
- `negative_prompt_en` phải ngăn sản phẩm sai, chữ lỗi, watermark, biến dạng và vật thể không liên quan.
- Giữ continuity về màu, ánh sáng và phong cách giữa các cảnh.

Nếu thiếu media thật và AI image bị tắt, trả `needs_input`; không render placeholder rồi gọi là video hoàn chỉnh.

## 12. Audio, TTS và phụ đề

TTS direction cho từng shot phải mô tả:

- Giọng điệu.
- Cảm xúc.
- Tốc độ.
- Từ cần nhấn.
- Khoảng nghỉ.
- Cách đọc tên món hoặc địa danh.

Cho phép cảnh không có voice-over khi natural sound hoặc ASMR truyền tải tốt hơn.

Không voice cloning và không giả giọng địa phương.

`resume --voiceover-dir` ưu tiên audio thật hợp lệ theo cảnh và bỏ qua TTS tương ứng.

Mix:

- Voice rõ và không clipping.
- BGM chỉ dùng khi có quyền quảng cáo được xác nhận.
- Duck BGM dưới voice; khoảng `-20 dB` chỉ là điểm khởi đầu, không phải hằng số bắt buộc.
- SFX không che lời thoại.
- Không tự lấy nhạc từ reference.

Phụ đề:

- Sinh theo audio thật, không theo thời lượng ước lượng.
- Chia thành cụm lời ngắn.
- Timestamp tăng đơn điệu, không chồng nhau.
- Không đè headline hoặc UI.
- Chữ trắng đậm, viền/bóng tối và nằm trong safe area.

## 13. Render và QA

Render:

- 1080×1920.
- H.264, AAC, `yuv420p`.
- FPS từ `VIDEO_FPS`.
- `faststart`.
- Không kéo méo media.
- Ken Burns chỉ là fallback cho ảnh tĩnh, không phải nhịp dựng mặc định.

QA bằng ffprobe:

- Có video stream.
- Có audio stream.
- Đúng kích thước.
- Duration dương và gần production plan.
- Subtitle timing hợp lệ.
- Không thiếu asset.
- Không có đoạn đen hoặc im lặng ngoài chủ ý đã khai báo.

## 14. Gói SEO và đăng thủ công

Mỗi biến thể có một entry riêng trong `post-package.json`.

Common fields:

```json
{
  "variant_id": "A",
  "platform": "tiktok",
  "video_path": "",
  "cover_text": "",
  "primary_keyword": "",
  "secondary_keywords": [],
  "cta": "",
  "pinned_comment": "",
  "location": "",
  "disclosures": [],
  "posting_checklist": []
}
```

SEO/search rules:

- Chỉ dùng keyword có trong brief hoặc được suy ra trực tiếp từ sản phẩm và địa điểm đã xác nhận.
- Đưa primary keyword tự nhiên vào lời nói, text hoặc metadata; không nhồi lặp.
- Hashtag chỉ 3–5 thẻ liên quan trực tiếp.
- Không gọi hashtag hoặc sound là trending khi không có reference còn thời hạn.
- Không tự đoán giờ vàng.

Platform fields:

### TikTok

- `caption`
- `search_phrase`
- `sound_source`
- `commercial_use_verified`
- commercial-content disclosure
- AI-generated disclosure nếu áp dụng
- safe-area checklist

### Instagram Reels

- `caption`
- `cover_text`
- `share_reason`
- `save_reason`
- `location` khi có dữ liệu
- originality/recommendation eligibility checklist
- AI disclosure nếu áp dụng

### YouTube Shorts

- `title`
- `description`
- `search_phrase`
- `pinned_comment`
- audience setting checklist
- title phải tuân thủ giới hạn hiện hành đã xác minh

## 15. Học từ hiệu suất thật

Metrics input phải có:

```json
{
  "experiment_id": "",
  "platform": "tiktok",
  "distribution_mode": "organic",
  "captured_at": "",
  "observation_window_hours": 72,
  "metric_source": "manual-export",
  "variants": [
    {
      "variant_id": "A",
      "published_at": "",
      "video_duration_seconds": null,

      "views": null,
      "impressions": null,
      "engaged_views": null,
      "stayed_to_watch_rate": null,
      "average_watch_seconds": null,
      "average_percentage_viewed": null,
      "completion_rate": null,
      "rewatches": null,

      "likes": null,
      "comments": null,
      "shares": null,
      "saves": null,
      "profile_visits": null,
      "follows": null,
      "messages": null,
      "orders": null,

      "retention_curve": [
        {"second": 0, "retained_rate": null}
      ],

      "raw_platform_metrics": {},
      "notes": ""
    }
  ]
}
```

Quy tắc:

- Giữ metric thiếu là `null`, không đổi thành 0.
- Giữ cả metric name gốc trong `raw_platform_metrics`.
- Chỉ so cùng experiment, platform, distribution mode và observation window gần tương đương.
- Chọn theo `primary_metric`; metrics khác chỉ là guardrails.
- Không cộng composite score tùy ý.
- Không so số tuyệt đối giữa các nền tảng.
- Không tuyên bố quan hệ nhân quả.
- Khi sample yếu hoặc điều kiện đăng chênh lệch, kết luận `directional`.
- Dùng cụm `best_observed_variant`, không dùng `winner`.
- Nếu có retention curve, ánh xạ điểm rơi vào shot/beat tương ứng.
- Phân tích riêng:
  - Hook: stayed-to-watch hoặc retention đầu video.
  - Body: watch time, APV, completion và dips.
  - Payoff: spike, replay hoặc completion.
  - Action: share, save, profile, message hoặc order.
- `next-brief.json` chỉ chứa một giả thuyết thử nghiệm mới.
- Không thay facts, offer hoặc dữ liệu thương mại gốc.

## 16. Output

```text
outputs/<job-id>/
├── manifest.json
├── normalized-brief.json
├── script-package.json
├── script-report.html
├── experiment.json
├── variants/
│   ├── A/
│   │   ├── production-plan.json
│   │   ├── images/
│   │   ├── audio/
│   │   ├── subtitles.srt
│   │   └── final.mp4
│   ├── B/
│   └── C/
├── post-package.json
└── performance/
    ├── metrics.json
    ├── performance-report.json
    └── next-brief.json
```

`script-package.json` chứa candidates, hard-gate results, judge results, revision history và selection. Không tách nhiều file trung gian nếu chúng chỉ lặp cùng dữ liệu.

Chỉ tạo file thuộc các bước đã chạy.

## 17. Profile rules

### `homemade`

- Ưu tiên cảnh thật: chuẩn bị nhân, đóng khuôn, bánh ra lò, cắt bánh, cận nhân, đóng hộp và chuẩn bị đơn.
- Hướng cảm xúc: ngon, ấm áp, chỉn chu, gia đình hoặc biếu tặng.
- Không suy ra “sạch”, “an toàn”, “ít đường” hoặc “không chất bảo quản”.
- Không dùng AI thay bánh thật.

### `milk-tea`

- Ưu tiên cảnh thật: pha đồ uống, topping, đóng nắp, đồ ăn vặt, xếp đơn, giao hàng và không gian quán.
- Phân biệt giờ nhận đơn, giờ giao và giờ ngồi tại quán.
- Không bịa freeship, combo, menu hoặc món bán chạy.
- Dine-in, delivery và promotion chỉ được dùng khi brief có dữ liệu.

## 18. Kiểm thử bắt buộc

Dùng `unittest`, mock HTTP và không cần API key hay mạng.

Ít nhất kiểm tra:

1. Validate và normalize brief.
2. Media path và advertising rights.
3. Trend thiếu nguồn bị hạ về evergreen.
4. Thiếu dữ liệu bán hàng trả `needs_input`.
5. Phát hiện fact hoặc CTA không có trong brief.
6. Hook hoàn tất trong 3 giây và first frame hợp lệ.
7. Retention beat timestamp liên tục và payoff đúng promise.
8. `--force` không bỏ qua hard/safety error.
9. Hook-package và single-variable experiment giữ đúng biến kiểm soát.
10. Review/gate failure không gọi media hoặc TTS.
11. Không `--allow-paid` thì không gọi API.
12. Dry-run tuyệt đối không request mạng.
13. Resume bỏ qua output hợp lệ và chạy lại output hỏng.
14. Mỗi variant có production plan riêng.
15. Subtitle và ffprobe validation.
16. Platform post-package có đúng trường bắt buộc.
17. `learn` không so chéo platform, giữ `null` và chỉ tạo một giả thuyết mới.

Sau khi viết:

- Chạy syntax check.
- Chạy unit tests.
- Chạy validator chính thức của skill.
- Chạy một dry-run `homemade`.
- Chạy một dry-run `milk-tea`.
- Chạy một fixture `learn`.
- Không gọi API trả phí.

## 19. Tiêu chí hoàn tất và phản hồi cuối

Chỉ coi là hoàn tất khi:

- Skill đã được cài đúng thư mục.
- Validator pass.
- CLI parse được toàn bộ lệnh.
- Unit tests pass.
- Hai dry-run pass hoặc báo dependency thiếu có thể hành động được.
- Fixture `learn` tạo report hợp lệ.
- Không có secret trong file hoặc log.

Câu trả lời cuối phải:

- Báo đường dẫn skill.
- Liệt kê ngắn các file đã tạo.
- Báo syntax check, tests, validator và hai dry-run.
- Đưa đúng hai lệnh dry-run mẫu.
- Liệt kê dữ liệu còn thiếu để chạy thật.
- Nói rõ chưa gọi API trả phí.