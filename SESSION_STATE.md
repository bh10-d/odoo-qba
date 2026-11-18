# Project Session State & Handover

Tài liệu này lưu trữ trạng thái làm việc và nhật ký bàn giao giữa các phiên làm việc (chat sessions).
**Mỗi phiên làm việc mới BẮT ĐẦU bằng việc đọc file này và KẾT THÚC bằng việc cập nhật file này.**

---

## 1. Thông Tin Môi Trường & Kiến Trúc Hiện Tại (Baseline)

- **Dự án:** QBA Odoo 18 Community (Phụ tùng ô tô xe tải nặng Q.BA)
- **Nhánh Git hiện tại:** `perf-optimize-qba-pos`
- **Môi trường Docker:**
  - `staging-qba-postgres-1`: PostgreSQL 15, Database chính: `qba`
  - `staging-qba-odoo-1`: Odoo 18.0 Community, Cổng Web: `http://localhost:8089` (Longpolling: `8092`)
- **Các Custom Addons đang cài đặt (`odoo/custom_addons/`):**
  - `qba`: Phụ tùng, đồng bộ Website SEO, in tem nhãn trực tiếp.
  - `qba_pos`: Điểm bán lẻ POS, bán hàng nhập tay `SP_CHUA_CO_MA`, bảo hành Zalo. Máy POS hiện tại: `POS Ban Le Q.BA` (3.106 sản phẩm đã kích hoạt).
  - `qba_ai`: Trợ lý AI tra cứu phụ tùng, kiểm tra tồn kho & báo giá thời gian thực.
- **Tích hợp Backend Ngoài (Express.js):**
  - Endpoint: `http://host.docker.internal:5000/api/v1`
  - Xác thực bảo mật: HMAC SHA-256 (`x-odoo-signature`, `x-odoo-timestamp`, `x-odoo-api-key`)
  - Trạng thái hiển thị giá: Chuẩn hóa nhãn `"Liên hệ Báo giá"` khi ẩn giá (`showPrice: false`).

---

## 2. Nhật Ký Phiên Gần Nhất (Last Session Log)

- **Thời gian:** 2026-11-06 11:25 (GMT+7)
- **Công việc đã hoàn thành:**
  1. Tích hợp bộ quy tắc **Ponytail** (`.agents/skills/ponytail*`, `.agents/rules/ponytail.md`) vào dự án.
  2. Tích hợp toàn diện **`odoo-senior-developer-skill-pack`** vào [.agents/](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/.agents) (10 Odoo skills, templates, workflows, `.agents/rules/odoo-senior.md`).
  3. Thiết lập **Mandatory Session Handover & Skill Activation Workflow**:
     - Tạo [SESSION_STATE.md](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/SESSION_STATE.md) làm file sổ tay ghi nhận trạng thái liên tục giữa các phiên.
     - Cập nhật quy tắc bắt đầu/kết thúc phiên vào [AGENTS.md](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/AGENTS.md) và [.agents/rules/session-handover.md](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/.agents/rules/session-handover.md).
  4. Cập nhật `.gitignore` cho phép theo dõi `AGENTS.md`, `SESSION_STATE.md`, `.agents/`.
  5. Đã commit (`0e9ef45`) và push toàn bộ cấu hình `.agents/`, `AGENTS.md`, `SESSION_STATE.md` lên Git remote (`origin feature/product-web-seo-sync`).
- **Các file chính đã thay đổi:**
  - `AGENTS.md` (Updated)
  - `SESSION_STATE.md` (Created & Initialized)
  - `.gitignore` (Updated)
  - `.agents/rules/session-handover.md` (Created)
  - `.agents/rules/odoo-senior.md` (Created)
  - `.agents/rules/ponytail.md` (Created)
  - `.agents/skills/*` (16 skills installed)

---

## 3. Bản Đồ Kích Hoạt Skills (Skill Activation Map)

Khi bắt đầu một tác vụ mới, AI bắt buộc phải đối chiếu và kích hoạt đúng skill tương ứng trước khi viết code:

| Tác vụ / Vấn đề cần xử lý | Skill áp dụng |
|---|---|
| Phân tích bài toán mới, xác định ranh giới module, lập kế hoạch | `.agents/skills/odoo-architect` |
| Viết model ORM, fields, compute, constraints, business logic, cron | `.agents/skills/odoo-backend` |
| Giao diện người dùng, OWL components, JS assets, QWeb templates, XML views | `.agents/skills/odoo-frontend` |
| Phân quyền, ACL (`ir.model.access.csv`), Record Rules, kiểm soát `sudo()` | `.agents/skills/odoo-security` |
| Tối ưu câu lệnh ORM, N+1 query, Index PostgreSQL, migration an toàn | `.agents/skills/odoo-database` |
| Viết Controller, Webhook, API client kết nối bên thứ 3 (Express, Zalo,...) | `.agents/skills/odoo-integration` |
| Phát triển hoặc debug AI Assistant, tìm kiếm ngữ nghĩa, RAG, prompt injection | `.agents/skills/odoo-ai-rag` |
| Viết unit test Odoo, kiểm thử bảo mật, kiểm chứng kết quả chạy test | `.agents/skills/odoo-testing` |
| Review code, đánh giá rủi ro trước khi commit hoặc merge | `.agents/skills/odoo-code-review` |
| Cấu hình Docker, kiểm tra log container, restart service, backup dữ liệu | `.agents/skills/odoo-devops` |
| Viết code tối giản, loại bỏ bloat, YAGNI, review diff tinh gọn | `.agents/skills/ponytail*` |
| Chống code rác, chống UI cliché, template sáo rỗng, comment máy móc | `.agents/skills/antislop*` |

---

## 4. Nhật Ký Phiên Vừa Thực Hiện

- **Thời gian:** 2026-11-18 17:26 (GMT+7)
- **Nhánh Git:** `feature/stock-accounting-opening-balance` (tạo từ `main`)
- **Công việc đã hoàn thành:**
  1. **Xóa hoàn toàn nút `Cập nhật số lượng` trên header form Sản phẩm & khóa chỉ đọc trên smart button `Hiện có`:**
     - Gắn `invisible="1"` cho `<header>/button[@name='action_update_quantity_on_hand']` trong [product_template_views.xml](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/views/product_template_views.xml) để không ai nhỡ tay chỉnh SL trên hồ sơ sản phẩm (kiểm kê định kỳ đi qua `Tồn kho → Hoạt động → Kiểm kê thực tế`).
     - Ghi đè `action_update_quantity_on_hand()` trong [product_template.py](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/models/product_template.py) luôn trả về danh sách tồn kho ở chế độ chỉ đọc (`create=False, edit=False, delete=False`).
  2. **Gia cố logic kế toán cho Bút toán Tồn đầu kỳ (`_calculate_historical_stock_breakdown`):**
     - Quy đổi toàn bộ số lượng PO, SO, POS và `stock.move` về **ĐVT gốc (`product_id.uom_id`)** qua `_compute_quantity()`.
     - Khấu trừ chính xác **hàng trả lại NCC** (`internal -> supplier`) và **hàng khách trả lại** (`customer -> internal`).
     - Tính riêng cho từng biến thể (`variant_ids=[variant.id]`) để không bị nhân bản tồn kho trên sản phẩm nhiều biến thể.
     - **Giữ nguyên 67 mã** chưa bật theo dõi kho trong CSDL để người dùng tự test tay.
  3. **Tài liệu giải thích nguyên lý kế toán:** Cập nhật [GIAI_THICH_NGUYEN_LY_KE_TOAN_TON_KHO.md](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/docs/GIAI_THICH_NGUYEN_LY_KE_TOAN_TON_KHO.md).
  5. **Audit Bảo Mật & Toàn Vẹn Dữ Liệu (`odoo-security`):**
     - **Chặn ghi đè lặp lại:** Chỉ chạy `_auto_sync_stock_from_history()` cho `newly_storable` (chuyển thực sự từ `False → True`), tránh trường hợp Bulk Edit hoặc RPC ghi `is_storable=True` lên mã đang theo dõi kho làm đè số tồn thực tế.
     - **Khóa cả biến thể (`product.product`):** Bổ sung override `action_update_quantity_on_hand()` trên `product.product` trả về danh sách tồn kho chỉ đọc (`create=False, edit=False, delete=False`).
     - **Cô lập công ty (`company_id`):** Bổ sung `company_domain` vào các truy vấn `.sudo().search(...)` trong `_calculate_historical_stock_breakdown()`.
     - **Kiểm thử bảo mật 4/4 đạt 100% (rollback sạch):** User `nhanvien` (`uid=34`) bị chặn `AccessError` khi sửa `is_storable`, nhận view chỉ đọc trên cả `product.template` & `product.product`; ghi lại `is_storable=True` không kích hoạt đồng bộ lại hay spam Chatter; HTTP 200.
- **File đã thay đổi / tạo mới:**
  - `odoo/custom_addons/qba/views/product_template_views.xml`
  - `odoo/custom_addons/qba/models/product_template.py`
  - `docs/GIAI_THICH_NGUYEN_LY_KE_TOAN_TON_KHO.md` (Mới)
  - `SESSION_STATE.md`

---

## 5. Việc Cần Làm Tiếp Theo (Backlog / Pending Tasks)

- [x] Gỡ bỏ nút `Tính Tồn Kho Theo Mua/Bán` khỏi form sản phẩm ✅
- [x] Ẩn/khóa nút `Cập nhật số lượng` với nhân viên thường & ghi log Chatter tồn đầu kỳ ✅
- [x] Viết file giải thích nguyên lý kế toán tồn kho (`docs/GIAI_THICH_NGUYEN_LY_KE_TOAN_TON_KHO.md`) ✅
- [ ] Người dùng test tay trên nhóm 67 mã chưa bật theo dõi kho.
- [ ] Xác định & sửa lỗi `"Thêm một dòng"` trên 4 tab Xe, Động cơ, Hộp số, Cầu (cần nội dung `"Xem thông tin kỹ thuật"` hoặc bật Chrome remote debugging).
