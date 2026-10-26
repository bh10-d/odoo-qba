from odoo import models, fields

class ProductCategory(models.Model):
    _inherit = "product.category"

    image_1920 = fields.Image(string="Hình ảnh danh mục", max_width=1920, max_height=1920)
    description = fields.Html(string="Mô tả danh mục", translate=True, sanitize=False)

    def action_view_products(self):
        self.ensure_one()
        all_ids = self.search([('id', 'child_of', self.ids)]).ids
        return {
            "name": f"Sản phẩm: {self.complete_name}",
            "type": "ir.actions.act_window",
            "res_model": "product.template",
            "view_mode": "kanban,list,form",
            "domain": [("categ_id", "in", all_ids)],
            "context": {
                "default_categ_id": self.id,
            },
        }

