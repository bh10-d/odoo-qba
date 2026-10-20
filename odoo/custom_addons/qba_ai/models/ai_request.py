# -*- coding: utf-8 -*-
import json
import logging
from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, AccessError

_logger = logging.getLogger(__name__)


class QbaAiRequest(models.Model):
    _name = "qba.ai.request"
    _description = "Yêu Cầu Hỗ Trợ Dữ Liệu Sản Phẩm & Kỹ Thuật AI"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(
        string="Mã yêu cầu",
        required=True,
        copy=False,
        readonly=True,
        default="New",
        tracking=True,
        index=True,
    )
    request_type = fields.Selection([
        ("missing_product", "Sản phẩm chưa có trong danh mục"),
        ("missing_spec", "Sản phẩm thiếu thông số kỹ thuật"),
        ("spec_conflict", "Thông số thực tế mâu thuẫn / sai lệch"),
        ("substitute_review", "Đề xuất xác minh phụ tùng thay thế"),
    ], string="Loại yêu cầu", required=True, default="missing_product", tracking=True, index=True)

    state = fields.Selection([
        ("submitted", "Đã gửi (Chờ xử lý)"),
        ("in_progress", "Đang xử lý"),
        ("resolved", "Đã xử lý xong"),
        ("rejected", "Từ chối"),
    ], string="Trạng thái", default="submitted", tracking=True, index=True)

    user_id = fields.Many2one(
        "res.users",
        string="Người gửi yêu cầu",
        default=lambda self: self.env.user,
        readonly=True,
        required=True,
        index=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Công ty",
        default=lambda self: self.env.company,
        required=True,
    )
    handler_id = fields.Many2one(
        "res.users",
        string="Admin phụ trách",
        tracking=True,
        index=True,
    )
    product_id = fields.Many2one(
        "product.template",
        string="Sản phẩm liên quan",
        ondelete="set null",
        index=True,
        tracking=True,
    )
    product_code = fields.Char(
        string="Mã SKU",
        related="product_id.default_code",
        readonly=True,
    )
    product_name = fields.Char(
        string="Tên sản phẩm",
        related="product_id.name",
        readonly=True,
    )
    conversation_id = fields.Many2one(
        "qba.ai.conversation",
        string="Cuộc trò chuyện QBA AI",
        ondelete="set null",
        index=True,
    )
    message_id = fields.Many2one(
        "qba.ai.message",
        string="Tin nhắn kích hoạt",
        ondelete="set null",
        index=True,
    )
    raw_query = fields.Char(
        string="Câu hỏi / Từ khóa tìm kiếm",
        readonly=True,
    )
    extracted_specs_json = fields.Text(
        string="Thông số AI đã bóc tách (JSON)",
        help="Lưu trữ cấu trúc thông số kỹ thuật được trích xuất từ câu hỏi",
    )
    user_notes = fields.Text(
        string="Ghi chú của người gửi",
        help="Ghi chú chi tiết, yêu cầu bổ sung từ nhân viên kinh doanh/kỹ thuật",
    )
    admin_feedback = fields.Text(
        string="Phản hồi của Admin",
        tracking=True,
        help="Kết quả xử lý từ Admin, nhân viên gửi yêu cầu có thể xem được nội dung này",
    )
    rejection_reason = fields.Text(
        string="Lý do từ chối",
        tracking=True,
        help="Lý do Admin từ chối yêu cầu (bắt buộc khi trạng thái là Từ chối)",
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "qba_ai_request_attachment_rel",
        "request_id",
        "attachment_id",
        string="Tài liệu / Ảnh chụp đính kèm",
    )

    @api.model_create_multi
    def create(self, vals_list):
        is_manager = self.env.user.has_group("qba_ai.group_qba_ai_manager")
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("qba.ai.request.seq") or "New"

            # Đảm bảo user_id là người dùng hiện tại (nếu không phải manager)
            if not is_manager or not vals.get("user_id"):
                vals["user_id"] = self.env.user.id

            # Người dùng thường chỉ được tạo ở trạng thái 'submitted'
            if not is_manager and vals.get("state") and vals.get("state") != "submitted":
                raise AccessError(_("Người dùng thông thường chỉ có thể tạo yêu cầu ở trạng thái 'Đã gửi'."))

            # Chống trùng lặp (Idempotency control)
            user_id = vals.get("user_id") or self.env.user.id
            raw_query = (vals.get("raw_query") or "").strip()
            req_type = vals.get("request_type") or "missing_product"
            msg_id = vals.get("message_id")
            conv_id = vals.get("conversation_id")

            dup_domain = [
                ("user_id", "=", user_id),
                ("request_type", "=", req_type),
            ]
            if msg_id:
                dup_domain.append(("message_id", "=", msg_id))
            elif conv_id and raw_query:
                dup_domain.extend([
                    ("conversation_id", "=", conv_id),
                    ("raw_query", "=", raw_query),
                    ("create_date", ">=", fields.Datetime.now() - timedelta(seconds=30)),
                ])
            else:
                dup_domain.extend([
                    ("raw_query", "=", raw_query),
                    ("create_date", ">=", fields.Datetime.now() - timedelta(seconds=15)),
                ])

            existing = self.search(dup_domain, limit=1)
            if existing:
                raise ValidationError(_("Yêu cầu này đã được gửi trước đó (Mã: %s). Vui lòng không gửi trùng lặp.") % existing.name)

        return super().create(vals_list)

    @api.model
    def create_from_drawer(self, vals):
        """Tạo yêu cầu hỗ trợ từ Trợ lý QBA AI Drawer và tự động thêm tin nhắn xác nhận vào hội thoại."""
        vals = dict(vals)
        if "state" not in vals:
            vals["state"] = "submitted"
        conv_id = vals.get("conversation_id")
        conv = self.env["qba.ai.conversation"].browse(conv_id).exists() if conv_id else None

        req = self.create(vals)
        if conv:
            type_labels = {
                "missing_product": "Sản phẩm chưa có trong danh mục",
                "missing_spec": "Sản phẩm thiếu thông số kỹ thuật",
                "spec_conflict": "Thông số mâu thuẫn / sai lệch",
                "substitute_review": "Đề xuất xác minh phụ tùng thay thế",
            }
            type_name = type_labels.get(req.request_type, req.request_type)
            confirm_content = (
                f"✅ **Yêu cầu hỗ trợ đã được gửi tới Admin thành công!**\n\n"
                f"- **Mã yêu cầu:** `{req.name}`\n"
                f"- **Phân loại:** {type_name}\n"
                f"- **Trạng thái:** Chờ Admin tiếp nhận xử lý\n\n"
                f"Ban quản trị sẽ cập nhật thông tin và phản hồi sớm nhất. "
                f"Bạn có thể theo dõi tiến độ tại menu *QBA AI Assistant → Yêu cầu của tôi*."
            )
            self.env["qba.ai.message"].create({
                "conversation_id": conv.id,
                "user_id": self.env.user.id,
                "role": "assistant",
                "message_type": "request_confirmation",
                "content": confirm_content,
            })
            conv.last_message_date = fields.Datetime.now()
        return req

    def write(self, vals):
        is_manager = self.env.user.has_group("qba_ai.group_qba_ai_manager")
        protected_fields = {
            "state", "handler_id", "admin_feedback", "rejection_reason",
            "raw_query", "product_id", "conversation_id", "message_id", "request_type"
        }

        if not is_manager:
            for field in vals:
                if field in protected_fields:
                    raise AccessError(_("Bạn không có quyền thay đổi trường '%s' của yêu cầu.") % field)
            for rec in self:
                if rec.state != "submitted":
                    raise AccessError(_("Không thể chỉnh sửa yêu cầu khi đã được tiếp nhận hoặc xử lý."))

        # Kiểm tra điều kiện chuyển trạng thái
        if "state" in vals:
            target_state = vals["state"]
            for rec in self:
                if target_state == "resolved":
                    feedback = vals.get("admin_feedback") or rec.admin_feedback
                    if not feedback or not feedback.strip():
                        raise ValidationError(_("Vui lòng nhập nội dung 'Phản hồi của Admin' trước khi hoàn tất yêu cầu."))
                elif target_state == "rejected":
                    reason = vals.get("rejection_reason") or rec.rejection_reason
                    if not reason or not reason.strip():
                        raise ValidationError(_("Vui lòng nhập 'Lý do từ chối' trước khi từ chối yêu cầu."))

        return super().write(vals)

    def unlink(self):
        if not self.env.user.has_group("qba_ai.group_qba_ai_manager"):
            raise AccessError(_("Chỉ Quản trị viên AI (AI Manager) mới có quyền xóa yêu cầu hỗ trợ."))
        return super().unlink()

    def action_assign_to_me(self):
        self.ensure_one()
        if not self.env.user.has_group("qba_ai.group_qba_ai_manager"):
            raise AccessError(_("Chỉ Quản trị viên AI mới có quyền tiếp nhận xử lý yêu cầu."))
        vals = {"handler_id": self.env.user.id}
        if self.state == "submitted":
            vals["state"] = "in_progress"
        return self.write(vals)

    def action_start_progress(self):
        self.ensure_one()
        if not self.env.user.has_group("qba_ai.group_qba_ai_manager"):
            raise AccessError(_("Chỉ Quản trị viên AI mới có quyền chuyển trạng thái yêu cầu."))
        return self.write({"state": "in_progress"})

    def action_resolve(self):
        self.ensure_one()
        if not self.env.user.has_group("qba_ai.group_qba_ai_manager"):
            raise AccessError(_("Chỉ Quản trị viên AI mới có quyền hoàn tất yêu cầu."))
        if not self.admin_feedback or not self.admin_feedback.strip():
            raise ValidationError(_("Vui lòng nhập 'Phản hồi của Admin' trước khi hoàn tất xử lý."))
        self.write({"state": "resolved"})
        self.message_post(
            body=_("<b>Yêu cầu đã được xử lý xong bởi %s</b><br/>Phản hồi: %s") % (self.env.user.name, self.admin_feedback),
            partner_ids=[self.user_id.partner_id.id] if self.user_id and self.user_id.partner_id else [],
            message_type="notification",
            subtype_xmlid="mail.mt_comment",
        )
        return True

    def action_reject(self):
        self.ensure_one()
        if not self.env.user.has_group("qba_ai.group_qba_ai_manager"):
            raise AccessError(_("Chỉ Quản trị viên AI mới có quyền từ chối yêu cầu."))
        if not self.rejection_reason or not self.rejection_reason.strip():
            raise ValidationError(_("Vui lòng nhập 'Lý do từ chối' trước khi từ chối yêu cầu."))
        self.write({"state": "rejected"})
        self.message_post(
            body=_("<b>Yêu cầu đã bị từ chối bởi %s</b><br/>Lý do: %s") % (self.env.user.name, self.rejection_reason),
            partner_ids=[self.user_id.partner_id.id] if self.user_id and self.user_id.partner_id else [],
            message_type="notification",
            subtype_xmlid="mail.mt_comment",
        )
        return True

    def action_open_conversation(self):
        self.ensure_one()
        if not self.conversation_id:
            raise UserError(_("Yêu cầu này không liên kết với cuộc hội thoại nào."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Hội Thoại QBA AI"),
            "res_model": "qba.ai.conversation",
            "res_id": self.conversation_id.id,
            "views": [[False, "form"]],
            "target": "current",
        }

