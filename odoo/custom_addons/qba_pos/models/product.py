# -*- coding: utf-8 -*-
from odoo import models, api, fields


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _get_archived_combinations_per_product_tmpl_id(self, product_tmpl_ids):
        """Toi uu hoa: Chi tinh toan exclusion cho cac san pham co cau hinh bien the (attribute_line_ids)."""
        tmpls_with_attrs = self.env["product.template"].search([
            ("id", "in", product_tmpl_ids),
            ("attribute_line_ids", "!=", False),
        ])
        if not tmpls_with_attrs:
            return {}
        return super()._get_archived_combinations_per_product_tmpl_id(tmpls_with_attrs.ids)

    def _load_pos_data(self, data):
        """Toi uu hoa toc do tai du lieu san pham POS:
        - Bo doc binary image_128 qua ORM (tiet kiem 8s).
        - Tra cuu su ton tai cua anh bang 1 cau SQL nhe (0.007s).
        """
        config = self.env["pos.config"].browse(data["pos.config"]["data"][0]["id"])
        fields_set = set(self._load_pos_data_fields(config.id))
        taxes = self.env["account.tax"].search(self.env["account.tax"]._load_pos_data_domain(data))
        product_fields = taxes._eval_taxes_computation_prepare_product_fields()
        fields_list = list(fields_set.union(product_fields))

        # Tach image_128 khoi danh sach cot ORM doc truc tiep
        has_image_field = "image_128" in fields_list
        read_fields = [f for f in fields_list if f != "image_128"]

        limit_count = config.get_limited_product_count()
        if limit_count:
            products = config.with_context(display_default_code=False, bin_size=True).get_limited_products_loading(read_fields)
        else:
            domain = self._load_pos_data_domain(data)
            products = self._load_product_with_domain(domain, config.id)

        self._add_missing_products(products, config.id, data)

        data["pos.config"]["data"][0]["_product_default_values"] = \
            self.env["account.tax"]._eval_taxes_computation_prepare_product_default_values(product_fields)

        # Xac dinh nhanh san pham co anh bang SQL truc tiep
        if has_image_field:
            self.env.cr.execute("""
                SELECT DISTINCT res_id
                FROM ir_attachment
                WHERE res_model = 'product.template' AND res_field IN ('image_128', 'image_1920')
            """)
            tmpl_ids_with_image = set(r[0] for r in self.env.cr.fetchall())
            self.env.cr.execute("""
                SELECT DISTINCT res_id
                FROM ir_attachment
                WHERE res_model = 'product.product' AND res_field IN ('image_128', 'image_variant_128')
            """)
            var_ids_with_image = set(r[0] for r in self.env.cr.fetchall())

            for product in products:
                product["image_128"] = bool(
                    product["id"] in var_ids_with_image or product["product_tmpl_id"] in tmpl_ids_with_image
                )

        self._process_pos_ui_product_product(products, config)
        return {
            "data": products,
            "fields": fields_list,
        }

