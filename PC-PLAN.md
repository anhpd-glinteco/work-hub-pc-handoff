# Kế hoạch chuyển Work Hub sang PC qua Internet, cài trên ổ D

Ngày: 10/11/2026, Asia/Saigon.
Trạng thái: ĐÃ LẬP PHƯƠNG ÁN; CHƯA TẠO BỘ CÀI, CHƯA UPLOAD, CHƯA CÀI TRÊN PC.

## 1. Mục tiêu và cấu hình đích

- Windows 64-bit, RTX 4060, RAM 16 GB, ổ D trống khoảng 70 GB, có Internet.
- Mang Work Hub, giao diện editor, scripts, skills trong workspace và các công cụ đang tích hợp sang PC.
- Không cần USB. Chưa chuyển project đang dựng, footage, thư viện media cá nhân, các bản xuất và lịch sử công việc.
- Model chạy tính năng được tính là thành phần cài đặt, phải tải trên PC; không nhầm với dữ liệu cá nhân đang để bổ sung sau.
- Source, bộ tải xuống, runtime, môi trường Python, model, cache, file tạm và kết quả thuộc bộ công cụ phải đặt trên D.
- Không coi cài xong file EXE hoặc mở được giao diện là đã nghiệm thu đầy đủ.

## 2. Kiến trúc bàn giao được đề xuất

Một GitHub repository private chứa source đã rà soát + tài liệu + bộ cài đặt tự tải phụ thuộc qua Internet. Không đưa model, node_modules, .venv, bộ cài ứng dụng hay file xuất nặng vào Git.

Trên PC, người dùng đăng nhập GitHub bằng tài khoản có quyền, tải source ZIP hoặc clone vào D:/local-video-factory. Cách tải ZIP giúp khởi động cả khi máy chưa cài Git. Lưu ZIP trực tiếp vào D:/Codex/downloads; sau đó dùng Git portable trên D cho cập nhật lâu dài. Không cần dịch vụ lưu trữ trả phí hoặc mở server laptop ra Internet.

Trước upload phải chuẩn bị xong danh sách file sẽ đưa lên và .gitignore. Việc tạo private repo/commit/push cần yêu cầu rõ riêng; lượt này chỉ lập phương án. Nếu chưa dùng GitHub thì có thể phân phối ZIP source đã lọc qua một nơi tải trực tuyến do người dùng chọn, nhưng chưa có URL tải được tạo.

## 3. Bố trí ổ D

Giữ source ở D:/local-video-factory, không đổi vị trí source máy hiện tại.

| Đường dẫn dự kiến trên PC | Nội dung |
|---|---|
| D:/local-video-factory | Source, editor, scripts, skills, hướng dẫn cài |
| D:/Codex/downloads/work-hub-install | Bộ tải chính thức, checksum, manifest tải xuống |
| D:/Codex/work/local-tools | Git portable, Node ZIP, uv, Python gốc, các công cụ và .venv riêng |
| D:/Codex/downloads/work-hub/huggingface | Model VieNeu và các model được chọn cho VoiceStudio |
| D:/Codex/downloads/whisper-models | Model ASR small dùng trong helper hiện có |
| D:/Codex/cache/work-hub | Cache npm, uv, pip, Torch, trình duyệt và profile ứng dụng đã cấu hình |
| D:/Codex/work/work-hub-temp | File tải dở, giải nén và file tạm của tiến trình |
| D:/Codex/outputs/work-hub | Project mới, output, log và báo cáo kiểm tra PC |

Không đổi HOME/USERPROFILE/APPDATA của toàn hệ thống và không dời cả hồ sơ Windows bằng junction. Launcher chỉ truyền cấu hình cần thiết cho tiến trình Work Hub và các tiến trình con.

## 4. Danh mục cần cài đủ

Phiên bản dưới đây là baseline quan sát từ máy nguồn, không phải khẳng định mới nhất hoặc đã chạy trên PC. Khóa URL/revision/hash thực tế trong manifest trước khi đóng bộ cài; nếu artifact upstream không còn thì báo thiếu, không tự thay bằng latest.

| Thành phần | Baseline / cách xử lý |
|---|---|
| Git | Bản Windows x64 portable, giải nén trên D; chỉ cấu hình trong phạm vi workspace khi cần |
| Node + npm | Node ZIP Windows x64; baseline nguồn v24.19.0. Chốt bản còn phù hợp và chạy hồi quy trước khi đổi baseline |
| uv + Python | uv standalone trên D; baseline môi trường Python công cụ là 3.12.14. Python gốc cũng phải nằm trên D |
| FFmpeg + ffprobe | Bản Windows giải nén trên D; kiểm tra codec cần dùng và đường dẫn executable |
| Editor Work Hub | Toàn bộ editor, template và scripts trong source; khởi động bằng launcher của bộ cài |
| HyperFrames | 0.8.223, giữ package-lock và override undici 7.30.1 hiện có; browser render cũng trên D |
| video-use + ASR | Commit nền 43cfc566833548093455c9d4a46bd69913b7e552 + các sửa local cần giữ; faster-whisper 1.2.1, uv.lock; model small tải mới đúng revision |
| VieNeu | 3.8.3; source commit 04044e1b8f822f946bafb2c88b716459f4164152; môi trường riêng và model ONNX fp32 cho đường narration hiện có |
| Whiteboard | Commit 696a7243c0e6ffb6827676e539c2ca5ebae2bf6b; .venv riêng, khóa opencv-python/numpy/PyAV/Pillow sau kiểm tra |
| ConCat | 0.2.8; cài/extract trên D và thay đường dẫn hardcode trong adapter. Cần kiểm chứng cách lưu profile/cache trên D |
| VoiceStudio | 0.5.7; app + runtime + model đã chọn trên D; kiểm chứng profile/cache, không tự tải toàn bộ model catalog |
| Recordly | 1.3.3; app trên D; kiểm tra ghi màn hình và xuất thật, kiểm chứng profile/cache |

Không thêm FLUX/LLM lớn/DaVinci Studio/Remotion/Manim hoặc mọi model được quảng cáo bởi từng ứng dụng: chúng không thuộc bộ đã tích hợp ở đây. Skills gọi dịch vụ ảnh/thiết kế hoặc công cụ Codex vẫn cần app/plugin/tài khoản riêng; sao chép file skill không mang theo quyền truy cập. Codex và driver NVIDIA đang có được coi là phần mềm host, không tự cài lại vào C trong bộ này.

## 5. Các chỗ phải xử lý trước khi phát hành source

- editor/server.mjs: đường dẫn HyperFrames, ConCat, video-use, narration, whiteboard, thư mục thư viện kết quả và công cụ. Giữ biến WORK_HUB_PROJECTS hiện có.
- editor/concat.mjs: executable đang cố định C:/Users/ASUS/...; dùng cùng cấu hình ConCat với server để tránh lệch hai nơi.
- editor/catalog.mjs: thư viện và vùng đường dẫn media cho phép; hỗ trợ ổ D đúng cấu hình, không bỏ kiểm tra phạm vi đường dẫn.
- editor/start.ps1: nạp môi trường cài trên D trước khi chạy; tiến trình phải dùng đúng node/Python/FFmpeg của bộ công cụ.
- scripts/narrate.py, scripts/transcribe_local.py và helper video-use: model/interpreter/cache theo cấu hình, không phụ thuộc tài khoản ASUS.
- Các bài verify/integration: nhiều bài trỏ fixture ở ngày 01/11 hoặc thư mục bằng chứng cũ. Không yêu cầu chép các dữ liệu đó; tạo fixture tổng hợp mới và lưu báo cáo riêng trên D.
- video-use nằm ngoài repo có sửa local chưa commit ở helpers và tài liệu. Clone upstream đơn thuần sẽ mất các sửa này. Đưa bản vá/source cần thiết vào gói bàn giao có ghi commit gốc và giữ license; không sửa hay commit repo upstream trong bước chuẩn bị hub.
- Một số skills dẫn tài liệu lịch sử ở outputs hoặc helper ngoài hub. Liệt kê dependency thiếu; đưa helper thực sự cần vào gói source được kiểm tra quyền/license, hoặc sửa tham chiếu tương ứng. Không chép hồ sơ D:/build-cv hay dữ liệu nghề nghiệp của người dùng.
- Không mang các file PPTX, .env, credential, log cá nhân, output và media không thuộc source. Không đọc .env để làm gói này. Cấu hình đường dẫn dùng file riêng không chứa secret.

## 6. Cài trên D: nguyên tắc thực thi và tiêu chí dừng

- Mọi tải xuống/giải nén chỉ chạy sau khi tạo thư mục temp trên D và gán TEMP/TMP cho phiên cài.
- Đặt UV_PYTHON_INSTALL_DIR, UV_PYTHON_CACHE_DIR, UV_CACHE_DIR, UV_TOOL_DIR và UV_TOOL_BIN_DIR trên D; không dùng Python gốc ở C để tạo .venv.
- Đặt npm cache/prefix/config cục bộ trên D; chạy npm ci bằng lock cho HyperFrames thay vì npx latest hoặc cài global mặc định.
- Đặt HF_HOME/HF_HUB_CACHE/HF_XET_CACHE và các cache Torch/model liên quan trên D trước khi import thư viện/tải model. Không đóng gói token cache.
- Với Chromium/HyperFrames: kiểm tra đúng phiên bản đang dùng hỗ trợ đường dẫn browser, registry preview, font cache và profile nào; đặt trên D và kiểm chứng thực tế. Không giả định một biến PUPPETEER_CACHE_DIR di chuyển được tất cả cache.
- Với ConCat/VoiceStudio/Recordly: kiểm tra tùy chọn portable hoặc đổi nơi cài/profile của đúng release. Electron có cơ chế userData/sessionData nhưng không chứng minh mọi app expose tùy chọn đó. Không tự bịa flag, không tự vá binary hay redirect APPDATA toàn hệ thống.
- Nếu một app bắt buộc cài/runtime/cache riêng trên C mà chưa có phương án được hỗ trợ, đánh dấu BLOCKED cho app đó và cho yêu cầu cài đủ trên D; không âm thầm cài C và không đổi yêu cầu thành cài thiếu.
- Windows, driver và phần mềm host đang cài trên C có thể tự ghi log, registry, shader cache hoặc dữ liệu hệ thống. Bộ cài kiểm soát nơi lưu thành phần của mình, không cam kết không một byte nào được Windows ghi lên C. Nếu phải bổ sung prerequisite hệ thống vào C, dừng và báo trước.
- Cài lặp lại phải bỏ qua artifact đã đúng hash và dependency đã đúng phiên bản; không ghi đè project/dữ liệu sẵn có. Tải lỗi giữ thông tin lỗi và cho phép chạy lại; không tiếp tục bằng file tải thiếu.

## 7. Ngân sách dung lượng và RTX 4060

70 GB là dung lượng đầu vào do người dùng cung cấp, không phải dung lượng đã đo trên PC. Mục tiêu của kế hoạch: giữ đỉnh sử dụng thêm, gồm archive + giải nén + cache + môi trường + model + fixture, trong khoảng tối đa 50 GB và chừa ít nhất 20 GB. Đây là hạn mức thiết kế, chưa phải số đo/bảo đảm cài đủ.

Trước từng phần tải/cài, đọc kích thước release/model và dự trù cả bản nén lẫn giải nén. Tải lần lượt, không tải trùng bộ model và không tải nhiều GPU runtime không cần thiết. Xóa chỉ các file tạm của chính phiên cài sau khi xác minh bản đã cài; không xóa cache/project có trước để lấy chỗ. Nếu dự kiến vượt hạn mức, dừng phần đó và báo dung lượng cần thêm; không chuyển sang C.

Baseline chạy các chức năng đã có bằng CPU/ONNX trước để đối chiếu. RTX 4060 có thể dùng tăng tốc sau khi driver, VRAM thực tế và tổ hợp thư viện được xác minh. Không mặc định dung lượng VRAM từ tên card. Không cài cả CUDA Toolkit chỉ vì có GPU; kiểm tra runtime mà thư viện thật sự cần. Không chạy đồng thời nhiều model với RAM 16 GB. Kiểm tra encoder NVENC nếu dự định dùng; không đổi renderer/codec mặc định chỉ để có nhãn GPU.

## 8. Bộ bàn giao cần tạo ở bước thực hiện

Tên dưới đây là đầu ra dự kiến, CHƯA được tạo bởi lượt lập kế hoạch này.

- SETUP-PC.md: tải source không cần Git ban đầu, cài từ đầu và khởi động, cách cập nhật và xử lý lỗi.
- install-pc.ps1: tải/cài theo manifest, bắt buộc D, có log, kiểm tra chỗ trống, checksum và chạy lại an toàn.
- check-pc.ps1: kiểm tra executable + Python gốc + model + cache/profile + các phép thử chức năng; thiếu là FAIL/BLOCKED rõ ràng.
- start-work-hub.ps1: đặt môi trường D trong phiên và mở editor loopback; các ứng dụng phụ mở qua launcher tương ứng nếu cần.
- Manifest phiên bản/URL/revision/SHA256 và các dependency lock; file cấu hình đường dẫn mẫu; bản vá video-use và thông tin license.
- .gitignore và danh sách source được upload; không tạo installer EXE mới hoặc đóng gói nguyên máy khi các script nhỏ đã đủ.

## 9. Thứ tự triển khai và nghiệm thu

1. Hoàn thiện inventory, hash/lock và kiểm tra phương án D cho ba desktop app; chốt tổng dung lượng tải/cài.
2. Sửa tối thiểu các đường dẫn trong hub; đóng gói bản sửa helper local cần thiết; giữ nguyên dữ liệu và CLI pipeline cũ.
3. Tạo script/tài liệu, kiểm tra trước trong thư mục cài thử sạch trên D của máy nguồn; không dùng dependency đã có ở C để lấp chỗ thiếu.
4. Chuẩn bị source private đã lọc; chỉ tạo repo/commit/push khi được yêu cầu rõ. Ghi revision phát hành để PC tải đúng bản.
5. PC tải qua Internet, cài lần lượt và mở launcher. Người dùng tự đăng nhập tài khoản khi cần; không chuyển phiên đăng nhập/secret từ laptop.
6. Nghiệm thu trên PC bằng fixture nhỏ, tự tạo hoặc được phép: tạo/save/reopen project; import ảnh/video/audio; phụ đề; render MP4 HyperFrames; ASR tiếng Việt có timestamp; narration WAV; whiteboard MP4; ConCat native save/reopen/export; VoiceStudio tạo WAV; Recordly quay/xuất ngắn. Các app cần nghe/xem hoặc chọn cửa sổ ghi hình phải có thao tác của người dùng nếu automation không thực hiện được.
7. Báo cáo executable/interpreter/model/cache/profile thực tế và thay đổi quan sát được trên C liên quan bộ cài. Kiểm tra vị trí thực bằng process config và probe ghi file có mục tiêu; chỉ chênh lệch dung lượng ổ C không đủ xác định nguyên nhân.
8. Đạt khi tất cả thành phần trong phạm vi chạy được, được kiểm tra trên PC, dữ liệu do bộ công cụ quản lý nằm trên D, và các mục chưa thử được báo đúng trạng thái. Sau đó người dùng bổ sung dữ liệu dựng riêng.

## 10. Bằng chứng đã có và phần chưa làm

PASS khảo sát: source editor có sẵn; hub chưa có .git; nhận diện đường dẫn hardcode; đọc baseline HyperFrames/lock; xác minh các .venv công cụ hiện trỏ Python gốc ở C; phát hiện bản sửa local video-use.

NOT_RUN: bộ cài/script mới, thử cài sạch, đo dung lượng đầy đủ, hỗ trợ D của desktop app theo đúng release, kiểm tra trên PC, tải model mới, GPU và kiểm tra chức năng trên PC.

Không có sự kiện nào trong tài liệu này là bằng chứng đã upload GitHub hoặc đã cài xong trên PC. Trạng thái tổng thể: kế hoạch sẵn sàng cho bước chuẩn bị bộ cài; yêu cầu cài đủ trên D chưa được nghiệm thu.

## 11. Nguồn đã dùng, đọc 10/11/2026

Nguồn local: D:/local-video-factory/{AGENTS.md,TOOLS.md,README.md,editor/README.md,editor/server.mjs,editor/catalog.mjs,editor/concat.mjs,editor/start.ps1,scripts/narrate.py,scripts/transcribe_local.py}; manifests, pyvenv.cfg và git status/revision của các công cụ trong D:/Codex/work/local-tools. Không đọc secret .env.

- Git portable Windows: https://git-scm.com/install/windows
- Node downloads/standalone: https://nodejs.org/en/download
- uv nơi lưu Python/cache: https://docs.astral.sh/uv/reference/environment/ và https://docs.astral.sh/uv/reference/storage/
- uv installer không mặc định đặt mọi dữ liệu theo nơi đặt executable: https://docs.astral.sh/uv/reference/installer/
- npm config: https://docs.npmjs.com/cli/v11/using-npm/config/
- Model cache Hugging Face: https://huggingface.co/docs/huggingface_hub/package_reference/environment_variables
- Electron userData/sessionData: https://www.electronjs.org/docs/latest/api/app
- HyperFrames: https://github.com/heygen-com/hyperframes
- VieNeu: https://github.com/pnnbao97/VieNeu-TTS
- video-use: https://github.com/browser-use/video-use
- Whiteboard: https://github.com/geeklee/srt-whiteboard-animation
- ConCat: https://github.com/jub0t/Concat
- VoiceStudio: https://github.com/debpalash/VoiceStudio
- Recordly: https://github.com/webadderallorg/Recordly

Nguồn ứng dụng chỉ xác nhận project phát hành; chưa xác nhận release nào cho phép toàn bộ profile/cache trên D. FFmpeg download page bị timeout ở lần tra cứu này; phải kiểm tra lại nguồn binary và checksum khi khóa manifest.
