# Mandatory Session Handover & Skill Activation Workflow

**QUY TẮC VẬN HÀNH BẮT BUỘC TRONG MỌI PHIÊN LÀM VIỆC (MANDATORY WORKFLOW):**

## 1. BẮT ĐẦU PHIÊN (Session Start)
- **Đọc file `SESSION_STATE.md` đầu tiên:** Để nắm bắt tức thì bối cảnh, nhánh Git, trạng thái Docker/Database và nhật ký phiên trước. **TUYỆT ĐỐI KHÔNG quét (audit) lại toàn bộ mã nguồn** khi không được yêu cầu cụ thể.
- **Kích hoạt Skill tương ứng:** Xác định loại công việc và áp dụng đúng hướng dẫn từ `.agents/skills/`:
  - `odoo-architect`: Khảo sát bài toán mới, xác định module và ranh giới.
  - `odoo-backend`: ORM models, fields, compute, constraints, scheduled cron jobs.
  - `odoo-frontend`: OWL components, QWeb templates, XML views, JS assets.
  - `odoo-security`: Phân quyền ACL (`ir.model.access.csv`), Record rules, kiểm soát `sudo()`.
  - `odoo-database`: Tối ưu câu lệnh ORM, N+1 queries, indexes, migrations.
  - `odoo-integration`: Controllers, APIs bên ngoài, Webhooks, HMAC signatures.
  - `odoo-ai-rag`: AI chatbot, tìm kiếm phụ tùng, vector, grounding, prompt defense.
  - `odoo-testing`: Kiểm thử tự động, test evidence thực tế.
  - `odoo-code-review` / `ponytail-review`: Rà soát rủi ro, bảo mật và tinh gọn mã nguồn.
  - `odoo-devops`: Vận hành Docker, logs, khởi động dịch vụ, backup an toàn.

## 2. TRIỂN KHAI (Execution)
- Tuân thủ phong cách **Ponytail** (viết ít code nhất có thể, không sinh boilerplate hay abstraction thừa, tái sử dụng code có sẵn).
- Tuân thủ chuẩn **Odoo Community 18** (không dùng tính năng Enterprise, tôn trọng cấu trúc kế thừa và bảo toàn dữ liệu).

## 3. KẾT THÚC PHIÊN HOẶC HOÀN THÀNH CÔNG VIỆC (Session Handover)
- **BẮT BUỘC:** Cập nhật lại file `SESSION_STATE.md` tại thư mục gốc trước khi kết thúc câu trả lời:
  - Thời gian và nội dung việc đã làm.
  - Danh sách file đã chỉnh sửa / tạo mới.
  - Trạng thái kiểm thử / container / commit (nếu có).
  - Ghi chú các công việc tồn đọng (Pending Tasks) cho phiên tiếp theo.

