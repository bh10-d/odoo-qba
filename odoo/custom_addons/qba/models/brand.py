from odoo import models, fields, api

class QbaBrand(models.Model):
    _name = "qba.brand"
    _description = "Thương hiệu"
    _order = "name"

    name = fields.Char(string="Tên thương hiệu", required=True, index=True)
    product_ids = fields.Many2many(
        "product.template",
        string="Danh sách sản phẩm liên quan",
        compute="_compute_related_products",
        compute_sudo=True
    )
    product_count = fields.Integer(
        string="Số sản phẩm",
        compute="_compute_related_products",
        compute_sudo=True
    )

    def _get_search_domain(self, kw):
        if not kw or not kw.strip():
            return [('id', '=', 0)]
        kw = kw.strip()
        conds = [
            ('name', 'ilike', kw),
            ('brand_id.name', 'ilike', kw),
            ('vehicle_ids.name', 'ilike', kw),
            ('vehicle_ids.complete_name', 'ilike', kw),
            ('oe_code_ids.name', 'ilike', kw),
            ('oe_code_ids.brand_id.name', 'ilike', kw),
            ('brand_sku', 'ilike', kw),
        ]
        if self.id and isinstance(self.id, int):
            conds.append(('brand_id', '=', self.id))
        return ['|'] * (len(conds) - 1) + conds

    @api.depends("name")
    def _compute_related_products(self):
        for rec in self:
            if rec.name and rec.name.strip():
                domain = rec._get_search_domain(rec.name)
                prods = self.env['product.template'].search(domain, order="id desc")
                rec.product_ids = [(6, 0, prods.ids)]
                rec.product_count = len(prods)
            else:
                rec.product_ids = [(6, 0, [])]
                rec.product_count = 0

    @api.onchange("name")
    def _onchange_name(self):
        if self.name and self.name.strip():
            domain = self._get_search_domain(self.name)
            prods = self.env['product.template'].search(domain, order="id desc")
            self.product_ids = [(6, 0, prods.ids)]
            self.product_count = len(prods)
        else:
            self.product_ids = [(6, 0, [])]
            self.product_count = 0

    def action_view_products(self):
        self.ensure_one()
        domain = self._get_search_domain(self.name)
        return {
            "name": f"Sản phẩm liên quan đến: {self.name}",
            "type": "ir.actions.act_window",
            "res_model": "product.template",
            "view_mode": "kanban,list,form",
            "views": [(False, "kanban"), (False, "list"), (False, "form")],
            "domain": domain,
            "context": {"default_brand_id": self.id},
        }
