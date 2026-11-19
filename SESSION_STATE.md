# Project Session State & Handover

Tài liệu này lưu trữ trạng thái làm việc và nhật ký bàn giao giữa các phiên làm việc (chat sessions).
**Mỗi phiên làm việc mới BẮT ĐẦU bằng việc đọc file này và KẾT THÚC bằng việc cập nhật file này.**

---

## 1. Thông Tin Môi Trường & Kiến Trúc Hiện Tại (Baseline)

- **Dự án:** QBA Odoo 18 Community (Phụ tùng ô tô xe tải nặng Q.BA)
- **Nhánh Git hiện tại:** `feature/oe-code-migration-and-hierarchy-list`
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

- **Thời gian:** 2026-11-19 10:48 (GMT+7)
- **Nhánh Git:** `feature/oe-code-migration-and-hierarchy-list` (tạo mới từ `feature/stock-accounting-opening-balance`)
- **Công việc đã hoàn thành:**
  1. **Xử lý Vấn đề 1 — Chuẩn hóa List View & Search View phân cấp `Xe`, `Động cơ`, `Hộp số`, `Cầu` giống hệt `Danh mục sản phẩm` (`product.category`):**
     - Rút gọn thẻ `<list>` trong [vehicle_views.xml](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/views/vehicle_views.xml#L2-L21), [engine_views.xml](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/views/engine_views.xml#L2-L21), [gearbox_views.xml](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/views/gearbox_views.xml#L2-L21), [axle_views.xml](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/views/axle_views.xml#L2-L21) về duy nhất 1 cột `<field name="display_name"/>` và bổ sung `<search>` view cho phép tìm kiếm theo `complete_name`/`name` và `parent_id`.
     - Gia cố `@api.depends("complete_name")` cho hàm `_compute_display_name()` trong [vehicle.py](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/models/vehicle.py#L67-L76), [engine.py](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/models/engine.py#L65-L74), [gearbox.py](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/models/gearbox.py#L62-L71), [axle.py](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/models/axle.py#L62-L71) để tự động cập nhật `display_name` từ gốc đến ngọn (`CHA / CON / CHÁU`) ngay khi đổi `parent_id` hoặc đổi tên cha.
     - Chuẩn hóa lại cây phân cấp mẫu của `qba.vehicle` trên DB (`FAW`, `THACO`, `THACO / AUMAN`, `THACO / FORLAND`, `THACO / OLLIN`, `THACO / OLLIN / OLLIN 500B`).
  2. **Xử lý Vấn đề 2a — Tự động trích xuất & chuyển đổi toàn bộ mã OE từ `<...>` và `brand_sku` sang bảng `OE. Code` (`qba.product.oe_code`):**
     - Viết hàm `_extract_oe_codes_from_name_and_sku()` trong [product_template.py](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/models/product_template.py#L521-L537): lấy chuỗi trong cặp dấu `<...>` trên tên sản phẩm và trường `brand_sku`, nếu có dấu `/` thì tách thành nhiều dòng riêng biệt, giữ nguyên các định dạng khác và khử trùng lặp.
     - Tích hợp vào `_register_hook()`, `create()`, và `write()` trong [product_template.py](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/models/product_template.py#L909-L942).
     - Kết quả thực tế trên DB: Đã tự động chuyển đổi thành công **1.555 dòng mã OE** cho **1.270 sản phẩm** (ví dụ `XP.007` → `M6600-1003111` hãng `YUCHAI`; `BOMH.003` → tách 2 dòng `612600130777` và `612600130924`).
  3. **Xử lý Vấn đề 2b & 2c — Mặc định `Bảo hành: 0` & Khôi phục đồng bộ `Mô tả bán hàng` → `Mô tả SP`:**
     - Đổi `warranty_days` trong [product_template.py](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/models/product_template.py#L122) về `default=0` (`Không bảo hành`) và gỡ bỏ lệnh SQL ép `0 → 90` ngày trong `_register_hook()`.
     - Khôi phục đầy đủ đoạn SQL trong `_register_hook()` gom `description_sale` (`Mô tả bán hàng`) & `description_purchase` (`Mô tả mua hàng`) vào `internal_notes` rồi đẩy sang `technical_specs` (`Mô tả SP`), đồng thời bổ sung `@api.onchange("description_sale")` và xử lý trong `write()` để khi sửa `Mô tả bán hàng` thì `Mô tả SP` tự động cập nhật theo.
  4. **Audit & Tinh gọn mã nguồn theo bộ Skills (`odoo-code-review`, `ponytail-review`, `odoo-database`, `odoo-security`, `odoo-testing`):**
     - **Hợp nhất & Batching ORM (`_auto_populate_oe_codes`):** Gộp logic tạo `qba.product.oe_code` thành 1 hàm batch duy nhất.
     - **Chống "hồi sinh" mã OE khi sửa tên SP & khi restart server:** Trong `write()`, chỉ gọi `_auto_populate_oe_codes()` khi phần `<...>` hoặc `brand_sku` thực sự thay đổi so với trước khi lưu; trong `_register_hook()`, gắn cờ one-shot `ir.config_parameter` (`qba.product_data_migrated_v1 = '1'`) để bỏ qua SQL migrate ở các lần restart sau (tránh lock/deadlock multi-worker và không bao giờ đẻ lại mã OE khách đã xóa).
     - **Tối ưu single-query `write()` & type-safety cho `description_sale`:** Kiểm tra `isinstance(..., str)` trước `.strip()`; gán thẳng `vals['technical_specs']` trước `super().write(vals)` khi toàn bộ recordset đang trống `technical_specs`.
     - **Rút gọn `_compute_display_name()` trên 4 model phân cấp** về dùng chuẩn `super()._compute_display_name()` (như `product.category`), giữ `@api.depends("complete_name")` (`-12` dòng lặp).
     - **Kiểm thử tự động 6/6 PASS (`ALL_6_AUDIT_FIX_TESTS_PASSED`, rollback sạch):** Bao gồm test tạo mới, xóa OE rồi sửa chính tả tên không hồi sinh OE, đổi `<...>` tự cập nhật OE, `description_sale=False` không crash, cờ `qba.product_data_migrated_v1 == '1'`, và `qba.vehicle` phân cấp `ROOT_V / CHILD_V`.
- **File đã thay đổi / tạo mới:**
  - `odoo/custom_addons/qba/views/vehicle_views.xml`
  - `odoo/custom_addons/qba/views/engine_views.xml`
  - `odoo/custom_addons/qba/views/gearbox_views.xml`
  - `odoo/custom_addons/qba/views/axle_views.xml`
  - `odoo/custom_addons/qba/models/product_template.py`
  - `SESSION_STATE.md`

---

## 5. Việc Cần Làm Tiếp Theo (Backlog / Pending Tasks)

- [x] Chuẩn hóa List View 1 cột phân cấp A–Z cho `Xe`, `Động cơ`, `Hộp số`, `Cầu` ✅
- [x] Đưa `Bảo hành` mặc định về `0` ngày & tự động đồng bộ `Mô tả bán hàng` (`description_sale`) sang `Mô tả SP` (`technical_specs`) ✅
- [x] Tự động chuyển mã OE từ `<...>` và `brand_sku` sang bảng `OE. Code` (tách dấu `/` thành nhiều dòng, tổng cộng 1.555 dòng trên 1.270 SP) ✅
- [ ] Người dùng test tay trên nhóm 67 mã chưa bật theo dõi kho.
