from odoo import models, fields

class QbaBrand(models.Model):
    _name = "qba.brand"
    _description = "Thương hiệu"

    name = fields.Char(string="Tên thương hiệu", required=True)
