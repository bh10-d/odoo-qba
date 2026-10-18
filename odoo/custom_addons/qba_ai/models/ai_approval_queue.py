from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError

class QbaAiApprovalQueue(models.Model):
    _name = "qba.ai.approval.queue"
    _description = "Hàng Chờ Admin Duyệt Kiến Thức AI"
    _order = "create_date desc"

    name = fields.Char(string="Tiêu đề câu hỏi / Vấn đề", required=True)
    question = fields.Text(string="Câu hỏi của nhân viên", required=True)
    suggested_answer = fields.Text(string="Câu trả lời đề xuất từ AI / Nhân viên")
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

    reviewer_id = fields.Many2one('res.users', string="Người duyệt")
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
            knowledge = self.env['qba.ai.knowledge'].create({
                'name': rec.name or rec.question[:50],
                'category': 'measurement',
                'content': f"<p>{rec.suggested_answer or rec.question}</p>",
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
            if vals.get("state") and vals.get("state") != "pending":
                if not is_ai_manager:
                    raise AccessError(_("Chỉ Quản trị viên QBA AI mới có quyền tạo bản ghi hàng chờ ở trạng thái khác 'Chờ duyệt'."))
        return super().create(vals_list)

    def write(self, vals):
        if "state" in vals and not self.env.user.has_group("qba_ai.group_qba_ai_manager"):
            for rec in self:
                if vals["state"] != rec.state:
                    raise AccessError(_("Chỉ Quản trị viên QBA AI mới có quyền thay đổi trạng thái phê duyệt hàng chờ."))
        return super().write(vals)
