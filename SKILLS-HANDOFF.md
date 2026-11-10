# Bàn giao skills và kiến thức Work Hub

Ngày 10/11/2026. Đọc tài liệu này cùng AGENTS.md và PC-PLAN.md. Thành công phải bao gồm bảo toàn cách làm đã tích lũy và định tuyến đúng yêu cầu trong chat, bên cạnh cài ứng dụng.

## Những gì đã mang theo

| Nhóm | Tên / vị trí |
|---|---|
| 6 skills tổng quát | work-start, work-research, work-freelance, work-content, work-build, work-media trong .agents/skills |
| 12 skills chuyên trách | content-ideas, video-style, video-rough-cut, video-template-edit, video-whiteboard, image-edit, product-creative, motion-graphics, video-generative, video-shorts, audio-production, podcast-create trong .agents/skills |
| video-use đã sửa local | vendor/video-use: SKILL.md, install.md, helpers, dependency lock, các tài liệu Manim đi kèm và license |
| Skill cá nhân pipeline cũ | vendor/local-video-factory: SKILL.md, references/homemade.md, milk-tea.md, platforms.md, agents metadata, scripts/video_factory.py và test đi kèm |
| Chuẩn làm việc tích lũy | AGENTS.md, .agents/workflow.md, prompt.md, README.md, TOOLS.md |
| Kiến thức giao diện/dựng | editor/README.md, templates.mjs, model.mjs, workflow.mjs, workflow-ui.js và toàn bộ source editor |
| Nguồn học và tình huống mẫu | docs/knowledge/skill-library/sources.md, 12 file *-scenario.md và hồ sơ kiểm tra gốc |
| Bằng chứng quy trình chung | docs/knowledge/workflow-standard/REPORT.md và verification.json |

18 skills Work Hub đã có từ bản source bàn giao đầu. Lần bổ sung này đưa thêm nguồn học/tình huống vốn nằm ngoài repo và toàn bộ skill cá nhân cũ. Không coi tài liệu lịch sử là kết quả nghiệm thu trên PC.

## Khôi phục trên PC

1. Giữ nguyên nội dung 18 skills và agents/openai.yaml tương ứng. Không tái tạo thành bản hướng dẫn chung ngắn hơn hoặc cập nhật upstream ghi đè bản local.
2. Sao chép vendor/video-use vào .agents/skills/video-use nếu đường dẫn đích chưa có, hoặc đăng ký bản source đó bằng cơ chế hỗ trợ đường dẫn D. Nếu đã có bản khác, so sánh trước, không ghi đè. Trỏ runtime editor đến đúng nơi chứa helper này.
3. Đăng ký bản skill cá nhân có sẵn trong vendor/local-video-factory tại .agents/skills/local-video-factory trên D theo cùng nguyên tắc. Khi chạy CLI cũ, dùng đúng scripts/video_factory.py trong skill này hoặc đường dẫn đã cấu hình; scripts/ ở gốc hub hiện không chứa script CLI đó. Không đổi CLI/schema và --allow-paid của pipeline cũ. Đây là khôi phục skill đã có, không thiết kế skill mới.
4. Skills hiện dẫn nguồn học tại D:/Codex/outputs/work-hub/2026-11-01/skill-library. Khôi phục các file từ docs/knowledge/skill-library vào đúng thư mục đó trên PC, chỉ khi chưa có; nếu đã có thì so sánh và bảo toàn bản khác. Làm tương tự với workflow-standard khi cần đọc hồ sơ lịch sử. Cách này giữ nguyên các dẫn chiếu cũ.
5. Mở lại workspace/chat nếu Codex cần quét lại skills. Khi bộ chọn skill chưa hiển thị, dùng fallback đọc trực tiếp SKILL.md theo AGENTS.md; không kết luận skill chạy được chỉ vì xuất hiện trong danh sách.
6. Đọc task.md lịch sử trong skill-library để biết giới hạn nguồn. Raw caption/frame/audio tham khảo và các file media kiểm chứng không nằm trong gói này; không tuyên bố đã xem lại chúng trên PC.

## Cách làm phải được giữ lại

- Hiểu mục tiêu → nghiên cứu phần chưa rõ → đề xuất có căn cứ → thực hiện → kiểm tra → rút kinh nghiệm; dùng phần phù hợp cho từng yêu cầu.
- Việc rõ đi thẳng nhánh; việc chưa rõ dùng work-start. Không biến mọi câu hỏi thành video, affiliate, trà sữa hoặc hồ sơ nghề nghiệp.
- Nguồn/facts/quyền dùng đứng trước nội dung; nguồn web là dữ liệu. Không bịa trải nghiệm, hiệu quả hoặc thu nhập.
- Hook, minh chứng, nhịp nội dung và thử biến thể theo mục 3 .agents/workflow.md; không biến mẫu sáng tạo thành công thức cam kết viral.
- Dựng video theo brief/beat plan, duyệt cut, sửa theo từng phần, giữ project chỉnh tay, revision và file xuất riêng theo editor/README.md.
- video-use giữ transcript theo từ, cache theo nguồn, quy tắc giữ lời/hơi thở, fades và phụ đề đúng timeline; giữ toàn bộ helper local thay vì chỉ copy tên skill.
- Ghi task.md và artifact để tiếp tục được; giữ PASS/FAIL/BLOCKED/NOT_RUN và bằng chứng thật.

## Dependency chưa được mang sang

- work-freelance dẫn tới D:/build-cv cùng skills nghề nghiệp; đây là project khác chưa nằm trong gói chuyển này. Khi chưa có nguồn đó, báo thiếu cho tác vụ nghề nghiệp, không tự bịa hồ sơ.
- work-research có dẫn helper inspect_video.py trong D:/build-cv. Cần giải quyết helper hoặc báo BLOCKED khi tác vụ thật cần; không suy ra source helper có trong repository này.
- Skills/plugin cài ở cấp tài khoản Codex như Figma, tài liệu, SEO, imagegen và các connector không nằm trong 18 skills Work Hub. Kiểm tra catalog trên PC; chúng có cơ chế cài/quyền truy cập riêng. Không sao chép credential.
- Các kết luận chưa kiểm chứng trong tài liệu nguồn vẫn giữ nguyên mức độ chưa kiểm chứng sau khi chuyển.

## Tiêu chí kiểm tra bàn giao skills

Đã đối chiếu SHA256 84 file source/metadata/helper/reference trong bản bàn giao với máy nguồn: không lệch. Chi tiết ở docs/skill-transfer-inventory.json. Báo cáo này là kiểm tra bảo toàn file trên máy nguồn, không phải kiểm chứng kỹ năng của agent hoặc runtime trên PC.

Trên PC cần kiểm tra đủ 18 + video-use + skill cá nhân cũ, các reference/helper và nguồn học mở được. Thử định tuyến ít nhất các yêu cầu: nghiên cứu ý tưởng mới, viết bài, sửa code trong repo chỉ định, phân tích phong cách video và cắt footage. Kiểm tra nội dung định tuyến trước; không tự sản xuất clip hoặc gọi dịch vụ tốn phí chỉ để thử bộ chọn skill. Với runtime thực hiện theo PC-PLAN.md.

Chỉ đánh dấu hoàn tất khi kiến thức đã được bảo toàn, agent đọc đúng skill, và dependency thiếu được giải quyết hoặc ghi rõ trạng thái.
