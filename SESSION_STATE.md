# Project Session State & Handover

Tài liệu này lưu trữ trạng thái làm việc và nhật ký bàn giao giữa các phiên làm việc (chat sessions).
**Mỗi phiên làm việc mới BẮT ĐẦU bằng việc đọc file này và KẾT THÚC bằng việc cập nhật file này.**

---

## 1. Thông Tin Môi Trường & Kiến Trúc Hiện Tại (Baseline)

- **Dự án:** QBA Odoo 18 Community (Phụ tùng ô tô xe tải nặng Q.BA)
- **Nhánh Git hiện tại:** `fix/product-ux-defaults-uom-images-fields`
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

- **Thời gian:** 2026-11-24 20:56 (GMT+7)
- **Nhánh Git:** `fix/product-ux-defaults-uom-images-fields` (tạo từ `origin/main` commit `aa5946f`)
- **Công việc đã hoàn thành:**
  1. **Đồng bộ giá trị mặc định tạo mới SP trên mọi menu (`action-873` Tồn kho, `action-935` Mua hàng, Bán hàng, POS)** ([product_template.py](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/models/product_template.py#L40-L44), [product_template_views.xml](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/views/product_template_views.xml#L18-L21)):
     - Đặt mặc định `sale_ok=True`, `purchase_ok=True`, `is_storable=True`, `list_price=0.0` (không fix cứng — user vẫn đổi được khi tạo mới).
     - Đồng bộ `sale_order.py` đổi fallback `warranty_days` từ `90` về `0`.
  2. **Sửa logic Đơn vị tính (`uom_id` / `uom_po_id`) về chuẩn Odoo** ([product_template.py](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/models/product_template.py#L242-L256), [L766-L785](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/models/product_template.py#L766-L785), [product_template_views.xml](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/views/product_template_views.xml#L22-L29)):
     - Bổ sung trường tính toán `has_stock_moves` (batch 1 SQL). Khi sản phẩm **chưa phát sinh nhập/xuất kho** (`not has_stock_moves`), acc phụ được đổi ĐVT thoải mái kể cả sau khi lưu (và tự đồng bộ `uom_po_id` cùng nhóm). Chỉ khóa `readonly` & `AccessError` khi đã có lịch sử dịch chuyển kho.
  3. **Sửa lỗi không xóa được ảnh chính + thêm tab quản lý/sắp xếp ảnh & chọn ảnh chính + kéo thả sắp xếp `OE. Code`** ([product_template_views.xml](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/views/product_template_views.xml#L117-L168), [product_image.py](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/models/product_image.py#L31-L45), [product_responsive.css](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/static/src/css/product_responsive.css#L1183-L1195), [image_lightbox.js](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/static/src/js/image_lightbox.js#L712)):
     - Tăng `z-index: 30; pointer-events: auto` cho `.o_form_image_controls` và loại trừ khỏi click Lightbox để bấm nút xóa/sửa ảnh đại diện chính hoạt động bình thường.
     - Thêm tab **Hình ảnh** trên Form SP cho phép kéo thả sắp xếp (`widget="handle"`), xóa ảnh phụ và nút **Đặt ảnh chính** (`action_set_as_main_image`, đã thêm `tmpl.check_access('write')` bảo mật).
     - Thêm `<field name="sequence" widget="handle"/>` vào bảng `OE. Code` và cập nhật `@api.depends("oe_code_ids.name", "oe_code_ids.sequence")` + `sorted(key=lambda r: (r.sequence, r.id))` để kéo thả cập nhật ngay thứ tự hiển thị.
  4. **Khử trùng lặp bộ lọc & bỏ trường thừa `Cầu xe` (`axle_info`) khỏi form** ([product_template.py](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/models/product_template.py#L46-L65), [L130-L163](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/models/product_template.py#L130-L163), [product_template_views.xml](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/views/product_template_views.xml#L131)):
     - Đổi nhãn `vehicle_ids` → **"Loại xe"**, `axle_ids` → **"Loại cầu"**.
     - Đặt `searchable=False` cho `axle_info` và 4 trường hiển thị Kanban (`vehicles_display`, `engines_display`, `gearboxes_display`, `axles_display`) để bộ lọc không còn bị trùng 4-5 trường gần giống nhau.
     - Gỡ `<field name="axle_info"/>` khỏi Form sản phẩm (giữ cột DB để không mất dữ liệu cũ).
  5. **Sửa triệt để lỗi crash nút `Đã bán` (`sale.report`) do múi giờ cũ `Asia/Saigon` trên PostgreSQL 15 + thông báo thân thiện khi thiếu quyền Sales** ([product_template.py](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/models/product_template.py#L761-L775), [L1004-L1011](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/models/product_template.py#L1004-L1011), [L1444-L1458](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/models/product_template.py#L1444-L1458)):
     - Nguyên nhân thực tế: Tài khoản nhân viên lưu `res_partner.tz = 'Asia/Saigon'`, bị PostgreSQL 15 từ chối (`time zone "Asia/Saigon" not recognized`) khi chạy `read_group` theo ngày trên `sale.report`.
     - Thêm one-shot migration `qba.fix_saigon_tz_v1` đổi toàn bộ `res_partner.tz = 'Asia/Saigon'` sang `'Asia/Ho_Chi_Minh'`, đồng thời kế thừa `res.partner` (`create`/`write`) tự chuẩn hóa nếu có nơi nào ghi `'Asia/Saigon'`.
     - Giữ thêm lớp kiểm tra quyền `has_access('read')` trên `action_view_sales()` trả về thông báo thân thiện nếu acc chưa có quyền Bán hàng.
  6. **Audit sẵn sàng lên Production (`odoo-security`, `odoo-frontend`, `odoo-database`, `ponytail-review`, `odoo-testing`):**
     - **Chống XSS trong Modal xác nhận xóa ảnh (`odoo-frontend`):** Gán `title` và `message` qua `.textContent` thay vì nội suy trực tiếp vào `innerHTML` trong [image_lightbox.js](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/static/src/js/image_lightbox.js#L648-L667).
     - **An toàn mutation `vals` & đồng bộ cache (`odoo-backend`, `odoo-database`):** Sao chép `vals = dict(vals)` trước khi gán `uom_po_id` trong `write()`; bổ sung `self.env.invalidate_all()` sau câu SQL đổi `Asia/Saigon` → `Asia/Ho_Chi_Minh`.
     - **Kiểm thử tự động 6/6 PASS (`ALL_PROD_READINESS_AUDIT_TESTS_PASSED_6_OF_6`, rollback sạch):** Xác nhận toàn bộ mặc định, phân quyền ĐVT trước/sau nhập kho, chuẩn hóa `Asia/Saigon`, báo cáo `sale.report`, sắp xếp `OE. Code`, đặt ảnh chính và lọc trùng trường.
- **File đã thay đổi / tạo mới:**
  - `odoo/custom_addons/qba/models/product_template.py`
  - `odoo/custom_addons/qba/models/product_image.py`
  - `odoo/custom_addons/qba/models/sale_order.py`
  - `odoo/custom_addons/qba/views/product_template_views.xml`
  - `odoo/custom_addons/qba/static/src/css/product_responsive.css`
  - `odoo/custom_addons/qba/static/src/js/image_lightbox.js`
  - `SESSION_STATE.md`

---

## 5. Việc Cần Làm Tiếp Theo (Backlog / Pending Tasks)

- [x] Chuẩn hóa List View 1 cột phân cấp A–Z cho `Xe`, `Động cơ`, `Hộp số`, `Cầu` ✅
- [x] Đưa `Bảo hành` mặc định về `0` ngày & tự động đồng bộ `Mô tả bán hàng` (`description_sale`) sang `Mô tả SP` (`technical_specs`) ✅
- [x] Tự động chuyển mã OE từ `<...>` và `brand_sku` sang bảng `OE. Code` (tách dấu `/` thành nhiều dòng, tổng cộng 1.555 dòng trên 1.270 SP) ✅
- [ ] Người dùng test tay trên nhóm 67 mã chưa bật theo dõi kho.
