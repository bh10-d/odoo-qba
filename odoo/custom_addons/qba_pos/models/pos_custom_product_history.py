# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class PosCustomProductHistory(models.Model):
    _name = "pos.custom.product.history"
    _description = "Lich Su Ten San Pham Nhap Tay POS"
    _order = "use_count desc, last_used_date desc, name asc"
    _inherit = ["pos.load.mixin"]

    name = fields.Char(string="Ten San Pham Nhap Tay", required=True, index="trigram")
    code = fields.Char(string="Ma / Ky Hieu Goi Y", index=True)
    last_price = fields.Float(string="Don Gia Gan Nhat", digits="Product Price", default=0.0)
    use_count = fields.Integer(string="So Lan Da Su Dung", default=1, index=True)
    last_used_date = fields.Datetime(string="Lan Dung Gan Nhat", default=fields.Datetime.now)
    notes = fields.Char(string="Ghi Chu Mac Dinh")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", string="Cong Ty", default=lambda self: self.env.company)

    _sql_constraints = [
        ("name_company_uniq", "unique(name, company_id)", "Ten san pham nhap tay nay da ton tai trong lich su!"),
    ]

    @api.model
    def _load_pos_data_domain(self, data):
        return [("active", "=", True)]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ["id", "name", "code", "last_price", "use_count", "notes"]

    def _load_pos_data(self, data):
        domain = self._load_pos_data_domain(data)
        fields = self._load_pos_data_fields(data["pos.config"]["data"][0]["id"])
        records = self.search_read(domain, fields, order="use_count desc, last_used_date desc", limit=200, load=False)
        return {
            "data": records,
            "fields": fields,
        }

    @api.model
    def record_custom_name(self, name, price=0.0, notes=""):
        """Ghi nho hoac cap nhat lich su ten san pham nhap tay."""
        clean_name = (name or "").strip()
        if not clean_name:
            return False
        company_id = self.env.company.id
        record = self.search([
            ("name", "=ilike", clean_name),
            ("company_id", "=", company_id),
        ], limit=1)
        if record:
            vals = {
                "use_count": record.use_count + 1,
                "last_used_date": fields.Datetime.now(),
            }
            if price > 0:
                vals["last_price"] = price
            if notes:
                vals["notes"] = notes
            record.write(vals)
            return record.id
        else:
            new_record = self.create({
                "name": clean_name,
                "last_price": price if price > 0 else 0.0,
                "use_count": 1,
                "last_used_date": fields.Datetime.now(),
                "notes": notes,
                "company_id": company_id,
            })
            return new_record.id

