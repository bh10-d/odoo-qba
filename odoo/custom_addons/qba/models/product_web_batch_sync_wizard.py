# -*- coding: utf-8 -*-
import logging
import requests
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from .api_utils import get_odoo_api_headers

_logger = logging.getLogger(__name__)


class QbaProductWebBatchSyncWizard(models.TransientModel):
    _name = "qba.product.web.batch.sync.wizard"
    _description = "Đồng bộ liên kết sản phẩm Odoo với Website theo mã SKU"

    mode = fields.Selection([
        ('selected', 'Chỉ các sản phẩm được chọn'),
        ('all_unlinked', 'Toàn bộ sản phẩm chưa có liên kết Web trong kho'),
    ], string="Phạm vi đồng bộ", default='selected', required=True)

    product_tmpl_ids = fields.Many2many(
        "product.template",
        string="Sản phẩm Odoo áp dụng"
    )
    product_count = fields.Integer(
        string="Số lượng sản phẩm",
        compute="_compute_product_count"
    )

    skip_already_linked = fields.Boolean(
        string="Bỏ qua sản phẩm đã liên kết trước đó",
        default=True,
        help="Nếu bật, hệ thống sẽ giữ nguyên các liên kết hiện có và chỉ xử lý những mã chưa có link"
    )

    state = fields.Selection([
        ('draft', 'Sẵn sàng'),
        ('done', 'Hoàn tất'),
    ], string="Trạng thái", default='draft')

    matched_count = fields.Integer(string="Số mã khớp thành công", default=0, readonly=True)
    unmatched_count = fields.Integer(string="Số mã chưa có trên Web", default=0, readonly=True)
    skipped_count = fields.Integer(string="Số mã bỏ qua", default=0, readonly=True)
    result_message = fields.Char(string="Thông báo kết quả", readonly=True)

    line_ids = fields.One2many(
        "qba.product.web.batch.sync.line",
        "wizard_id",
        string="Chi tiết đối soát"
    )

    api_url = fields.Char(
        string="Backend API",
        default=lambda self: self._get_default_api_url()
    )
    site_url = fields.Char(
        string="Website Public",
        default=lambda self: self._get_default_site_url()
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
    def _get_default_site_url(self):
        param = self.env['ir.config_parameter'].sudo().get_param('qba.website_public_url')
        if param and param.strip():
            return param.strip().rstrip('/')
        return 'http://localhost:3000'

    @api.model
    def default_get(self, fields_list):
        res = super(QbaProductWebBatchSyncWizard, self).default_get(fields_list)
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids') or []
        
        # Chỉ nhận active_ids khi người dùng mở từ danh sách sản phẩm (product.template)
        if active_model == 'product.template' and active_ids:
            valid_prods = self.env['product.template'].browse(active_ids).exists()
            if valid_prods:
                res['product_tmpl_ids'] = [(6, 0, valid_prods.ids)]
                res['mode'] = 'selected'
            else:
                res['mode'] = 'all_unlinked'
                res['product_tmpl_ids'] = [(6, 0, [])]
        else:
            res['mode'] = 'all_unlinked'
            res['product_tmpl_ids'] = [(6, 0, [])]
        return res

    @api.depends('product_tmpl_ids', 'mode')
    def _compute_product_count(self):
        for rec in self:
            if rec.mode == 'selected':
                rec.product_count = len(rec.product_tmpl_ids.exists())
            else:
                rec.product_count = self.env['product.template'].search_count([
                    ('is_website_linked', '=', False),
                    ('default_code', '!=', False)
                ])

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

    def action_start_sync(self):
        """Khởi chạy quét đối chiếu SKU và đồng bộ 2 chiều với Website"""
        self.ensure_one()

        # 1. Xác định danh sách sản phẩm Odoo cần xử lý
        if self.mode == 'selected':
            targets = self.product_tmpl_ids.exists()
        else:
            targets = self.env['product.template'].search([
                ('default_code', '!=', False)
            ])

        if not targets:
            raise UserError(_("Không tìm thấy sản phẩm nào để xử lý."))

        skipped_records = self.env['product.template']
        if self.skip_already_linked:
            skipped_records = targets.filtered(lambda p: p.is_website_linked)
            targets = targets - skipped_records

        valid_targets = targets.filtered(lambda p: bool(p.default_code and p.default_code.strip()))
        if not valid_targets:
            raise UserError(_("Không có sản phẩm nào có mã SKU (Mã nội bộ) hợp lệ để thực hiện đối soát."))

        # 2. Chuẩn bị payload gửi sang Express API
        site_url = (self.site_url or self._get_default_site_url()).rstrip('/')
        items = [{'odooId': p.id, 'sku': p.default_code.strip()} for p in valid_targets]

        endpoints = self._get_candidate_endpoints()
        connected = False
        working_ep = None
        response_data = None
        last_error = ""

        headers = get_odoo_api_headers(self.env)
        for ep in endpoints:
            sync_endpoint = f"{ep}/products/sync-by-sku"
            try:
                resp = requests.post(
                    sync_endpoint,
                    json={
                        'items': items,
                        'publicBaseUrl': site_url,
                    },
                    headers=headers,
                    timeout=20.0
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('success'):
                        connected = True
                        working_ep = ep
                        response_data = data.get('data', {})
                        self.env['ir.config_parameter'].sudo().set_param('qba.website_api_url', working_ep)
                        self.api_url = working_ep
                        break
                    else:
                        last_error = data.get('error', {}).get('message', 'API trả về lỗi không xác định')
                elif resp.status_code == 401:
                    raise UserError(_(
                        "Xác thực thất bại (401 Unauthorized)!\n\n"
                        "Khóa bí mật HMAC nhập trong Cài đặt không chính xác hoặc không khớp với cấu hình ODOO_SHARED_SECRET trên máy chủ Backend.\n\n"
                        "Toàn bộ dữ liệu trên Odoo được GIỮ NGUYÊN 100%."
                    ))
                else:
                    last_error = f"Mã lỗi HTTP {resp.status_code}"
            except UserError:
                raise
            except Exception as e:
                last_error = str(e)
                continue

        if not connected or not response_data:
            raise UserError(_("Không thể kết nối tới máy chủ Website API Express! Chi tiết: %s. Vui lòng kiểm tra dịch vụ Backend trên cổng 5000.") % last_error)

        # 3. Xử lý kết quả trả về từ Express
        matched_items = response_data.get('matched', [])
        unmatched_items = response_data.get('unmatched', [])

        self.line_ids.unlink()
        line_vals = []

        # Xử lý các mã khớp thành công
        for item in matched_items:
            odoo_id = item.get('odooId')
            prod = self.env['product.template'].browse(odoo_id)
            if prod.exists():
                prod.write({
                    'website_product_url': item.get('webUrl') or '',
                    'website_product_id': item.get('webId') or 0,
                    'website_product_slug': item.get('slug') or '',
                    'website_link_date': fields.Datetime.now(),
                })
                line_vals.append({
                    'wizard_id': self.id,
                    'product_tmpl_id': prod.id,
                    'sku': item.get('sku') or prod.default_code or '',
                    'product_name': prod.name,
                    'web_name': item.get('name') or '',
                    'web_url': item.get('webUrl') or '',
                    'state': 'success',
                })

        # Xử lý các mã chưa tìm thấy trên Web
        for item in unmatched_items:
            odoo_id = item.get('odooId')
            prod = self.env['product.template'].browse(odoo_id)
            if prod.exists():
                line_vals.append({
                    'wizard_id': self.id,
                    'product_tmpl_id': prod.id,
                    'sku': item.get('sku') or prod.default_code or '',
                    'product_name': prod.name,
                    'web_name': '',
                    'web_url': '',
                    'state': 'not_found',
                })

        # Ghi nhận các mã đã bỏ qua (nếu có)
        for prod in skipped_records[:50]:
            line_vals.append({
                'wizard_id': self.id,
                'product_tmpl_id': prod.id,
                'sku': prod.default_code or '',
                'product_name': prod.name,
                'web_name': '(Đã liên kết từ trước)',
                'web_url': prod.website_product_url or '',
                'state': 'skipped',
            })

        if line_vals:
            self.env['qba.product.web.batch.sync.line'].create(line_vals)

        self.matched_count = len(matched_items)
        self.unmatched_count = len(unmatched_items)
        self.skipped_count = len(skipped_records)
        self.state = 'done'
        self.result_message = _(
            "Đồng bộ thành công! Đã ghép nối %s sản phẩm. Chưa tìm thấy trên Web: %s sản phẩm. Bỏ qua: %s sản phẩm."
        ) % (self.matched_count, self.unmatched_count, self.skipped_count)

        return {
            "type": "ir.actions.act_window",
            "name": "Kết quả đồng bộ liên kết Website theo SKU",
            "res_model": "qba.product.web.batch.sync.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
        }


class QbaProductWebBatchSyncLine(models.TransientModel):
    _name = "qba.product.web.batch.sync.line"
    _description = "Chi tiết từng dòng đối soát liên kết SKU"

    wizard_id = fields.Many2one("qba.product.web.batch.sync.wizard", string="Wizard", ondelete="cascade", required=True)
    product_tmpl_id = fields.Many2one("product.template", string="Sản phẩm Odoo")
    sku = fields.Char(string="Mã SKU")
    product_name = fields.Char(string="Tên sản phẩm Odoo")
    web_name = fields.Char(string="Tên bài viết Website")
    web_url = fields.Char(string="Link Web")
    state = fields.Selection([
        ('success', 'Đã liên kết thành công'),
        ('not_found', 'Không tìm thấy trên Web'),
        ('skipped', 'Bỏ qua (Đã có link)'),
    ], string="Trạng thái", default='success')

