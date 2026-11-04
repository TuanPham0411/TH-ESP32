# TH-ESP32 — XiaoZhi độc lập

Hostname triển khai: **https://esp.th.io.vn**. Đặt `PUBLIC_URL=https://esp.th.io.vn` và đăng ký Google callback `https://esp.th.io.vn/auth/callback`.

Website và API tự chứa cho XiaoZhi Copper Robot ESP32-S3: hướng dẫn phần cứng, Web Serial installer, firmware/gói offline, tài khoản Google, quản lý thiết bị và tám công cụ Internet. Không dùng backend, database, Google callback hoặc hostname của portal cũ.

**Mọi tính năng công khai đều miễn phí.** Tải xuống, cài firmware và gọi API công cụ không cần đăng nhập, bearer key, gói dịch vụ hoặc mở khóa. Đăng nhập Google chỉ phục vụ hồ sơ và danh sách thiết bị riêng của bạn.

## Chạy trên Docker hoặc Raspberry Pi mới

Hỗ trợ Linux AMD64 và ARM64, Raspberry Pi OS/Debian **64 bit**, Docker Engine và Compose v2.

```sh
git clone https://github.com/TuanPham0411/TH-ESP32.git
cd TH-ESP32
cp .env.example .env
# Chỉnh PUBLIC_URL và Google OAuth cho hostname của bạn nếu dùng tài khoản.
docker compose up -d --build --wait --wait-timeout 180
python3 tools/smoke.py
```

Cổng mặc định: 5081, bind localhost. Dùng `BIND_ADDRESS=0.0.0.0` nếu cần truy cập LAN. Web Serial cần Chrome/Edge desktop và **HTTPS**, ngoại trừ localhost. Không phải trình duyệt nào trên điện thoại cũng hỗ trợ cài qua USB.

Installer JavaScript và firmware được phục vụ từ chính container; không tải thư viện installer từ CDN lúc người dùng mở trang. Source frontend và lockfile nằm trong `frontend/`, bundle đã build nằm trong `app/static/vendor/`.

## Google/Gmail cho địa chỉ mới

1. Tạo OAuth Client loại Web application trong Google Cloud Console.
2. Đặt `PUBLIC_URL=https://esp32.ten-mien-cua-ban.example` trong `.env`.
3. Thêm đúng `https://esp32.ten-mien-cua-ban.example/auth/callback` vào **Authorized redirect URIs**, rồi điền `GOOGLE_CLIENT_ID` và `GOOGLE_CLIENT_SECRET`.
4. Khi phát triển, có thể đăng ký `http://localhost:5081/auth/callback`. Với LAN/Internet, dùng hostname HTTPS.
5. Google consent screen ở Testing chỉ nhận tài khoản thử đã thêm; chuyển sang Production theo yêu cầu Google để cho phép đăng nhập công khai.
6. Nếu dùng một reverse proxy tin cậy phía trước cổng 5081, bật `TRUST_PROXY=1`; không bật khi nhận trực tiếp traffic không tin cậy.

Không có credential Google nào được đóng gói trong source/image. Khi chưa cấu hình, `/login` báo chưa sẵn sàng; các trang, download, installer và công cụ công khai vẫn dùng được. Khóa cookie tự sinh trong volume `/data`; giữ volume khi nâng cấp.

## Biên tập nội dung riêng

Đặt `ADMIN_EMAILS` thành danh sách email Google đã xác thực của người được phép sửa hướng dẫn. Đăng nhập rồi mở `/?edit=1`; bản chỉnh sửa và lịch sử được lưu trong SQLite riêng. Nếu để trống, không ai có quyền biên tập. Đây là quyền quản trị nội dung, không phải quyền mở tính năng hoặc thuê bao. HTML được lọc bỏ script và event handler.

## Công cụ robot

`GET /api/xiaozhi/tools/list` liệt kê tám công cụ. `POST /api/xiaozhi/tools/call` nhận JSON `name` và `arguments`, không kiểm tra giấy phép hay thuê bao. `X-Xiaozhi-Session` tùy chọn để tách phiên nhạc; không phải khóa trả phí. URL audio được tạo theo `PUBLIC_URL` hiện tại, không trỏ về website cũ.

Ví dụ:

```json
{"name":"search_web","arguments":{"query":"ESP32-S3","limit":3}}
```

Google News, DuckDuckGo, iTunes, YouTube và OpenAI vẫn là các dịch vụ ngoài. `OPENAI_API_KEY` và `YOUTUBE_API_KEY` là tùy chọn của chủ triển khai; tính năng tương ứng báo 503 nếu chưa cấu hình. Đơn vị cung cấp API có thể áp dụng hạn mức/chi phí cho chủ khóa; ứng dụng này không có chức năng thu tiền của người dùng.

## Firmware, phần mềm và driver

Binary gốc đã được đối chiếu với Git LFS; SHA-256 firmware hợp nhất là `c8e77c6e00c9e38dcd8c0b48ee637a8c37d8aa376dbcfa7ac51cd2bad25bba5a`. Gói ZIP được đóng lại chỉ để cập nhật hướng dẫn cho website độc lập; mọi binary bên trong giữ nguyên. Catalog ghi checksum của từng bản phát hành và ứng dụng kiểm tra khi khởi động.

Trang `/downloads` chứa BIN, gói offline và liên kết công cụ/driver chính thức. Gói cũ chỉ có firmware và hướng dẫn; không giả định có một bộ driver Windows riêng bên trong. Không cần website cũ để tải các tệp được đóng gói.

**Chưa có source ESP-IDF của firmware.** Website build lại được, firmware hiện tại được phân phối nguyên bản. Firmware vẫn sử dụng dịch vụ XiaoZhi/OTA bên thứ ba theo cấu hình gốc; việc tách website không biến firmware thành một firmware offline. Cần bổ sung source firmware nếu muốn thay nhà cung cấp hoặc build lại chương trình ESP32.

## Kiểm thử và phát triển

```sh
python3 -m venv .venv
.venv/bin/pip install -r app/requirements.txt
.venv/bin/python -m unittest discover -s tests -v
cd frontend
npm ci
npm run build
```

Các test Google dùng provider giả lập, kiểm tra state/nonce/PKCE, issuer, audience, expiry và email_verified; không chứa tài khoản mẫu hoặc đường đăng nhập bỏ qua xác thực. Web Serial trên robot thật và Google login thật cần kiểm thử ở địa chỉ HTTPS/callback đã cấu hình.

CI kiểm thử rồi publish image AMD64/ARM64 tại `ghcr.io/tuanpham0411/th-esp32:COMMIT_SHA`. Dùng SHA cố định và kiểm tra quyền truy cập package. Đọc [triển khai/sao lưu](docs/DEPLOY.md) và [nguồn gốc](docs/PROVENANCE.md).
