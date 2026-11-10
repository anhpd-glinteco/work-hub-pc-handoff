# Work Hub

Mở folder này trong Codex và nói yêu cầu. Ví dụ:
- “Đọc các link này và chọn ý có thể thử trên máy mình.”
- “Đọc JD này, đối chiếu hồ sơ và soạn proposal để mình gửi.”
- “Sửa responsive trong repo [đường dẫn], kiểm tra mobile.”
- “Từ dữ liệu này tạo báo cáo/slide/bảng tính.”
- “Dựng demo từ footage [đường dẫn], có phụ đề tiếng Việt.”
- “Làm demo, rồi viết case và bài giới thiệu từ kết quả đã kiểm tra.”

Sáu skill tổng quát và 12 skill chuyên trách nằm trong .agents/skills. Chat mới sẽ có cơ hội nhận diện; AGENTS.md vẫn hướng dẫn đọc trực tiếp nếu bộ chọn chưa cập nhật. Không cần gõ tên skill. Đầu ra ở D:/Codex/outputs/work-hub. Đọc TOOLS.md để biết trạng thái công cụ thực tế.

Bối cảnh nghề nghiệp đọc từ D:/build-cv, không sao chép. Kế hoạch 30 ngày và nguồn tổng hợp nằm trong thư mục setup đầu ra. Nội dung/video chỉ được đăng/gửi khi có yêu cầu riêng. Template video cũ được giữ nguyên.

## Cách làm việc chung

Bạn đưa ý tưởng/yêu cầu và nguồn đang có; không cần gọi tên skill. Với ý tưởng mới, mặc định nghiên cứu kỹ: vấn đề, đối tượng, giải pháp hiện có, bằng chứng và hướng khả thi. Thiếu bối cảnh ảnh hưởng quyết định thì hỏi bạn, đồng thời tiếp tục phần độc lập. Yêu cầu rõ dùng lại nghiên cứu còn hợp lệ và đi thẳng phần cần làm.

Chu trình: hiểu mục tiêu → nghiên cứu → đề xuất có căn cứ → thực hiện → kiểm tra → rút kinh nghiệm. Áp dụng cho nhiều chủ đề và loại đầu ra; ví dụ đồ ăn/trà sữa là trường hợp riêng. Chuẩn chi tiết: [.agents/workflow.md](.agents/workflow.md).

Ví dụ: “Mình có ý tưởng [mô tả]. Hãy nghiên cứu kỹ đối tượng, vấn đề và hướng làm; cần thêm bối cảnh thì hỏi mình. Đầu ra mình muốn là [bài/video/ảnh/code/báo cáo], ràng buộc [nếu có].” Nếu yêu cầu gồm thực hiện thì tiếp tục phần đã được giao, không bắt duyệt lại từng bước.

Nội dung đi từ ý tưởng sang kịch bản rồi sản xuất khi cần. Video ngắn có kiểm tra hook ba giây đầu, minh chứng, giữ chân, CTA và biến thể theo mục tiêu; hiệu quả cần số liệu thật. Nghiên cứu sản phẩm có thể ở chat riêng: chuyển bản tổng hợp đối tượng, vấn đề, hướng chọn, nguồn, giả thuyết và câu hỏi mở sang chat làm nội dung. Chưa có bộ tự tìm sản phẩm thắng; kiến thức chuyên sâu sẽ bổ sung theo yêu cầu sau.

Việc nhiều bước có task.md và artifact trong thư mục đầu ra theo ngày/tên việc; khi tiếp tục sẽ đọc hồ sơ và xác minh bản hiện có. Pipeline video cũ giữ nguyên CLI/schema và phạm vi riêng.

## Editor local

Chạy editor/start.ps1, mở http://127.0.0.1:4317. Hướng dẫn, schema và giới hạn ở editor/README.md. Bộ nguồn và kết quả kiểm chứng: D:/Codex/outputs/work-hub/2026-11-01/skill-library.
