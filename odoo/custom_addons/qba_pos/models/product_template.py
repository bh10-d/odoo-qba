# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ProductTemplate(models.Model):
    _inherit = "product.template"

    available_in_pos = fields.Boolean(
        default=True,
        help="Cho phep san pham nay xuat hien va duoc phep ban tren man hinh POS."
    )
    is_custom_manual_product = fields.Boolean(
        string="La san pham nhap tay (Chua co ma)",
        default=False,
        help="Danh dau san pham dung de ban cac mat hang chua co tren he thong va nhap tay ten hang."
    )

    @api.model
    def action_enable_all_products_in_pos(self):
        """Kich hoat available_in_pos cho toan bo san pham hop le va dong bo danh muc POS."""
        products = self.search([
            ("sale_ok", "=", True),
            ("available_in_pos", "=", False),
        ])
        count = len(products)
        if products:
            products.write({"available_in_pos": True})

        # Dong bo them danh muc POS
        self.action_sync_pos_categories()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Cap Nhat POS Thanh Cong"),
                "message": _("Da bat ban hang POS cho %d san pham va dong bo danh muc POS.") % count,
                "type": "success",
                "sticky": False,
            }
        }

    @api.model
    def action_sync_pos_categories(self):
        """Dong bo he thong Danh Muc San Pham (product.category) sang POS Category (pos.category)."""
        ProductCategory = self.env["product.category"]
        PosCategory = self.env["pos.category"]

        master_cat = PosCategory.search([("name", "=", "PHU TUNG Q.BA")], limit=1)
        if not master_cat:
            master_cat = PosCategory.create({
                "name": "PHU TUNG Q.BA",
                "sequence": 1,
            })

        prod_cats = ProductCategory.search([("id", "!=", 1)], order="parent_path asc")
        cat_map = {}

        existing_pos_cats = PosCategory.search([])
        pos_by_name = {c.name: c for c in existing_pos_cats}

        for pc in prod_cats:
            existing = pos_by_name.get(pc.name)
            parent_pos = cat_map.get(pc.parent_id.id) if pc.parent_id and pc.parent_id.id != 1 else master_cat.id
            if not existing:
                existing = PosCategory.create({
                    "name": pc.name,
                    "parent_id": parent_pos,
                    "sequence": pc.id,
                })
                pos_by_name[pc.name] = existing
            else:
                if existing.id != master_cat.id and existing.parent_id.id != parent_pos:
                    existing.write({"parent_id": parent_pos})
            cat_map[pc.id] = existing.id

        # Gan pos_categ_ids cho cac san pham chua co danh muc POS
        for pc_id, pos_cat_id in cat_map.items():
            tmpls = self.search([
                ("categ_id", "=", pc_id),
                ("pos_categ_ids", "=", False)
            ])
            if tmpls:
                tmpls.write({"pos_categ_ids": [(4, pos_cat_id)]})

        return True

    @api.model
    def get_or_create_custom_manual_product(self):
        """Lay hoac tao san pham dung chung cho cac mat hang chua co ma tren he thong."""
        Product = self.env["product.product"]
        product = Product.search([("default_code", "=", "SP_CHUA_CO_MA")], limit=1)
        if not product:
            tmpl = self.create({
                "name": "Hang Chua Co Ma [Nhap Tay]",
                "default_code": "SP_CHUA_CO_MA",
                "type": "service",
                "available_in_pos": True,
                "sale_ok": True,
                "purchase_ok": False,
                "list_price": 0.0,
                "is_custom_manual_product": True,
                "taxes_id": False,
            })
            product = tmpl.product_variant_id
        return product
