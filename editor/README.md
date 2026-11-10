# Work Hub Studio v2

Chạy `powershell -NoProfile -File D:/local-video-factory/editor/start.ps1`, mở http://127.0.0.1:4317. Không npm install, không đọc .env. Source/CLI video thương mại cũ được giữ nguyên.

## Làm việc
- Trái: chọn layer, thêm text/caption/shape/image/video/audio, thêm bố cục mẫu. Giữa: preview theo composition HTML. Phải: sửa nội dung, transform, màu, font, căn lề, thời gian và volume; khóa/ẩn layer. Kéo layer để di chuyển, kéo góc dưới phải để resize. Xoay bằng inspector.
- Dưới: play/scrub, kéo clip theo frame, giữ Shift khi kéo để trim đuôi, chọn clip rồi Tách clip. Đổi thứ tự bằng Lên/Xuống lớp trong inspector.
- Ctrl+Z / Ctrl+Shift+Z; Space phát/dừng; Delete xóa layer khi không gõ trong ô nhập. Autosave 750ms và revision conflict; undo/redo trong phiên, lịch sử file trong history/.
- 1080p/30fps ngang hoặc dọc; asset gốc giữ nguyên. Preview hiện scale canvas, chưa có transcoding proxy tự động. Asset H264/PNG/WAV dễ preview nhất.
- Import ảnh/video/audio theo đường dẫn D trong vùng đã cho phép. SourceIn và duration tính bằng giây. Không có keyframe editor nâng cao; dùng HyperFrames native cho phần đó.
- Nhập SRT/VTT dạng hh:mm:ss,mmm, sửa từng caption layer và xuất SRT. Chưa có tự nhận dạng lời nói ngay trong UI.
- Thư viện tìm skills, dữ liệu nguồn, mẫu/kết quả cũ, báo cáo và công cụ; Xem tài nguyên mở file được đăng ký, không di chuyển môi trường/model. Bố cục mẫu là khung để điền nội dung, chưa phải video thành phẩm.

## Công cụ
- Xuất video và HyperFrames dùng cùng compiler model.mjs. Mỗi job có snapshot và project native riêng, không ghi đè bản chỉnh tay. Chỉ render bản gốc có asset local.
- ConCat tạo, save/reopen và export native qua MCP 0.2.8. Project riêng nằm trong exports/<job>/native-project. SourceIn khác 0 hiện từ chối rõ ràng thay vì bỏ qua. Native ConCat có thể khác typography/transform của HTML: chưa được nghiệm thu pixel parity giữa hai engine.
- Storyboard/whiteboard sửa JSON gồm scenes và whiteboard {image: assets/…, annotation: {canvas,sceneDurationMs,elements}}. Tạo WAV giữ narration từng scene; WAV mới không tự thay audio đang dùng, import WAV vào audio layer. Render whiteboard dùng renderer local; không chạy lại cả phim khi sửa một annotation.
- VoiceStudio/Recordly được liệt kê ở thư viện và TOOLS.md; chưa có adapter thao tác đầy đủ trong UI. OmniVoice phi thương mại.

## Model/API
Schema v1 được migrate trong bộ nhớ, bản gốc nằm ở history khi lưu v2. V2 thêm output {width,height,fps}, layers [{id,type,name,start,duration,sourceIn,x,y,width,height,rotation,opacity,volume,fontSize,font,color,align,text,asset,hidden,locked}], giữ scenes cho narration/whiteboard. Layer cuối ở phía trước; compiler đảo track index HyperFrames để giữ thứ tự giống preview.
GET/POST /api/projects; GET/PUT /api/projects/:id (409 khi revision cũ); POST .../import {path}; POST .../jobs {action,revision}; GET /api/jobs/:id; GET .../files/* có Range/HEAD. Action render/hyperframes/concat/narrate/whiteboard. GET /api/library; GET /api/library/file?id=<registered-id>; POST /api/preview. Không nhận lệnh shell từ client. Chỉ loopback/cùng origin. Job lưu dưới editor-projects/jobs; restart đánh dấu interrupted.

## Kiểm tra
`node editor/verify-v2.mjs`: migration, save, conflict, validation, library/origin. `node editor/integration-v2.mjs`: copy asset tự tạo, HTTP Range, render có ảnh/audio, whiteboard, native ConCat. `node editor/benchmark.mjs`: 10/30/60s, mỗi fixture 4 lượt, 1080p30, một worker. Benchmark tổng hợp không đại diện talking-head/B-roll hoặc audio-sync. Báo cáo, ảnh UI và các phần NOT_RUN: D:/Codex/outputs/work-hub/2026-11-01/editor-v2.

## Dựng theo quy trình

1. Mở **Quy trình dựng**, chọn khung hình trong Project rồi ghi brief, mẫu và beat plan. Thẻ **Video mẫu** trong **Thư viện** có nút đưa link và ghi chú vào brief. Duyệt beat plan trước khi xuất bản cắt thô.
2. Trong **Thư viện**, chọn Footage, Video mẫu hoặc SFX. Đăng ký file ở vị trí đang có và chọn điểm vào/ra nguồn bằng giây. Chọn **Được dùng** kèm căn cứ quyền dùng để mở nút **Chèn tại playhead**. Clip chèn là bản sao trong assets của project. Thư viện nằm ở D:/Codex/outputs/work-hub/media-library; có thể đặt WORK_HUB_LIBRARY khi chạy trong môi trường thử.
3. Đánh dấu các layer thoại, hình hoặc nhạc chủ đạo bằng **Clip chính của bản cắt** trong Thuộc tính. Đặt playhead để Trim đầu, Trim đuôi hoặc Tách clip theo frame. Với clip thoại đã chọn, có thể tạo và mở transcript tiếng Việt theo từ trong Quy trình dựng. Cache nằm trong analysis của project, tách theo file nguồn, kích thước và thời điểm sửa.
4. Xuất **Bản cắt thô** và chọn đúng bản ở hộp Quy trình dựng để xem, ghi góp ý theo playhead và duyệt. Sửa phụ đề, B-roll hoặc SFX phụ giữ duyệt bản cắt nếu beat plan và clip chính vẫn khớp. Thay đổi take, thứ tự, điểm cắt chính hoặc beat plan yêu cầu xem lại bản cắt phù hợp.
5. Xuất **Bản ứng viên** rồi mở file từ lịch sử. Ghi QA sau khi xem trọn file trên thiết bị đích. QA gắn với job cụ thể; khi timeline đổi, UI phân biệt QA của bản trước. Các lượt xuất giữ snapshot và MP4 riêng.
6. **Gói bàn giao** ở thanh trái lấy cả timeline. Trong Quy trình dựng, nhập khoảng giây để lấy riêng một đoạn. Gói gồm media, cuts.json (timecode tương đối của đoạn và beat plan), captions.srt và hướng dẫn lớp. Nhập bản nâng cao đã dựng trở lại timeline. Với file tự nhập theo đường dẫn, người dựng xác nhận quyền dùng trước khi bàn giao.

Quy trình là trường tùy chọn của Studio v2. Project cũ có thể tiếp tục xuất bằng nút cũ hoặc bật quy trình khi cần. Catalog giữ link của video mẫu để học kỹ thuật. SFX CC0 trong kho gồm các bản MP3 công khai đã kiểm tra giải mã.

## Kiểm tra nâng cấp

- node editor/verify-v2.mjs kiểm tra hồi quy schema, revision và API cũ.
- node editor/verify-workflow.mjs <thư-mục-fixture> [thư-mục-editor-baseline] chạy API, render 2 bản, kiểm tra ASR và gói bàn giao. Fixture gồm take.mp4 có thoại tiếng Việt và broll.mp4. Chạy trên thư mục bằng chứng mới vì script giữ nguyên các bản đã xuất.

## Khớp khung, phụ đề và bố cục mẫu

- Layer video mới lấy kích thước canvas. Vừa khung giữ đủ hình; Phủ khung cắt giữa theo tỷ lệ khung của layer. Thay nguồn giữ vị trí và kích thước đã chỉnh. Dùng Đặt về khung canvas để đưa layer cũ về kích thước project. Dùng Xuất video hoặc HyperFrames cho clip Phủ khung.
- Nhập SRT/VTT kiểm tra toàn file trước khi thêm layer. Trạng thái báo số cue hoặc vị trí lỗi. Một lần Hoàn tác bỏ cả lượt nhập.
- Xem bố cục mẫu mở bản xem riêng. Chèn tại playhead thêm các layer vào project hiện tại. Tạo project từ mẫu dùng khung hình hiện tại, với layer của mẫu bắt đầu tại giây 0.
- POST /api/projects có thể nhận template và output {width,height,fps} để tạo từ mẫu. Project v2 lưu tùy chọn fit của video là contain hoặc cover; mặc định contain. Kiểm tra tập trung bằng node editor/verify-editor-fixes.mjs.
