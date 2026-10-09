# -*- coding: utf-8 -*-
from odoo import models, fields, api


class QbaProductImage(models.Model):
    _name = "qba.product.image"
    _description = "Ảnh Phụ Sản Phẩm QBA"
    _inherit = ["image.mixin"]
    _order = "sequence, id"

    name = fields.Char(string="Tên / Mô tả ảnh", default="Ảnh chi tiết")
    image_1920 = fields.Image(string="Hình ảnh", max_width=1920, max_height=1920, required=True)
    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Sản phẩm",
        required=True,
        ondelete="cascade",
        index=True
    )
    sequence = fields.Integer(string="Thứ tự", default=10)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == "Ảnh chi tiết":
                if vals.get("product_tmpl_id"):
                    tmpl = self.env["product.template"].browse(vals["product_tmpl_id"])
                    vals["name"] = f"Ảnh chi tiết - {tmpl.name or ''}".strip()
                else:
                    vals["name"] = "Ảnh chi tiết"
        return super().create(vals_list)
