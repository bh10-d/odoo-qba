from odoo import models, fields, api

class QbaAxle(models.Model):
    _name = "qba.axle"
    _description = "Cầu xe"
    _order = "complete_name"
    _rec_name = "complete_name"

    name = fields.Char(string="Tên cầu", required=True, index=True)
    complete_name = fields.Char(
        string="Đầy đủ",
        compute="_compute_complete_name",
        recursive=True,
        store=True,
        index=True
    )
    parent_id = fields.Many2one("qba.axle", string="Danh mục cha", index=True, ondelete="cascade")
    child_ids = fields.One2many("qba.axle", "parent_id", string="Danh mục con")
    parent_path = fields.Char(index=True)

    product_tmpl_ids = fields.Many2many(
        "product.template", "product_axle_rel", "axle_id", "product_id",
        string="Sản phẩm áp dụng"
    )
    product_count = fields.Integer(string="Số sản phẩm", compute="_compute_product_count")

    # Hình ảnh và mô tả
    image_1920 = fields.Image(string="Hình ảnh", max_width=1920, max_height=1920)
    description = fields.Html(string="Mô tả", translate=True, sanitize=False)

    brand = fields.Char(string="Hãng sản xuất")
    category = fields.Char(string="Chủng loại cầu")
    ratio = fields.Char(string="Tỷ số truyền")
    tonnage = fields.Char(string="Tải trọng")
    note = fields.Char(string="Ghi chú")

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for rec in self:
            if rec.parent_id:
                rec.complete_name = f"{rec.parent_id.complete_name} / {rec.name}"
            else:
                rec.complete_name = rec.name

    def _compute_product_count(self):
        descendants_map = {rec.id: self.search([('id', 'child_of', rec.ids)]).ids for rec in self}
        all_descendants = list({d_id for d_list in descendants_map.values() for d_id in d_list})
        counts = {}
        if all_descendants:
            self.env.cr.execute("""
                SELECT axle_id, count(DISTINCT product_id)
                FROM product_axle_rel
                WHERE axle_id IN %s
                GROUP BY axle_id
            """, [tuple(all_descendants)])
            counts = dict(self.env.cr.fetchall())
        for rec in self:
            d_ids = descendants_map.get(rec.id, [])
            rec.product_count = sum(counts.get(d_id, 0) for d_id in d_ids)

    def action_view_products(self):
        self.ensure_one()
        descendant_ids = self.search([('id', 'child_of', self.ids)]).ids
        return {
            "name": f"Sản phẩm: {self.complete_name}",
            "type": "ir.actions.act_window",
            "res_model": "product.template",
            "view_mode": "kanban,list,form",
            "views": [(False, "kanban"), (False, "list"), (False, "form")],
            "domain": [("axle_ids", "in", descendant_ids)],
            "context": {"default_axle_ids": [(4, self.id)]},
        }

