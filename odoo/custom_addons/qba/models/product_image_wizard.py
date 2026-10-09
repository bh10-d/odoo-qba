# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class QbaProductImageWizard(models.TransientModel):
    _name = "qba.product.image.wizard"
    _description = "Tải Lên Nhiều Ảnh Sản Phẩm"

    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Sản phẩm",
        required=True,
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        string="Chọn các tệp ảnh",
        help="Có thể chọn cùng lúc nhiều tệp ảnh (JPG, PNG, WebP) từ máy tính",
    )

    def action_upload_images(self):
        self.ensure_one()
        if not self.attachment_ids:
            raise UserError(_("Vui lòng chọn ít nhất một hình ảnh để tải lên."))

        existing_count = len(self.product_tmpl_id.extra_image_ids)
        seq = (existing_count + 1) * 10

        images_to_create = []
        for att in self.attachment_ids:
            if att.datas:
                clean_name = att.name.rsplit(".", 1)[0] if "." in att.name else att.name
                images_to_create.append({
                    "product_tmpl_id": self.product_tmpl_id.id,
                    "name": clean_name or f"Ảnh {self.product_tmpl_id.name}",
                    "image_1920": att.datas,
                    "sequence": seq,
                })
                seq += 10

        if images_to_create:
            self.env["qba.product.image"].create(images_to_create)

        # Xóa các attachment tạm vừa tải lên wizard
        self.attachment_ids.unlink()

        return {"type": "ir.actions.act_window_close"}

