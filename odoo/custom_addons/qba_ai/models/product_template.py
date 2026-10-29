# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import AccessError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    spec_value_ids = fields.One2many(
        "qba.product.spec.value",
        "product_tmpl_id",
        string="Thông số kỹ thuật",
        copy=True
    )
    spec_value_count = fields.Integer(
        string="Số lượng thông số",
        compute="_compute_spec_value_count"
    )
    spec_verified_count = fields.Integer(
        string="Số thông số đã duyệt",
        compute="_compute_spec_value_count"
    )
    spec_has_conflict = fields.Boolean(
        string="Có thông số xung đột",
        compute="_compute_spec_value_count"
    )

    spec_category_diagram = fields.Binary(
        related="categ_id.measurement_diagram",
        string="Sơ đồ đo danh mục",
        readonly=True
    )
    spec_category_instructions = fields.Html(
        related="categ_id.measurement_instructions",
        string="Hướng dẫn đo danh mục",
        readonly=True
    )

    @api.depends("spec_value_ids.validation_status", "spec_value_ids.spec_definition_id.active")
    def _compute_spec_value_count(self):
        for rec in self:
            active_values = rec.spec_value_ids.filtered(lambda v: v.spec_definition_id and v.spec_definition_id.active)
            rec.spec_value_count = len(active_values)
            rec.spec_verified_count = len(active_values.filtered(lambda v: v.validation_status == "verified"))
            rec.spec_has_conflict = any(v.validation_status == "conflicted" for v in active_values)

    def action_populate_category_specs(self):
        """Tiện ích: Tải sẵn danh sách thông số kỹ thuật định nghĩa từ danh mục vào sản phẩm nếu chưa có."""
        self.ensure_one()
        if not self.categ_id:
            return
        # Tìm tất cả thông số kỹ thuật liên kết với danh mục này hoặc danh mục cha
        parent_categ_ids = self.env["product.category"].search([("id", "parent_of", self.categ_id.id)]).ids
        spec_defs = self.env["qba.product.spec.definition"].search([
            "|",
            ("category_ids", "=", False),
            ("category_ids", "in", parent_categ_ids),
            ("active", "=", True),
        ])
        existing_spec_ids = self.spec_value_ids.mapped("spec_definition_id").ids
        new_values = []
        for s_def in spec_defs:
            if s_def.id not in existing_spec_ids:
                new_values.append((0, 0, {
                    "spec_definition_id": s_def.id,
                    "validation_status": "unverified",
                    "source": "manual_entry",
                }))
        if new_values:
            self.write({"spec_value_ids": new_values})

    def action_open_spec_parser_wizard(self):
        """Điểm gọi chung (Generic Dispatcher) mở công cụ trích xuất thông số kỹ thuật cho sản phẩm."""
        self.ensure_one()
        if not self.env.user.has_group("qba_ai.group_qba_ai_manager"):
            raise AccessError(_("Chỉ Quản trị viên QBA AI mới có quyền trích xuất thông số kỹ thuật từ tên."))

        return self.env["qba.spec.parser.registry"].open_product_wizard(self)

    def action_open_lc_parser_wizard(self):
        """[DEPRECATED in Phase 4.0] Proxy tương thích ngược gọi sang generic dispatcher."""
        return self.action_open_spec_parser_wizard()

    def action_find_matching_substitutes(self):
        """Mở Trợ lý AI Assistant với chế độ đối chiếu kỹ thuật tự động cho sản phẩm hiện tại."""
        self.ensure_one()
        query = self.default_code or self.name
        assistant = self.env["qba.ai.assistant"].create({
            "user_query": query,
        })
        assistant.action_ask_ai()
        view = self.env.ref("qba_ai.view_qba_ai_assistant_form", raise_if_not_found=False)
        return {
            "type": "ir.actions.act_window",
            "name": _("Đối Chiếu Kỹ Thuật: %s") % query,
            "res_model": "qba.ai.assistant",
            "res_id": assistant.id,
            "view_mode": "form",
            "views": [(view.id if view else False, "form")],
            "target": "current",
        }

    def action_open_ai_assistant_drawer(self):
        """Mở bảng chat Trợ lý AI (Drawer) trực tiếp từ chi tiết sản phẩm, nạp context sản phẩm hiện tại."""
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "qba_ai_assistant_open",
            "params": {
                "product_id": self.id,
                "product_name": self.name,
                "default_code": self.default_code or "",
                "category_name": self.categ_id.complete_name or "",
            }
        }

    @api.model
    def action_open_ai_assistant_general(self):
        """Mở bảng chat Trợ lý AI ở chế độ tìm kiếm chung toàn bộ catalog sản phẩm."""
        return {
            "type": "ir.actions.client",
            "tag": "qba_ai_assistant_open",
            "params": {}
        }

    @api.model
    def action_open_ai_assistant_general_matching(self):
        """Mở giao diện Trợ lý AI Assistant (Wizard đầy đủ) để tra cứu / đối chiếu kỹ thuật & gửi duyệt."""
        return self.env.ref("qba_ai.action_qba_ai_assistant").read()[0]


