# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import AccessError


class ProductCategory(models.Model):
    _inherit = "product.category"

    tech_spec_definition_ids = fields.Many2many(
        "qba.product.spec.definition",
        "qba_spec_def_category_rel",
        "category_id",
        "spec_def_id",
        string="Thông số kỹ thuật áp dụng",
        help="Danh sách các thông số kỹ thuật định nghĩa cho danh mục này. "
             "Sản phẩm thuộc danh mục sẽ được áp dụng các thông số này."
    )
    tech_introduction = fields.Html(
        string="Mô tả danh mục",
        help="Mô tả công dụng, vị trí lắp đặt và đặc tính của nhóm phụ tùng này."
    )
    naming_convention = fields.Html(
        string="Cách đặt tên / Cú pháp tìm kiếm",
        help="Cú pháp mẫu quy ước đặt tên sản phẩm theo thông số kích thước (dành cho nhân viên và AI học)."
    )
    measurement_instructions = fields.Html(
        string="Cách đo chi tiết",
        help="Hướng dẫn chi tiết các bước và vị trí cần đo (A, B, C, D...)."
    )
    measurement_diagram = fields.Binary(
        string="Ảnh hướng dẫn cách đo",
        attachment=True,
        help="Sơ đồ hoặc ảnh chụp các vị trí đo đạc tham chiếu (A, B, C, D...)."
    )
    measurement_diagram_filename = fields.Char(
        string="Tên file ảnh đo lường"
    )
    category_image = fields.Binary(
        string="Hình ảnh danh mục",
        attachment=True,
        help="Hình ảnh đại diện / minh họa danh mục (tỉ lệ ngang 3 : cao 4) gồm bao bì, catalog, mẫu phụ tùng."
    )
    category_image_filename = fields.Char(
        string="Tên file ảnh danh mục"
    )
    tech_notes = fields.Html(
        string="Lưu ý kỹ thuật & Gợi ý AI",
        help="Các lưu ý về sai số đo đạc, dung sai cho phép hoặc chỉ dẫn đặc biệt cho AI gợi ý sản phẩm."
    )

    def action_create_new_spec(self):
        """Mở modal tạo mới thông số kỹ thuật với danh mục hiện tại đã được gán sẵn."""
        self.ensure_one()
        return {
            "name": _("Tạo Thông số kỹ thuật áp dụng"),
            "type": "ir.actions.act_window",
            "res_model": "qba.product.spec.definition",
            "view_mode": "form",
            "views": [(self.env.ref("qba_ai.view_qba_product_spec_definition_form").id, "form")],
            "target": "new",
            "context": {
                **self.env.context,
                "active_test": False,
                "default_category_ids": [(6, 0, [self.id])],
            },
        }

    def action_open_spec_parser_wizard(self):
        """Điểm gọi chung (Generic Dispatcher) mở công cụ trích xuất thông số kỹ thuật cho toàn danh mục."""
        self.ensure_one()
        if not self.env.user.has_group("qba_ai.group_qba_ai_manager"):
            raise AccessError(_("Chỉ Quản trị viên QBA AI mới có quyền trích xuất thông số kỹ thuật từ tên."))

        return self.env["qba.spec.parser.registry"].open_category_wizard(self)

    def action_open_lc_parser_wizard(self):
        """[DEPRECATED in Phase 4.0] Proxy tương thích ngược gọi sang generic dispatcher."""
        return self.action_open_spec_parser_wizard()

