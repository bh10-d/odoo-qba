# Project Session State & Handover

Tài liệu này lưu trữ trạng thái làm việc và nhật ký bàn giao giữa các phiên làm việc (chat sessions).
**Mỗi phiên làm việc mới BẮT ĐẦU bằng việc đọc file này và KẾT THÚC bằng việc cập nhật file này.**

---

## 1. Thông Tin Môi Trường & Kiến Trúc Hiện Tại (Baseline)

- **Dự án:** QBA Odoo 18 Community (Phụ tùng ô tô xe tải nặng Q.BA)
- **Nhánh Git hiện tại:** `hotfix/non-admin-create-product-uom`
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

- **Thời gian:** 2026-11-23 08:46 (GMT+7)
- **Nhánh Git:** `hotfix/non-admin-create-product-uom` (tạo từ `origin/main` commit `0f64abc`)
- **Công việc đã hoàn thành:**
  1. **Hotfix cho phép Acc phụ (không phải Admin) chọn Đơn vị tính (`uom_id` & `uom_po_id`) khi tạo mới sản phẩm (`create`), vẫn giữ khóa cứng khi sửa sản phẩm đã lưu (`write`):**
     - Trong [product_template_views.xml](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/views/product_template_views.xml#L22-L28): đổi thuộc tính `readonly` của `uom_id` và `uom_po_id` từ `not is_system_admin` thành `id and not is_system_admin` (mở cho phép chọn khi `id` chưa có — bản ghi mới tạo, và tự động khóa lại chỉ đọc ngay sau khi lưu với acc không phải Admin).
     - Trong [product_template.py](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/models/product_template.py#L552-L561): tự động đồng bộ `uom_po_id` theo cùng nhóm `uom_id` trong `create()` để tránh lỗi ràng buộc nhóm ĐVT của Odoo khi nhân viên chọn ĐVT khác nhóm mặc định (VD: `Kg`, `Mét`, `Lít` thay vì `Cái`).
     - Giữ nguyên khóa bảo vệ `AccessError` trong `write()` cho user không phải Admin khi sửa sản phẩm đã tồn tại.
     - Đã kiểm tra cú pháp Python (`py_compile`) và cấu trúc XML (`xml.etree.ElementTree`) đạt 100% (`SYNTAX_AND_XML_VALIDATION_PASSED`).
- **File đã thay đổi / tạo mới:**
  - `odoo/custom_addons/qba/views/product_template_views.xml`
  - `odoo/custom_addons/qba/models/product_template.py`
  - `SESSION_STATE.md`

---

## 5. Việc Cần Làm Tiếp Theo (Backlog / Pending Tasks)

- [x] Chuẩn hóa List View 1 cột phân cấp A–Z cho `Xe`, `Động cơ`, `Hộp số`, `Cầu` ✅
- [x] Đưa `Bảo hành` mặc định về `0` ngày & tự động đồng bộ `Mô tả bán hàng` (`description_sale`) sang `Mô tả SP` (`technical_specs`) ✅
- [x] Tự động chuyển mã OE từ `<...>` và `brand_sku` sang bảng `OE. Code` (tách dấu `/` thành nhiều dòng, tổng cộng 1.555 dòng trên 1.270 SP) ✅
- [ ] Người dùng test tay trên nhóm 67 mã chưa bật theo dõi kho.
