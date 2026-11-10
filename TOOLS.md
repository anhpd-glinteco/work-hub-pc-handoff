# Công cụ đã kiểm tra — 01/11/2026

Chỉ báo trạng thái dưới đây theo bằng chứng local, không suy ra nghiệm thu khách. CPU Intel Iris Xe / RAM khoảng 16GB. Không dùng API trả phí.

| Công cụ | Trạng thái | Vị trí / giới hạn |
|---|---|---|
| VieNeu 3.8.3 CPU ONNX fp32 | PASS tạo WAV | D:/Codex/work/local-tools/vieneu-env; mẫu 7.28s tạo trong 14.62s gồm load; chưa nghe nghiệm thu |
| SRT Whiteboard | PASS render | D:/Codex/work/local-tools/srt-whiteboard-animation; mẫu 6s H264 640x360; chưa là phim minh họa hoàn chỉnh |
| HyperFrames 0.8.223 | PASS render | D:/Codex/work/local-tools/hyperframes; mẫu 20s H264 640x360/15fps; renderer lần đầu khoảng 12.4s không tính tải Chrome |
| VoiceStudio 0.5.7 | PASS nạp model và tạo WAV | CPU /health OK; OmniVoice ready; /generate trả WAV 4.383917s, PCM 24kHz mono, mean -19.1dB/max -2dB. Điều khoản đã accept theo yêu cầu rõ của người dùng. OmniVoice phi thương mại; tokenizer chưa rõ license. Chưa nghe nghiệm thu. |
| Recordly 1.3.3 | Cài PASS, quay/xuất NOT_RUN | Bản ổn định chính thức checksum PASS; installer exit 0; exe trên D:/Codex/work/local-tools/Recordly. Có HUD/controls nhưng input đang không chạm đúng cửa sổ; chưa có demo. Bản 1.4.0 cũ lỗi System.dll. |
| FFmpeg/ffprobe | PASS dùng thực tế | Đã dùng render/QC/extract frames; binary hiện có nằm trên C |
| Whisper/helper inspect | PASS lấy phụ đề + frames | D:/build-cv/scripts/inspect_video.py, interpreter D:/Codex/work/video-tools/.venv/Scripts/python.exe; ba video có captions nên không chạy ASR |
| FLUX 4B / LLM 35B / DaVinci MCP | Hoãn | Không tải model nặng hoặc mua Studio |

## Chạy narration
```powershell
& 'D:/Codex/work/local-tools/vieneu-env/Scripts/python.exe' 'D:/local-video-factory/scripts/narrate.py' --text 'Nội dung tiếng Việt.' --output 'D:/Codex/outputs/work-hub/voice-moi.wav'
```
Chỉ nhận preset có sẵn, không ghi đè output. Model cache: D:/Codex/downloads/work-hub/huggingface. Script tự đặt HF_HOME khi chưa có biến; nếu môi trường đặt đường dẫn khác phải công bố.

## Render motion
```powershell
& 'D:/Codex/work/local-tools/hyperframes/node_modules/.bin/hyperframes.cmd' render 'D:/Codex/outputs/work-hub/2026-11-01/setup/samples/motion' --fps 15 --quality draft -o 'D:/Codex/outputs/work-hub/motion-moi.mp4'
```
Chạy tại thư mục công cụ/job để không nạp .env cũ của hub. CLI upstream vẫn có telemetry mặc định; không đăng nhập hoặc publish. Phụ thuộc undici override ^7.30.1; npm audit sau sửa báo 0. package-lock ở thư mục cài. Có hai lint warning với mẫu seek timeline tự viết; không có lint error và đã render thật.

## Whiteboard
Python: D:/Codex/work/local-tools/srt-whiteboard-animation/.venv/Scripts/python.exe. Script scripts/render_stream_whiteboard.py nhận image, annotation JSON và output; dùng --bare-tip cho mẫu không cần tài sản bàn tay. Đọc README và --help của đúng commit trước việc mới; không tự kích hoạt skill upstream với các quy tắc ngôn ngữ/confirmation khác workflow hub.
Commit: 696a7243c0e6ffb6827676e539c2ca5ebae2bf6b. VieNeu source: 04044e1b8f822f946bafb2c88b716459f4164152. Lock Python trong setup/vieneu-lock.txt.

## Lưu trữ và quyền sử dụng
Bộ cài và SHA256 upstream ở D:/Codex/downloads/work-hub. VoiceStudio/Chromium có cache trên C:/Users/ASUS/AppData/Roaming/VoiceStudio và C:/Users/ASUS/.cache/hyperframes; Chrome/fonts/pip cache có thể trên C dù môi trường chính trên D. Không đổi setting hệ thống để ép dời cache.
App license không thay license model/voice/ảnh. VoiceStudio/Recordly AGPL; VieNeu Apache 2.0 và model có điều kiện riêng; HyperFrames Apache 2.0. Xác minh đúng model/voice trước làm asset thương mại. Mẫu geometric tự vẽ dùng cho kiểm tra; không tái sử dụng video tham khảo làm sản phẩm khách.

## Editor và skill library bổ sung
- Work Hub Editor: Node built-in, local 127.0.0.1:4317; save/reopen/conflict/path/origin/error handling và FFmpeg render PASS qua editor/test.mjs; UI save/export đã thao tác.
- HyperFrames Studio: mở composition có timeline PASS; render mẫu 4s PASS, một lint warning về cấu trúc nested scene. Chưa nghiệm thu chỉnh từng thuộc tính qua Studio. Preview registry/log trên C:/Users/ASUS/AppData/Local/hyperframes; font cache trên C:/Users/ASUS/.cache/hyperframes.
- VieNeu job từ editor: WAV tạo PASS; nghe/sync NOT_RUN.
- ConCat 0.2.8: cài per-user PASS và khởi chạy PASS; `C:/Users/ASUS/AppData/Local/Programs/Concat/Concat.exe`. Release chính thức Windows x64 SHA256 xác minh PASS (`6ded705620e6c18adbc2ece28a2876db326e4f6361c8e41151dab516419c8776`); upstream ghi build chưa ký số. Native project, MCP, model AI và export thực tế: NOT_RUN.
- 18 skill metadata validation PASS; 12 scenario chuyên trách được lưu, nghiệm thu từng workflow NOT_RUN.

## Studio v2 — 01/11/2026
Nguồn trạng thái mới: D:/Codex/outputs/work-hub/2026-11-01/editor-v2/REPORT.md. Có layer/timeline, compiler preview/render chung, v1 migration, thư viện và job persistence. ConCat MCP create/save/reopen/export ảnh/title/audio PASS kỹ thuật. Whiteboard render PASS. Benchmark 12 lượt text/shape 1080p30 đã chạy; không đại diện video người nói. VoiceStudio/Recordly adapter UI và 12 workflow editorial chưa nghiệm thu. Ghi chú v1 phía trên là lịch sử, không dùng làm trạng thái hiện hành.
