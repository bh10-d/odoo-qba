from odoo import models, fields, api


DEFAULT_CATEGORY_DESC_TEMPLATE = """
<div style="font-size: 14px; line-height: 1.6; color: #1e293b;">
    <p><b>Công dụng &amp; Dấu hiệu nhận biết:</b></p>
    <ul>
        <li>Mô tả vị trí lắp đặt, chức năng truyền động / làm việc của phụ tùng...</li>
        <li>Nếu phụ tùng mòn / hỏng → triệu chứng nhận biết trên xe...</li>
    </ul>
    <p><b>Cách đặt tên:</b></p>
    <p style="font-weight: 600; color: #b91c1c;">[Tên danh mục] ØA / B ... ØC / ØD</p>
    <p><b>Cách đo:</b></p>
    <ul>
        <li><b>A:</b> Đo đường kính ngoài (Ø ngoài)...</li>
        <li><b>B:</b> Đếm số răng / số nia / thông số thứ 2...</li>
        <li><b>C:</b> Đo đường kính trong (Ø trong)...</li>
        <li><b>D:</b> Đo kích thước vòng / chiều cao / độ dày...</li>
    </ul>
</div>
"""


class ProductCategory(models.Model):
    _inherit = "product.category"

    image_1920 = fields.Image(string="Hình ảnh danh mục", max_width=1920, max_height=1920)
    measurement_image = fields.Image(string="Hình ảnh sơ đồ cách đo", max_width=1920, max_height=1920)
    description = fields.Html(
        string="Mô tả danh mục",
        translate=True,
        sanitize=False,
    )

    def action_insert_description_template(self):
        """Chèn nhanh khung mẫu chuẩn (Công dụng, Cách đặt tên, Cách đo) cho bất kỳ danh mục nào"""
        for rec in self:
            if not rec.description or rec.description.strip() in ("", "<p><br></p>"):
                rec.description = DEFAULT_CATEGORY_DESC_TEMPLATE
        return True

    def action_view_products(self):
        self.ensure_one()
        all_ids = self.search([('id', 'child_of', self.ids)]).ids
        return {
            "name": f"Sản phẩm: {self.complete_name}",
            "type": "ir.actions.act_window",
            "res_model": "product.template",
            "view_mode": "kanban,list,form",
            "views": [(False, "kanban"), (False, "list"), (False, "form")],
            "domain": [("categ_id", "in", all_ids)],
            "context": {
                "default_categ_id": self.id,
            },
        }
