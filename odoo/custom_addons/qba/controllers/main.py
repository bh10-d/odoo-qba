# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request, Response


class QbaProductImageController(http.Controller):

    @http.route('/qba/product_images/<int:product_tmpl_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_product_images(self, product_tmpl_id, **kwargs):
        product = request.env['product.template'].browse(product_tmpl_id).exists()
        if not product:
            variant = request.env['product.product'].browse(product_tmpl_id).exists()
            if variant and variant.product_tmpl_id:
                product = variant.product_tmpl_id
        if not product:
            return Response(json.dumps([]), content_type='application/json')
        product.check_access('read')

        images = []
        seen_checksums = set()
        Attachment = request.env['ir.attachment'].sudo()

        # 1. Thu thập checksum của ảnh đại diện chính (nếu có) để tránh trùng lặp
        main_att = Attachment.search([
            ('res_model', '=', 'product.template'),
            ('res_id', '=', product.id),
            ('res_field', '=', 'image_1920'),
        ], limit=1)
        if main_att and main_att.checksum:
            seen_checksums.add(main_att.checksum)

        # 2. Ảnh đại diện chính của sản phẩm
        if product.image_1920:
            clean_name = product.name or 'Sản phẩm'
            images.append({
                'id': 0,
                'src': f'/web/image/product.template/{product.id}/image_1920',
                'title': f'{clean_name} (Ảnh chính)'
            })

        # 3. Toàn bộ ảnh phụ từ bảng qba.product.image (batch query 1 lần khử N+1)
        extra_imgs = product.extra_image_ids
        if extra_imgs:
            extra_atts = Attachment.search([
                ('res_model', '=', 'qba.product.image'),
                ('res_id', 'in', extra_imgs.ids),
                ('res_field', '=', 'image_1920'),
            ])
            for att in extra_atts:
                if att.checksum:
                    seen_checksums.add(att.checksum)
            for img in extra_imgs:
                images.append({
                    'id': f'extra_{img.id}',
                    'src': f'/web/image/qba.product.image/{img.id}/image_1920',
                    'title': img.name or f'Ảnh phụ #{img.id}'
                })

        # 4. Toàn bộ ảnh đính kèm từ ir.attachment (tải lên qua chatter, tài liệu đính kèm)
        extra_attachments = Attachment.search([
            ('res_model', '=', 'product.template'),
            ('res_id', '=', product.id),
            ('res_field', '=', False),
            ('mimetype', '=like', 'image/%'),
        ], order='id asc')

        for att in extra_attachments:
            if att.checksum and att.checksum in seen_checksums:
                continue
            if att.checksum:
                seen_checksums.add(att.checksum)

            clean_title = att.name or 'Ảnh đính kèm'
            if '.' in clean_title:
                clean_title = clean_title.rsplit('.', 1)[0]
            images.append({
                'id': f'att_{att.id}',
                'src': f'/web/image/{att.id}',
                'title': f'{clean_title} (Ảnh đính kèm)'
            })

        return Response(json.dumps(images), content_type='application/json')
