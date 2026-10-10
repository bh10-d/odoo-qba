# -*- coding: utf-8 -*-
import logging
import requests
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from .api_utils import get_odoo_api_headers

_logger = logging.getLogger(__name__)


class QbaProductWebBatchUnlinkWizard(models.TransientModel):
    _name = "qba.product.web.batch.unlink.wizard"
    _description = "Xác nhận hủy liên kết sản phẩm ERP với Website hàng loạt"

    product_tmpl_ids = fields.Many2many(
        "product.template",
        string="Sản phẩm sẽ hủy liên kết",
        required=True
    )
    product_count = fields.Integer(
        string="Số lượng sản phẩm",
        compute="_compute_product_count"
    )

    api_url = fields.Char(
        string="Backend API",
        default=lambda self: self._get_default_api_url()
    )

    @api.model
    def _get_default_api_url(self):
        param = self.env['ir.config_parameter'].sudo().get_param('qba.website_api_url')
        if param and param.strip():
            url = param.strip().rstrip('/')
            if 'localhost:5000' in url or '127.0.0.1:5000' in url:
                return url.replace('localhost:5000', 'host.docker.internal:5000').replace('127.0.0.1:5000', 'host.docker.internal:5000')
            return url
        return 'http://host.docker.internal:5000/api/v1'

    @api.model
    def default_get(self, fields_list):
        res = super(QbaProductWebBatchUnlinkWizard, self).default_get(fields_list)
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids') or []

        if active_model == 'product.template' and active_ids:
            valid_prods = self.env['product.template'].browse(active_ids).exists().filtered(lambda p: p.is_website_linked)
            res['product_tmpl_ids'] = [(6, 0, valid_prods.ids)]
        elif not res.get('product_tmpl_ids'):
            linked_prods = self.env['product.template'].search([('is_website_linked', '=', True)])
            res['product_tmpl_ids'] = [(6, 0, linked_prods.ids)]
        return res

    @api.depends('product_tmpl_ids')
    def _compute_product_count(self):
        for rec in self:
            rec.product_count = len(rec.product_tmpl_ids.exists())

    def _get_candidate_endpoints(self):
        candidates = []
        custom_api = (self.api_url or '').strip().rstrip('/')
        if custom_api:
            candidates.append(custom_api)
            if 'localhost:5000' in custom_api or '127.0.0.1:5000' in custom_api:
                candidates.append(custom_api.replace('localhost:5000', 'host.docker.internal:5000').replace('127.0.0.1:5000', 'host.docker.internal:5000'))

        param = self.env['ir.config_parameter'].sudo().get_param('qba.website_api_url')
        if param and param.strip():
            p = param.strip().rstrip('/')
            candidates.append(p)
            if 'localhost:5000' in p or '127.0.0.1:5000' in p:
                candidates.append(p.replace('localhost:5000', 'host.docker.internal:5000').replace('127.0.0.1:5000', 'host.docker.internal:5000'))

        candidates.append('http://host.docker.internal:5000/api/v1')
        candidates.append('http://172.18.0.1:5000/api/v1')
        candidates.append('http://localhost:5000/api/v1')

        dedup = []
        for c in candidates:
            if c and c not in dedup:
                dedup.append(c)
        return dedup

    def action_confirm_batch_unlink(self):
        """Xác nhận gỡ bỏ liên kết website trên cả Odoo và Express PostgreSQL"""
        self.ensure_one()
        targets = self.product_tmpl_ids.exists().filtered(lambda p: p.is_website_linked)
        if not targets:
            raise UserError(_("Không có sản phẩm nào trong danh sách đang liên kết với Website."))

        odoo_ids = targets.ids
        web_ids = [p.website_product_id for p in targets if p.website_product_id]
        total_count = len(targets)

        # 1. Gửi lệnh xóa hàng loạt sang Backend Express TRƯỚC TIÊN (không sửa Odoo nếu API lỗi)
        endpoints = self._get_candidate_endpoints()
        sync_success = False
        auth_failed = False
        connected = False
        last_error = ""

        payload = {
            'odooProductIds': odoo_ids,
            'webProductIds': web_ids,
        }
        headers = get_odoo_api_headers(self.env)

        for ep in endpoints:
            unlink_endpoint = f"{ep}/products/batch-unlink-odoo"
            try:
                resp = requests.post(unlink_endpoint, json=payload, headers=headers, timeout=6.0)
                connected = True
                if resp.status_code == 200:
                    sync_success = True
                    break
                elif resp.status_code == 401:
                    auth_failed = True
                    last_error = "Khóa bí mật HMAC không chính xác hoặc không khớp với Backend (Mã 401 Unauthorized)"
                    break
                elif resp.status_code == 404:
                    # Endpoint batch chưa có (bản cũ), tiếp tục thử fallback
                    continue
                else:
                    last_error = f"Máy chủ phản hồi mã lỗi HTTP {resp.status_code}"
            except Exception as e:
                last_error = str(e)
                continue

        # Nếu phát hiện lỗi xác thực HMAC (401), DỪNG NGAY LẬP TỨC và KHÔNG xóa dữ liệu Odoo
        if auth_failed:
            raise UserError(_(
                "Xác thực thất bại (401 Unauthorized)!\n\n"
                "Khóa bí mật HMAC nhập trong Cài đặt không chính xác hoặc không khớp với cấu hình ODOO_SHARED_SECRET trên máy chủ Backend.\n\n"
                "Toàn bộ dữ liệu trên Odoo đã được GIỮ NGUYÊN 100%, không có sản phẩm nào bị gỡ bỏ."
            ))

        # Fallback: Nếu API batch 404, thử gọi endpoint đơn lẻ từng sp
        if not sync_success and web_ids and not auth_failed:
            for ep in endpoints:
                try:
                    success_count = 0
                    for wid in web_ids:
                        try:
                            r = requests.post(f"{ep}/products/{wid}/link-odoo", json={'odooProductId': None}, headers=headers, timeout=2.0)
                            if r.status_code == 200:
                                success_count += 1
                            elif r.status_code == 401:
                                auth_failed = True
                                break
                        except Exception:
                            pass
                    if auth_failed:
                        raise UserError(_(
                            "Xác thực thất bại (401 Unauthorized)!\n\n"
                            "Khóa bí mật HMAC nhập trong Cài đặt không chính xác hoặc không khớp với cấu hình ODOO_SHARED_SECRET trên máy chủ Backend.\n\n"
                            "Toàn bộ dữ liệu trên Odoo đã được GIỮ NGUYÊN 100%."
                        ))
                    if success_count > 0:
                        sync_success = True
                        break
                except UserError:
                    raise
                except Exception:
                    continue

        if not sync_success:
            raise UserError(_(
                "Không thể đồng bộ với máy chủ Website Express!\n\n"
                "Chi tiết lỗi: %s\n\n"
                "Thao tác hủy liên kết đã bị DỪNG LẠI để đảm bảo tính an toàn và tính đồng bộ dữ liệu giữa Odoo ERP và Website."
            ) % (last_error or "Không kết nối được tới bất kỳ cổng API nào"))

        # 2. CHỈ KHI máy chủ Website đã xác nhận xóa thành công (200), mới xóa thông tin liên kết trên Odoo
        targets.write({
            'website_product_url': False,
            'website_product_id': False,
            'website_product_slug': False,
            'website_link_date': False,
        })

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Đã hủy liên kết hàng loạt",
                "message": f"Đã gỡ bỏ liên kết Website thành công cho {total_count} sản phẩm trên cả Odoo ERP và Website!",
                "type": "success",
                "sticky": False,
            }
        }

