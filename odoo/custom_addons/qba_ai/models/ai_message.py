# -*- coding: utf-8 -*-
import json
from odoo import models, fields, api


class QbaAiMessage(models.Model):
    _name = "qba.ai.message"
    _description = "Tin Nhắn Hội Thoại Trợ Lý AI"
    _order = "id asc"

    conversation_id = fields.Many2one(
        "qba.ai.conversation",
        string="Cuộc hội thoại",
        required=True,
        ondelete="cascade",
        index=True
    )
    user_id = fields.Many2one(
        "res.users",
        string="Người gửi",
        default=lambda self: self.env.user,
        index=True
    )
    role = fields.Selection([
        ("user", "Người dùng"),
        ("assistant", "Trợ lý AI"),
        ("system", "Hệ thống")
    ], string="Vai trò", default="user", required=True, index=True)

    message_type = fields.Selection([
        ("user", "Người dùng"),
        ("greeting", "Chào mừng"),
        ("search_result", "Kết quả tìm kiếm"),
        ("search_empty", "Không tìm thấy phụ tùng"),
        ("request_confirmation", "Xác nhận gửi yêu cầu"),
        ("error", "Thông báo lỗi"),
        ("general", "Chung")
    ], string="Loại tin nhắn", default="general", index=True)

    content = fields.Text(string="Nội dung tin nhắn", required=True)
    matched_product_ids = fields.Many2many(
        "product.template",
        string="Sản phẩm gợi ý"
    )
    matched_products_json = fields.Text(
        string="Dữ liệu thẻ sản phẩm (JSON)",
        help="Lưu trữ cấu trúc thông tin thẻ sản phẩm (tên, mã, giá, thông số, hành động) hiển thị trên giao diện chat"
    )
    explanation_html = fields.Html(
        string="Bảng đối chiếu kỹ thuật chi tiết / Bằng chứng thay thế"
    )
    perf_info_json = fields.Text(
        string="Thông số hiệu năng (JSON)"
    )
    intent = fields.Char(string="Ý định nhận diện")
    intent_label = fields.Char(string="Nhãn ý định")
    intent_badge_html = fields.Html(string="Huy hiệu ý định")

    def to_dict(self):
        """Chuyển đổi bản ghi tin nhắn thành từ điển chuẩn trả về cho frontend chat."""
        self.ensure_one()
        products = []
        if self.matched_products_json:
            try:
                products = json.loads(self.matched_products_json)
            except Exception:
                products = []

        perf = {}
        if self.perf_info_json:
            try:
                perf = json.loads(self.perf_info_json)
            except Exception:
                perf = {}

        return {
            "id": self.id,
            "role": self.role,
            "message_type": self.message_type or ("user" if self.role == "user" else "general"),
            "content": self.content or "",
            "create_date": fields.Datetime.to_string(self.create_date),
            "matched_products": products,
            "explanation_html": self.explanation_html or "",
            "perf_info": perf,
            "intent": self.intent or "",
            "intent_label": self.intent_label or "",
            "intent_badge_html": self.intent_badge_html or "",
        }

