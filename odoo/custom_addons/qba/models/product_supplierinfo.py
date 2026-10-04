from odoo import models, fields

class ProductSupplierinfo(models.Model):
    _name = 'product.supplierinfo'
    _inherit = ['product.supplierinfo', 'mail.thread', 'mail.activity.mixin']

    price = fields.Float(tracking=True)
    min_qty = fields.Float(tracking=True)
    product_code = fields.Char(tracking=True) 