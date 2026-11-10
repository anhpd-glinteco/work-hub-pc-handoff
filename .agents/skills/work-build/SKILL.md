---
name: work-build
description: "Implement or verify scoped code, QA and automation tasks in an explicitly identified target project; not writing-only or video-only work."
---
# work-build

Chuẩn chung: đọc .agents/workflow.md mục 1, 2 và 5; nghiên cứu phần kỹ thuật chưa rõ, giữ routing code/QA và phạm vi repo. Đường dẫn tính từ gốc hub; ví dụ cũ không giới hạn chủ đề mới.

Các đường dẫn tài liệu tương đối bên dưới tính từ D:/local-video-factory. Đọc AGENTS.md trước; tuân thủ chế độ host và phạm vi yêu cầu.

Xác định repo đích và phạm vi được yêu cầu trước khi sửa. Đọc AGENTS.md của repo, kiểm tra dirty work và ownership. Có .codegraph/ thì dùng CodeGraph trước khi tìm/đọc để hiểu code; không tự index. Tìm callers/tests/config/export liên quan và sửa đầy đủ với diff nhỏ.
Dùng skill kỹ thuật hiện có theo tác vụ: frontend, backend, Android, QA hoặc automation; không giới hạn mọi việc thành frontend. Skill là hướng dẫn cho agent hiện tại, không đồng nghĩa phân việc cho subagent. Tái sử dụng pattern/dependency hiện có. Giữ source ở repo gốc và bảo toàn sửa đổi khác.
Chạy kiểm tra phù hợp thay đổi; với logic không tầm thường có test/self-check nhỏ kiểm tra hành vi thật. Không tự nhận đã test UI/live khi chỉ build. Không tự commit/push/deploy. Bàn giao diff/artifact, cách chạy, PASS/FAIL/BLOCKED/NOT_RUN và hạn chế.
