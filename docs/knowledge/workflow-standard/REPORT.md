# Kiểm chứng chuẩn Work Hub — 01/11/2026

## Kết quả

PASS kiểm tra tĩnh tài liệu: 53 kiểm tra, 0 lỗi (verification.json). Cả 18 skill, AGENTS.md và README dẫn tới chuẩn chung. Nội dung cũ của 20 tài liệu được bảo toàn theo thứ tự; metadata skill hợp lệ. 16 file được chụp hash trong prompt.md, TOOLS.md, scripts/ và editor/ không đổi. Không có .codegraph; thư mục hiện không có Git nên không có git diff/status để xác minh dirty work. Bản trước sửa của các tài liệu được lưu ở before/; không đọc .env.

Thay đổi gồm .agents/workflow.md mới, các dẫn chiếu theo vai trò trong 18 skill và hướng dẫn vào việc trong AGENTS.md/README. Không thêm skill, dependency hoặc thay CLI/schema; không sửa source project khác.

## Thử tình huống trên giấy

Đây là review thủ công luồng chỉ dẫn, không phải chạy agent độc lập hay nghiên cứu thị trường thực tế.

| Đầu vào thử | Đối chiếu chuẩn | Kết quả review |
|---|---|---|
| Có máy hút bụi mini, muốn làm TikTok affiliate | Mục 1–4: work-start/work-research tìm hiểu đối tượng, vấn đề, phương án và bằng chứng; hỏi link/thông tin sản phẩm, tài nguyên và mục tiêu còn thiếu. content-ideas → work-content/product-creative → work-media khi được giao sản xuất; thiếu footage không giả kết quả. Chưa có bằng chứng bán chạy thì giữ là ứng viên. | PASS: không ép profile trà sữa/homemade, có hook/minh chứng/thử nghiệm và bàn giao chat. |
| Muốn viết bài giải thích học ngoại ngữ cho người mới | Mục 1–3: nghiên cứu kỹ ý tưởng mới, hỏi bối cảnh người học ảnh hưởng lựa chọn; content-ideas → work-content. Bài viết có cách mở phù hợp, không ép mốc ba giây, CTA mua hàng hoặc render. | PASS: dùng chuẩn theo định dạng, không bắt làm video. |
| Ý tưởng dịch vụ sửa xe lưu động, chưa rõ nhu cầu | Mục 1–2: work-start/work-research khảo sát vấn đề, nhóm khách hàng, giải pháp hiện có và hạn chế; hỏi địa bàn/phạm vi phục vụ, tiếp tục phần độc lập. Chưa cần hồ sơ cá nhân. Chỉ chuyển work-freelance khi yêu cầu gói dịch vụ/proposal gắn nghề nghiệp. | PASS: không tự tải build-cv cho nghiên cứu nhu cầu chung, kết thúc bằng hướng và bước thử. |
| Sửa lỗi lưu dữ liệu trong một repo được chỉ định | Mục 1, 2, 5 và work-build: đọc hướng dẫn repo, xác định lỗi/tiêu chí đạt và dirty work, CodeGraph nếu có, kiểm tra callers/tests, sửa và kiểm tra phù hợp. Chỉ nghiên cứu phần kỹ thuật chưa rõ; hỏi cách tái hiện khi cần. | PASS: đi thẳng code/QA, không ép nghiên cứu thị trường hoặc nội dung. |

## Giới hạn

NOT_RUN: agent smoke trong chat mới, nghiên cứu thị trường thực tế, render, đăng bán và đo chuyển đổi/viral. Không thay đổi runtime nên không chạy lại bộ render/editor. Chuẩn là chỉ dẫn cho agent, không phải cơ chế cưỡng chế bằng code. Kiến thức chuyên sâu tìm sản phẩm thắng chờ yêu cầu cập nhật sau.
