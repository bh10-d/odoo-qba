from odoo import models, fields, api

class QbaEngine(models.Model):
    _name = "qba.engine"
    _description = "Động cơ xe"
    _order = "complete_name"
    _rec_name = "complete_name"

    name = fields.Char(string="Tên động cơ", required=True, index=True)
    complete_name = fields.Char(
        string="Đầy đủ",
        compute="_compute_complete_name",
        recursive=True,
        store=True,
        index=True
    )
    parent_id = fields.Many2one("qba.engine", string="Danh mục cha", index=True, ondelete="cascade")
    child_ids = fields.One2many("qba.engine", "parent_id", string="Danh mục con")
    parent_path = fields.Char(index=True)

    product_tmpl_ids = fields.Many2many(
        "product.template", "product_engine_rel", "engine_id", "product_id",
        string="Sản phẩm áp dụng"
    )
    product_count = fields.Integer(string="Số sản phẩm", compute="_compute_product_count")

    # Hình ảnh và mô tả
    image_1920 = fields.Image(string="Hình ảnh", max_width=1920, max_height=1920)
    description = fields.Html(string="Mô tả", translate=True, sanitize=False)

    brand = fields.Char(string="Nhãn hiệu")
    capacity = fields.Char(string="Dung tích xy lanh")
    horsepower = fields.Char(string="Mã lực HP")
    torque = fields.Char(string="Lực kéo")
    emission_standard = fields.Char(string="Tiêu chuẩn khí thải")
    category = fields.Char(string="Chủng loại")
    vehicle_models = fields.Char(string="Các mẫu xe sử dụng")
    note = fields.Char(string="Ghi chú thêm")

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for rec in self:
            if rec.parent_id:
                rec.complete_name = f"{rec.parent_id.complete_name} / {rec.name}"
            else:
                rec.complete_name = rec.name

    def _compute_product_count(self):
        for rec in self:
            descendant_ids = self.search([('id', 'child_of', rec.ids)]).ids
            rec.product_count = self.env['product.template'].search_count([
                ('engine_ids', 'in', descendant_ids)
            ])

    def action_view_products(self):
        self.ensure_one()
        descendant_ids = self.search([('id', 'child_of', self.ids)]).ids
        return {
            "name": f"Sản phẩm: {self.complete_name}",
            "type": "ir.actions.act_window",
            "res_model": "product.template",
            "view_mode": "kanban,list,form",
            "views": [(False, "kanban"), (False, "list"), (False, "form")],
            "domain": [("engine_ids", "in", descendant_ids)],
            "context": {"default_engine_ids": [(4, self.id)]},
        }

