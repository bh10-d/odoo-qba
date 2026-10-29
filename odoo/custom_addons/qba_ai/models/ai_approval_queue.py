from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError

class QbaAiApprovalQueue(models.Model):
    _name = "qba.ai.approval.queue"
    _description = "Hàng Chờ Admin Duyệt Kiến Thức AI"
    _order = "create_date desc"

    name = fields.Char(string="Tiêu đề câu hỏi / Vấn đề", required=True)
    question = fields.Text(string="Câu hỏi của nhân viên", required=True)
    suggested_answer = fields.Html(string="Câu trả lời đề xuất từ AI / Nhân viên")
    reason = fields.Selection([
        ('low_confidence', 'Độ tin cậy AI thấp'),
        ('no_product_found', 'Không tìm thấy sản phẩm trong DB'),
        ('manual_flag', 'Nhân viên yêu cầu Admin kiểm tra'),
        ('new_knowledge', 'Kiến thức mới cần xác minh')
    ], string="Lý do vào hàng chờ", default='low_confidence', required=True)

    state = fields.Selection([
        ('pending', 'Chờ duyệt'),
        ('approved', 'Đã duyệt (Lưu vào Knowledge)'),
        ('rejected', 'Từ chối')
    ], string="Trạng thái", default='pending', required=True, index=True)

    user_id = fields.Many2one(
        'res.users',
        string="Người yêu cầu",
        default=lambda self: self.env.user,
        readonly=True,
        index=True
    )
    reviewer_id = fields.Many2one('res.users', string="Người duyệt", readonly=True)
    review_notes = fields.Text(string="Ghi chú người duyệt")
    created_knowledge_id = fields.Many2one('qba.ai.knowledge', string="Bài kiến thức đã tạo", readonly=True)

    def action_approve(self):
        """Admin duyệt -> Tự động chuyển câu trả lời thành 1 bài Kiến Thức Chuẩn"""
        if not self.env.user.has_group('qba_ai.group_qba_ai_manager'):
            raise AccessError(_("Chỉ Quản trị viên QBA AI (AI Manager) mới có quyền duyệt yêu cầu này."))
        for rec in self:
            if rec.state == 'approved':
                continue
            
            # Tạo bản ghi kiến thức mới
            content_val = rec.suggested_answer or f"<p>{rec.question}</p>"
            knowledge = self.env['qba.ai.knowledge'].create({
                'name': rec.name or rec.question[:50],
                'category': 'measurement',
                'content': content_val,
                'summary': rec.question,
                'keywords': rec.name,
                'active': True
            })
            
            rec.write({
                'state': 'approved',
                'reviewer_id': self.env.user.id,
                'created_knowledge_id': knowledge.id
            })

    def action_reject(self):
        """Từ chối câu trả lời"""
        if not self.env.user.has_group('qba_ai.group_qba_ai_manager'):
            raise AccessError(_("Chỉ Quản trị viên QBA AI (AI Manager) mới có quyền từ chối yêu cầu này."))
        for rec in self:
            rec.write({
                'state': 'rejected',
                'reviewer_id': self.env.user.id
            })

    @api.model_create_multi
    def create(self, vals_list):
        is_ai_manager = self.env.user.has_group("qba_ai.group_qba_ai_manager")
        for vals in vals_list:
            if not vals.get("user_id"):
                vals["user_id"] = self.env.user.id
            if vals.get("state") and vals.get("state") != "pending":
                if not is_ai_manager:
                    raise AccessError(_("Chỉ Quản trị viên QBA AI mới có quyền tạo bản ghi hàng chờ ở trạng thái khác 'Chờ duyệt'."))
        return super().create(vals_list)

    def write(self, vals):
        is_ai_manager = self.env.user.has_group("qba_ai.group_qba_ai_manager")
        if not is_ai_manager:
            protected_fields = {"state", "reviewer_id", "review_notes", "created_knowledge_id"}
            if any(f in vals for f in protected_fields):
                raise AccessError(_("Chỉ Quản trị viên QBA AI mới có quyền thay đổi thông tin kiểm duyệt hàng chờ."))
            for rec in self:
                if rec.state != "pending":
                    raise AccessError(_("Không thể chỉnh sửa yêu cầu đã được phê duyệt hoặc từ chối."))
        return super().write(vals)

    def unlink(self):
        if not self.env.user.has_group("qba_ai.group_qba_ai_manager"):
            raise AccessError(_("Chỉ Quản trị viên QBA AI mới có quyền xóa bản ghi hàng chờ phê duyệt."))
        return super().unlink()
