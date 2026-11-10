---
name: audio-production
description: "Tạo narration, làm sạch và phối audio local."
---
# audio-production

Chuẩn chung: đọc .agents/workflow.md mục 1, 3 và 5; áp dụng phần phù hợp với định dạng và đầu ra được yêu cầu. Đường dẫn tính từ gốc hub; ví dụ cũ không giới hạn chủ đề mới.

Đọc AGENTS.md; với tác vụ media đọc TOOLS.md và .agents/skills/work-media/SKILL.md.

Đọc TOOLS.md. Dùng scripts/narrate.py với VieNeu preset cho tiếng Việt. Đo duration/peak, nghe phát âm và sync. Nhạc/SFX cần quyền dùng; tạo nhạc mới chỉ khi có công cụ phù hợp, không tự tải model nặng. VoiceStudio OmniVoice có giới hạn phi thương mại.

Đầu ra: WAV, transcript, phép đo và bản phối khi có yêu cầu.

Nguồn học: https://www.tiktok.com/@qimedia5.2/photo/7700213216495848724. Chi tiết và mức đọc: D:/Codex/outputs/work-hub/2026-11-01/skill-library/sources.md.

Kiểm chứng: Lời thoại tiếng Việt có tên riêng và chữ viết tắt. Kiểm tra artifact thực tế, ghi PASS/FAIL/BLOCKED/NOT_RUN; không coi file skill là kết quả nghiệm thu.

Bàn giao qua editor theo editor/README.md; giữ project native và revision, không ghi đè sửa tay. Đầu ra theo thư mục task trên ổ D.
