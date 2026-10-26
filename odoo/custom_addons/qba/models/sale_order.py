# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    warranty_days = fields.Integer(string="Bảo hành (ngày)")
    warranty_end_date = fields.Date(
        string="Hạn bảo hành",
        compute="_compute_warranty_end_date",
        store=True,
        readonly=False
    )

    @api.onchange("product_id", "product_template_id")
    def _onchange_product_id_warranty(self):
        for line in self:
            tmpl = line.product_template_id or (line.product_id.product_tmpl_id if line.product_id else False)
            if tmpl:
                line.warranty_days = tmpl.warranty_days or 90

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "warranty_days" not in vals and vals.get("product_id"):
                product = self.env["product.product"].browse(vals["product_id"])
                vals["warranty_days"] = product.product_tmpl_id.warranty_days or 90
        return super().create(vals_list)

    @api.depends("warranty_days", "order_id.date_order", "order_id.state")
    def _compute_warranty_end_date(self):
        for line in self:
            if not line.warranty_days:
                line.warranty_end_date = False
                continue
            base_date = False
            if line.order_id and line.order_id.date_order:
                base_date = line.order_id.date_order.date()
            elif fields.Date.today():
                base_date = fields.Date.today()

            if base_date:
                line.warranty_end_date = base_date + timedelta(days=line.warranty_days)
            else:
                line.warranty_end_date = False

