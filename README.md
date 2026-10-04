# QBA Auto Parts - Hệ Thống Quản Lý & Tra Cứu Phụ Tùng Ô Tô (Odoo 18)

[![Odoo Version](https://img.shields.io/badge/Odoo-18.0-875A7B.svg?logo=odoo&logoColor=white)](https://www.odoo.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB.svg?logo=python&logoColor=white)](https://www.python.org)

Hệ thống ERP chuyên sâu ngành phụ tùng ô tô phát triển trên nền tảng **Odoo 18 Community**, giải quyết bài toán phức tạp về quản lý đa mã OE, tra cứu thông số kỹ thuật xe cơ giới và hỗ trợ bán hàng tốc độ cao.

---

## Mục Lục
- [Tổng Quan Ứng Dụng](#tổng-quan-ứng-dụng)
- [Tính Năng Cốt Lõi](#tính-năng-cốt-lõi)
- [Kiến Trúc Giao Diện (Responsive UI)](#kiến-trúc-giao-diện-responsive-ui)
- [Cấu Trúc Thư Mục](#cấu-trúc-thư-mục)
- [Hướng Dẫn Triển Khai & Khởi Chạy](#hướng-dẫn-triển-khai--khởi-chạy)

---

## Tổng Quan Ứng Dụng

Đặc thù ngành phụ tùng xe tải và ô tô là một chi tiết linh kiện có thể dùng chung cho nhiều dòng xe, nhiều đời động cơ và có nhiều mã phụ tùng thay thế (Mã OE chính hãng). Phân hệ **qba** được tùy biến nhằm:
1. **Rút ngắn thời gian tra cứu:** Nhân viên bán hàng chỉ mất 1–2 giây để tra mã phụ tùng, kiểm tra tồn kho, giá bán và các mã OE thay thế.
2. **Nâng cao độ chính xác:** Công cụ đối chiếu song song 2–4 sản phẩm giúp tư vấn đúng loại phụ tùng, giảm thiểu tối đa tỷ lệ trả hàng do sai quy cách.
3. **Quản lý dữ liệu tập trung:** Đầy đủ lịch sử nhập kho, báo giá gần nhất, thương hiệu, động cơ, hộp số và thư viện ảnh phụ đa góc chụp.

---

## Tính Năng Cốt Lõi

### 1. Quản Lý Đa Mã Phụ Tùng Chính Hãng (Multi-OE Codes)
- Một sản phẩm phụ tùng liên kết không giới hạn với nhiều mã OE (qba.oe.code).
- Phân loại rõ ràng mã OE theo từng hãng sản xuất (Hyundai, Kia, Ford, Isuzu, Toyota, Antek,...).
- Bộ tìm kiếm thông minh: Tìm kiếm tức thì theo bất kỳ mã OE nào ngay trên thanh tìm kiếm chung của Odoo.
- Bộ lọc nhanh: *Có mã OE*, *Hàng sẵn trong kho*.

### 2. Thư Viện Ảnh Phụ Đa Góc Chụp (Extra Images Gallery)
- Lưu trữ album ảnh phụ độ phân giải cao cho từng phụ tùng (qba.product.image).
- Đánh số thứ tự và hiển thị số lượng ảnh phụ dạng badge (+X ảnh).
- **Click-to-Zoom (Lightbox):** Bấm trực tiếp vào ảnh để phóng to toàn màn hình xem chi tiết răng bánh răng, bước ren, kích thước khắc trên thân phụ tùng.

### 3. Công Cụ So Sánh Chi Tiết Song Song (Product Compare Wizard)
- Cho phép chọn đối chiếu nhanh từ **2 đến 4 sản phẩm** cùng lúc.
- Bảng ma trận so sánh đầy đủ 11 thông số kỹ thuật:
  - Slide Album ảnh: Tích hợp carousel lướt ảnh phụ, nút Next/Prev, thumbnail chọn nhanh và khung ảnh 200px chống tràn.
  - Mã SKU & Tên sản phẩm.
  - Giá bán niêm yết (VNĐ).
  - Tồn kho thực tế (màu sắc trực quan).
  - Danh sách mã OE tương đương.
  - Thương hiệu nhà sản xuất.
  - Lịch sử ngày nhập kho gần nhất.
  - Lịch sử ngày nhận báo giá gần nhất.
  - Động cơ & Hộp số áp dụng.
  - Danh sách dòng xe tương thích.
  - Ghi chú bán hàng chuyên biệt.
- Giao diện thanh tìm kiếm ghim trên đỉnh (**Sticky Header**) và thanh cuộn mượt mà duy nhất.

### 4. Quản Lý Lịch Sử Giá & Nhập Hàng Tự Động
- Tự động quét và cập nhật ngày nhập hàng gần nhất từ các Đơn mua hàng đã xác nhận (purchase.order.line).
- Tự động lưu vết ngày nhận báo giá gần nhất từ các yêu cầu báo giá (RFQ).

### 5. In Tem & Mã Vạch Phụ Tùng (Label Printing Wizard)
- Hỗ trợ tạo và in nhãn dán barcode trực tiếp từ thẻ sản phẩm phục vụ quản lý dán tem kho bãi.

---

## Kiến Trúc Giao Diện (Responsive UI)

Giao diện được thiết kế chuẩn Responsive ngay từ đầu theo đề xuất BA:

`	ext
                 PRODUCT UI
                     │
             ┌───────┴───────┐
             │               │
          DESKTOP           MOBILE
             │               │
      Wide Product Row   Product Card
             │               │
             └───────┬───────┘
                     │
                Same Odoo Data
`

- **Desktop (>= 992px) - Wide Product Row:**
  Thẻ sản phẩm trải rộng theo chiều ngang (tối thiểu 480px, chia cột thông tin mạch lạc), giúp hiển thị trọn vẹn 10 thông số kỹ thuật mà không bị co cụm dòng chữ.
- **Mobile (< 992px) - Product Card:**
  Thẻ tự động xếp tầng gọn gàng thành thẻ dọc chuẩn di động, tối ưu diện tích và thao tác chạm cảm ứng.
- **Same Odoo Data:** Cả hai chế độ hiển thị đồng bộ từ cùng một nguồn dữ liệu Odoo product.template.

---

## Cấu Trúc Thư Mục

`	ext
odoo-qba/
├── .gitignore                         # Bộ lọc Git chuẩn (chặn dữ liệu tạm, db runtime)
├── README.md                          # Tài liệu dự án
├── environment/
│   ├── docker-compose.yaml            # Cấu hình Docker Compose khởi chạy hệ thống
│   ├── restore.sh                     # Script Bash khôi phục Database từ dump.sql
│   └── restore.ps1                    # Script PowerShell khôi phục Database (Windows)
└── odoo/
    ├── custom_addons/
    │   └── qba/                       # Module tính năng chính QBA Auto Parts
    │       ├── models/                # Models Odoo (product_template, oe_code, wizard,...)
    │       ├── views/                 # Giao diện XML (Kanban, List, Form, Wizard)
    │       ├── static/                # CSS Responsive & JS Lightbox/Slider
    │       └── security/              # Phân quyền truy cập ir.model.access.csv
    ├── debian/
    │   └── odoo.conf                  # File cấu hình Odoo Server (addons-path, dev_mode, db)
    ├── Dockerfile                     # Dockerfile tối ưu đa tầng (Multi-stage build)
    └── requirements.txt               # Thư viện Python phụ thuộc
`

---

## Hướng Dẫn Triển Khai & Khởi Chạy

### Yêu cầu hệ thống:
- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/)
- Docker Image Odoo: staging-qba-odoo-18:latest

### Các bước khởi chạy:

1. **Clone repository:**
   `ash
   git clone https://github.com/bh10-d/odoo-qba.git
   cd odoo-qba
   `

2. **Khởi chạy container:**
   `ash
   cd environment
   docker compose up -d
   `

3. **Khôi phục dữ liệu mẫu (Tùy chọn - nếu có file dump.sql):**
   - Đặt file dump.sql vào thư mục environment/.
   - Chạy script restore tự động:
     - **Trên Linux / macOS / Git Bash:**
       `ash
       chmod +x restore.sh
       ./restore.sh qba dump.sql
       `
     - **Trên Windows PowerShell:**
       `powershell
       .\restore.ps1 -DbName qba -DumpFile dump.sql
       `

4. **Truy cập ứng dụng:**
   - Mở trình duyệt tại: http://localhost:8089 (hoặc cổng cấu hình trong docker-compose.yaml).
   - Vào menu **Ứng dụng (Apps)** -> Cập nhật danh sách ứng dụng -> Nâng cấp/Cài đặt module **Phụ tùng ô tô QBA** (qba).
