# SARWatch AI

**NISAR giúp ưu tiên kiểm chứng ngập tại Huế.** NASA Space Apps 2026 · Dancing with the SARs.

## Chạy ứng dụng

```bash
python run.py --open
```

Bấm đúp **start.bat** trên Windows để mở bản HTML trực tiếp, không cần server hay Python. Muốn dùng API server, chạy start.bat --server hoặc lệnh Python ở trên; chế độ server cần Python 3.11+. 

| Thư mục | Bao gồm |
|---|---|
| **app/** | `web/`: giao diện và font; `server/`: API và dự báo mưa |
| **data/** | `inputs/`: toàn bộ dữ liệu gốc; `products/`: mô hình và kết quả; `manifest.json`: checksum |
| **pipeline/** | Các bước xử lý khoa học; `core/`: thuật toán dùng chung; `notebooks/`: notebook 15 bước |
| **dev/** | `build/`: công cụ build/kiểm tra; `tests/`: test; `tools/`: lấy dữ liệu mới; cấu hình Node |
| **docs/** | Nguồn dữ liệu, phương pháp, khai báo AI và nội dung nộp bài |

## Các lệnh cần dùng

| Lệnh | Công việc |
|---|---|
| `python run.py --open` | Mở web |
| `python run.py check` | Kiểm tra dữ liệu, checksum và tính đầy đủ của repo |
| `python run.py build` | Tạo bản một file tại `app/standalone/index.html` |
| `python run.py reproduce` | Tái chạy toàn bộ xử lý khoa học |
| `python run.py test` | Kiểm tra Python và các dữ liệu đã đóng gói |
| `python run.py package` | Xuất ZIP đầy đủ để mang sang máy khác |

## Cài môi trường

Để tái chạy pipeline, dùng Python 3.11:

```bash
python -m venv dev/.venv
# Windows
dev/.venv/Scripts/python -m pip install -r requirements.txt
dev/.venv/Scripts/python run.py reproduce
# macOS/Linux: thay dev/.venv/Scripts/python bằng dev/.venv/bin/python
```

Để kiểm tra giao diện, cài Node 24 và chạy:

```bash
npm --prefix dev ci
npm --prefix dev run test:ui
```

## Dữ liệu và kết quả

Case NISAR 15/27-10-2026 có 1.646 vùng ứng viên sau sàng lọc, tổng 9,3045 km². Phơi nhiễm dân số mô hình một phần khoảng 1.681 người, với dữ liệu dân số hợp lệ trên 60,5% diện tích ứng viên; đường giao cắt khoảng 18,689 km. Đây chưa phải tác động ngập đã được xác nhận.

Random Forest đạt F1 0,8825 so với baseline Otsu 0,8560 trên tập giữ riêng theo không gian. Các chỉ số đo khớp nhãn nước tự động Sentinel-2, không phải độ chính xác cảnh báo lũ. Bản tái chạy 9,3809 km² được lưu riêng với sản phẩm Colab gốc.

## Tài liệu

- [Phương pháp, nguồn dữ liệu, khai báo AI và hồ sơ nộp](docs/METHODOLOGY.md)

Mã nguồn: Apache 2.0, xem LICENSE. Dữ liệu và font giữ giấy phép riêng trong NOTICE và tài liệu nguồn. Đây là nguyên mẫu phân tích phục vụ kiểm chứng, chưa phải hệ thống cảnh báo khẩn cấp được kiểm định.
