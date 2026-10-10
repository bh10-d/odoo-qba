from odoo import models, fields, api

class QbaGearbox(models.Model):
    _name = "qba.gearbox"
    _description = "Hộp số xe"
    _order = "complete_name"
    _rec_name = "complete_name"

    name = fields.Char(string="Mã hộp số", required=True, index=True)
    complete_name = fields.Char(
        string="Đầy đủ",
        compute="_compute_complete_name",
        recursive=True,
        store=True,
        index=True
    )
    parent_id = fields.Many2one("qba.gearbox", string="Danh mục cha", index=True, ondelete="cascade")
    child_ids = fields.One2many("qba.gearbox", "parent_id", string="Danh mục con")
    parent_path = fields.Char(index=True)

    product_tmpl_ids = fields.Many2many(
        "product.template", "product_gearbox_rel", "gearbox_id", "product_id",
        string="Sản phẩm áp dụng"
    )
    product_count = fields.Integer(string="Số sản phẩm", compute="_compute_product_count")

    brand = fields.Char(string="Nhãn hiệu")
    ratio = fields.Char(string="Ratio")
    category = fields.Char(string="Chủng loại")
    note = fields.Char(string="Ghi chú")
    vehicle_models = fields.Char(string="Loại xe sử dụng")

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for rec in self:
            if rec.parent_id:
                rec.complete_name = f"{rec.parent_id.complete_name} / {rec.name}"
            else:
                rec.complete_name = rec.name

    def _compute_product_count(self):
        for rec in self:
            rec.product_count = len(rec.product_tmpl_ids)

    def action_view_products(self):
        self.ensure_one()
        return {
            "name": f"Sản phẩm: {self.complete_name}",
            "type": "ir.actions.act_window",
            "res_model": "product.template",
            "view_mode": "kanban,list,form",
            "views": [(False, "kanban"), (False, "list"), (False, "form")],
            "domain": [("gearbox_ids", "in", [self.id])],
            "context": {"default_gearbox_ids": [(4, self.id)]},
        }

