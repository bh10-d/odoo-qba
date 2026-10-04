# -*- coding: utf-8 -*-
from odoo import models, fields, api

class QbaProductOeCode(models.Model):
    _name = "qba.product.oe_code"
    _description = "Mã Phụ Tùng Chính Hãng (OE Code)"
    _order = "sequence, id"

    name = fields.Char(string="Mã OE", required=True, index=True)
    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Sản phẩm",
        required=True,
        ondelete="cascade",
        index=True
    )
    brand_id = fields.Many2one("qba.brand", string="Hãng sản xuất / Thương hiệu")
    note = fields.Char(string="Ghi chú / Vị trí áp dụng")
    sequence = fields.Integer(string="Thứ tự", default=10)

    _sql_constraints = [
        ('unique_oe_per_product', 'unique(name, product_tmpl_id)', 'Mã OE này đã tồn tại trên sản phẩm!')
    ]
