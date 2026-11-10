---
name: work-media
description: "Produce local narration, captions, screen demos, whiteboard and motion videos from permitted sources, then verify the actual export."
---
# work-media

Chuẩn chung: đọc .agents/workflow.md mục 3 và 5 cho kiểm tra bản sản xuất, hook/giữ chân khi phù hợp và bảo toàn artifact. Đường dẫn tính từ gốc hub; ví dụ cũ không giới hạn chủ đề mới.

Các đường dẫn tài liệu tương đối bên dưới tính từ D:/local-video-factory. Đọc AGENTS.md trước; tuân thủ chế độ host và phạm vi yêu cầu.

Đọc TOOLS.md ở gốc hub trước khi chọn công cụ; phân biệt installed với tested. Chỉ dùng nhánh và reference của công cụ đang cần. Mặc định tận dụng Codex hiện tại cho lời thoại/kịch bản, không gọi text API khác. Dùng VieNeu CPU preset cho tiếng Việt, VoiceStudio cho audio theo khả năng đã kiểm chứng, Recordly cho quay demo, HyperFrames cho motion, whiteboard scripts cho vẽ bảng, FFmpeg để ghép/subtitle/kiểm tra. Không giả video bằng placeholder.
Phân tích đầu vào bằng helper inspect_video.py của build-cv nếu phù hợp. Thiếu footage/quyền sử dụng thì hoàn thành kịch bản/storyboard và hỏi phần chặn render, ghi needs_input. Video tham khảo không tự thành asset được phép tái đăng. Không clone giọng khi chưa được chủ giọng cho phép.
Lập edit plan ngắn với asset, thời gian và audio; giữ nguyên nguồn. Phụ đề theo audio thật, sửa lỗi nhận dạng trong đoạn dùng. Mặc định không nhạc khi chưa yêu cầu. Chạy tác vụ model/render lần lượt trên máy RAM 16GB; không tự tải model lớn hoặc chuyển sang API trả phí.
Xem file xuất cuối, ffprobe streams/duration/resolution; kiểm tra hình đầu/giữa/cuối, phụ đề/dấu tiếng Việt và sync. Nghe khi công cụ hỗ trợ, nếu chưa nghe ghi NOT_RUN. Ghi lệnh tái tạo, phiên bản, thời gian chạy và giới hạn. Đăng tải là việc riêng, không tự làm.
Pipeline local-video-factory cũ chỉ dùng cho homemade/milk-tea đúng brief; giữ nguyên CLI và --allow-paid. Quy trình đa nội dung dùng các công cụ local trực tiếp, không ép vào schema thương mại cũ.

Với tác vụ chuyên biệt, dùng skill tương ứng trong AGENTS.md; editor/README.md mô tả project schema và bàn giao giữa editor. Không ép tác vụ content thành render; giữ nguyên project native đã sửa tay.
