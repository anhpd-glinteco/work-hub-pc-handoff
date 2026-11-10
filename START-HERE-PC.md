# Bàn giao cho Codex trên PC

Hãy thực hiện PC-PLAN.md đến khi cài và kiểm tra xong; đây là source bàn giao, chưa phải bộ cài hoàn thiện. Windows x64, RTX 4060, RAM 16 GB, D trống khoảng 70 GB. Người dùng đã yêu cầu cài đủ công cụ trên D, tải qua Internet, chưa chuyển dữ liệu dựng.

## Bắt đầu

Clone repository này vào D:/local-video-factory. Nếu chưa có Git, tải ZIP bằng trình duyệt, chọn lưu vào D:/Codex/downloads rồi giải nén source vào D:/local-video-factory. Mở folder đó bằng Codex, đọc AGENTS.md và PC-PLAN.md.

Prompt cho Codex:

> Thực hiện PC-PLAN.md trong workspace này. Tạo và chạy bộ cài trên PC, chuẩn hóa đường dẫn, tải đúng phiên bản, đặt Python gốc/runtime/model/cache/temp/output trên D. Kiểm tra dung lượng trước mỗi bước; giữ tối thiểu 20 GB trống. Hoàn thiện install-pc.ps1, check-pc.ps1 và launcher. Cài đủ các thành phần trong kế hoạch, chạy kiểm tra chức năng bằng dữ liệu mẫu tự tạo, ghi PASS/FAIL/BLOCKED/NOT_RUN thật. Không chuyển project/footage của máy cũ. Không tự cài phần nào sang C. Nếu ứng dụng không hỗ trợ cấu hình D, báo chặn rõ ràng. Tiếp tục tự xử lý các việc độc lập. Không commit/push nếu chưa được yêu cầu.

## Source bổ sung

- vendor/video-use là bản source chứa sửa local của máy nguồn, không thay bằng clone upstream thuần. Commit nền: 43cfc566833548093455c9d4a46bd69913b7e552. Giữ LICENSE của upstream.
- vendor/hyperframes-package.json và hyperframes-package-lock.json: sao chép vào thư mục cài HyperFrames trên D dưới tên package.json/package-lock.json trước npm ci.
- vendor/vieneu-lock.txt: baseline môi trường nguồn, cần kiểm tra khả năng cài trên Python đích, không coi là bằng chứng cài thành công.
- Whiteboard upstream commit 696a7243c0e6ffb6827676e539c2ca5ebae2bf6b; VieNeu upstream commit 04044e1b8f822f946bafb2c88b716459f4164152. URL trong PC-PLAN.md.

Tài liệu cũ có link tới outputs máy nguồn; chúng là lịch sử, không phải file đã chuyển. Không cần khôi phục bộ dữ liệu cũ để chạy fixture mới. App/plugin Codex và quyền truy cập tài khoản cần thiết lập riêng trên PC. Bộ source này không mang theo đăng nhập.

## Trạng thái bàn giao

Source được mang theo cả giao diện và các script hiện có. Bộ cài tự động và hỗ trợ D hoàn toàn của các desktop app vẫn cần được Codex trên PC triển khai và kiểm chứng theo kế hoạch. Không suy ra cài đủ chỉ từ clone thành công.
`nKhi cài, đăng ký vendor/video-use thành skill .agents/skills/video-use bằng bản sao hoặc cơ chế liên kết local phù hợp; đường dẫn skill của máy nguồn không được đưa vào Git.
