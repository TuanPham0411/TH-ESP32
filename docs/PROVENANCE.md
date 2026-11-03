# Nguồn gốc và tài nguyên

Website được tách từ `TuanPham0411/GOT`, commit `4a7de663b0bf16427b7c51e88ea3d8c1426cda73`, theo yêu cầu chủ repository. Giữ hướng dẫn XiaoZhi và các hàm công cụ, viết lại lớp tài khoản và lưu thiết bị độc lập. Không nhập database người dùng, giao dịch, giấy phép, khóa API, Cloudflare hoặc cấu hình SIKA.

Firmware hợp nhất có Git LFS OID `c8e77c6e00c9e38dcd8c0b48ee637a8c37d8aa376dbcfa7ac51cd2bad25bba5a`. Gói ZIP nguồn có SHA-256 `7cc50bff2a44dd474843081bc5ef804c7eef947391b66b9515786977cfe00d0d`; được kiểm tra trước khi đóng gói lại hướng dẫn. Binary không thay đổi. Checksum trong `app/releases/catalog.json` áp dụng cho các tệp phân phối mới.

ESP Web Tools và các thành phần JavaScript được khóa dependency trong `frontend/package-lock.json`, giữ legal notices của bundle trong `app/static/vendor/`. Điều kiện cấp phép riêng của các thành phần/binary vẫn có hiệu lực; việc công khai và miễn phí website không tự cấp thêm quyền tái cấp phép thành phần bên thứ ba.
