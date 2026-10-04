# -*- coding: utf-8 -*-
from odoo import models, fields, api

class QbaProductImage(models.Model):
    _name = "qba.product.image"
    _description = "Ảnh Phụ Sản Phẩm QBA"
    _order = "sequence, id"

    name = fields.Char(string="Tên / Mô tả ảnh")
    image_1920 = fields.Image(string="Hình ảnh", max_width=1920, max_height=1920, required=True)
    image_128 = fields.Image(string="Thumbnail", related="image_1920", max_width=128, max_height=128, store=True)
    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Sản phẩm",
        required=True,
        ondelete="cascade",
        index=True
    )
    sequence = fields.Integer(string="Thứ tự", default=10)
