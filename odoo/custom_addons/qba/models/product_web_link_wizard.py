# -*- coding: utf-8 -*-
import logging
import re
import requests
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from .api_utils import get_odoo_api_headers

_logger = logging.getLogger(__name__)


class QbaProductWebLinkWizard(models.TransientModel):
    _name = "qba.product.web.link.wizard"
    _description = "Hỗ trợ liên kết sản phẩm ERP với Website SEO"

    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Sản phẩm ERP (Nguồn gốc chính)",
        required=True
    )
    product_name = fields.Char(
        string="Tên sản phẩm Odoo",
        related="product_tmpl_id.name",
        readonly=True
    )
    product_code = fields.Char(
        string="Mã nội bộ (SKU)",
        related="product_tmpl_id.default_code",
        readonly=True
    )
    product_oe_codes = fields.Char(
        string="Mã OE / Part No",
        related="product_tmpl_id.oe_codes_display",
        readonly=True
    )
    product_qty = fields.Float(
        string="Tồn kho Odoo",
        related="product_tmpl_id.qty_available",
        readonly=True
    )
    product_price = fields.Float(
        string="Giá bán Odoo",
        related="product_tmpl_id.list_price",
        readonly=True
    )

    # 1. Chế độ dán đường link trực tiếp
    target_url = fields.Char(
        string="Đường link Website (URL)",
        help="Dán URL sản phẩm trên web (vd: https://phutungotoquyba.com/products/loc-nhot-dong-co-15 hoặc http://localhost:3000/products/15)"
    )
    web_product_id = fields.Integer(
        string="ID Sản phẩm Web"
    )
    web_product_slug = fields.Char(
        string="Slug Web"
    )

    # 2. Chế độ tra cứu trực tiếp qua API
    search_query = fields.Char(
        string="Từ khóa tìm kiếm trên Website",
        help="Nhập tên sản phẩm, mã part number, hoặc mã nội bộ trên web để tìm kiếm"
    )
    candidate_ids = fields.One2many(
        "qba.product.web.link.candidate",
        "wizard_id",
        string="Kết quả tìm kiếm từ Web"
    )
    candidate_count = fields.Integer(
        string="Số kết quả tìm thấy",
        compute="_compute_candidate_count"
    )
    api_status_message = fields.Char(
        string="Trạng thái kết nối",
        readonly=True
    )
    api_status_state = fields.Selection([
        ('info', 'Thông tin'),
        ('success', 'Thành công'),
        ('warning', 'Cảnh báo'),
        ('danger', 'Lỗi'),
    ], string="Mức độ thông báo", default='info')

    # Cấu hình kết nối API & Website
    api_url = fields.Char(
        string="Địa chỉ Backend API",
        default=lambda self: self._get_default_api_url()
    )
    site_url = fields.Char(
        string="Địa chỉ Website Public",
        default=lambda self: self._get_default_site_url()
    )

    sync_to_web = fields.Boolean(
        string="Cập nhật ngược lên Web (Ghi nhận mã Odoo)",
        default=True,
        help="Khi bật, hệ thống sẽ gửi ID sản phẩm Odoo sang Web để đánh dấu sản phẩm trên Web là hàng có sẵn tại kho QBA"
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
        res = super(QbaProductWebLinkWizard, self).default_get(fields_list)
        active_id = self.env.context.get('active_id') or self.env.context.get('default_product_tmpl_id')
        if active_id:
            product = self.env['product.template'].browse(active_id)
            if product.exists():
                res['product_tmpl_id'] = product.id
                res['target_url'] = product.website_product_url or ''
                res['web_product_id'] = product.website_product_id or 0
                res['web_product_slug'] = product.website_product_slug or ''
                first_oe = product.oe_code_ids[0].name if product.oe_code_ids else ''
                res['search_query'] = product.default_code or first_oe or product.name or ''
        return res

    @api.depends('candidate_ids')
    def _compute_candidate_count(self):
        for rec in self:
            rec.candidate_count = len(rec.candidate_ids)

    def _resolve_url_to_product(self, url):
        """Phân tích URL để lấy ID và slug sản phẩm, có gọi API kiểm chứng nếu có kết nối"""
        if not url:
            return 0, '', None
        clean_url = url.strip().split("?")[0].split("#")[0].rstrip("/")
        parts = clean_url.split("/")
        if not parts:
            return 0, '', None

        last_seg = parts[-1]
        MAX_INT = 2147483647
        candidate_id = 0

        # Nếu đoạn cuối chỉ toàn chữ số (vd /products/153)
        if last_seg.isdigit():
            val = int(last_seg)
            if 0 < val <= MAX_INT:
                candidate_id = val
        else:
            # Nếu đoạn cuối có dạng slug-153
            match = re.search(r'-(\d+)$', last_seg)
            if match:
                try:
                    val = int(match.group(1))
                    if 0 < val <= MAX_INT:
                        candidate_id = val
                except (ValueError, TypeError):
                    pass

        # Thử gọi API Express để xác minh và lấy thông tin chính xác nhất
        endpoints = self._get_candidate_endpoints()
        identifiers_to_try = []
        if candidate_id:
            identifiers_to_try.append(str(candidate_id))
        identifiers_to_try.append(last_seg)

        for ident in identifiers_to_try:
            for ep in endpoints:
                try:
                    resp = requests.get(f"{ep}/products/{ident}", timeout=2.0)
                    if resp.status_code == 200:
                        data = resp.json().get('data', {})
                        if data and data.get('id'):
                            return int(data['id']), data.get('slug', last_seg), data
                except Exception:
                    continue

        if candidate_id:
            return candidate_id, last_seg, None

        return 0, last_seg, None

    @api.onchange('target_url')
    def _onchange_target_url(self):
        if self.target_url:
            p_id, p_slug, _ = self._resolve_url_to_product(self.target_url)
            self.web_product_id = p_id
            self.web_product_slug = p_slug
        else:
            self.web_product_id = 0
            self.web_product_slug = ''

    def _get_candidate_endpoints(self):
        """Danh sách các endpoint API Express tiềm năng (ưu tiên host.docker.internal cho Docker)"""
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

    def _reopen_wizard_action(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "qba.product.web.link.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
        }

    def action_search_web(self):
        """Gọi Express API để tra cứu danh sách sản phẩm trên Website SEO"""
        self.ensure_one()
        query = (self.search_query or '').strip()
        if not query:
            raise UserError(_("Vui lòng nhập từ khóa hoặc mã phụ tùng để tìm kiếm."))

        self.candidate_ids.unlink()

        site_url = (self.site_url or self._get_default_site_url()).rstrip('/')
        endpoints = self._get_candidate_endpoints()

        connected = False
        working_endpoint = None
        products = []

        for ep in endpoints:
            api_url = f"{ep}/products"
            try:
                resp = requests.get(
                    api_url,
                    params={'search': query, 'limit': 15},
                    timeout=2.5
                )
                if resp.status_code == 200:
                    data = resp.json()
                    products = data.get('data', [])
                    connected = True
                    working_endpoint = ep
                    self.env['ir.config_parameter'].sudo().set_param('qba.website_api_url', working_endpoint)
                    self.api_url = working_endpoint
                    break
            except Exception as e:
                _logger.info("Thử endpoint %s thất bại: %s", api_url, str(e))
                continue

        if connected:
            if not products:
                self.api_status_state = 'warning'
                msg = f"Không tìm thấy bài viết nào trên Website khớp với từ khóa '{query}'. Vui lòng thử từ khóa khác hoặc dán link trực tiếp."
                self.api_status_message = msg
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Không tìm thấy sản phẩm",
                        "message": msg,
                        "type": "warning",
                        "sticky": False,
                        "next": self._reopen_wizard_action(),
                    }
                }

            self.api_status_state = 'success'
            self.api_status_message = f"Kết nối thành công! Tìm thấy {len(products)} bài viết trên Web qua [{working_endpoint}]."

            candidate_vals = []
            for p in products:
                p_id = p.get('id')
                p_slug = p.get('slug') or ''
                p_name = p.get('name') or ''
                p_part = p.get('partNumber') or ''
                p_code = p.get('internalCode') or ''
                p_price = float(p.get('price') or 0.0)

                images = p.get('images') or []
                first_img = images[0].get('imageUrl') if images else ''
                if first_img and not first_img.startswith('http'):
                    img_host = site_url if site_url.endswith('/') else site_url + '/'
                    clean_img = first_img.lstrip('/')
                    full_img_url = f"{img_host}{clean_img}"
                else:
                    full_img_url = first_img or '/web/static/img/placeholder.png'

                web_url = f"{site_url}/products/{p_slug}-{p_id}" if p_slug else f"{site_url}/products/{p_id}"

                candidate_vals.append({
                    'wizard_id': self.id,
                    'web_id': p_id,
                    'name': p_name,
                    'slug': p_slug,
                    'part_number': p_part,
                    'internal_code': p_code,
                    'price': p_price,
                    'image_url': full_img_url,
                    'web_url': web_url,
                    'is_odoo_linked': bool(p.get('odooProductId') or p.get('isOdooLinked')),
                })

            if candidate_vals:
                self.env['qba.product.web.link.candidate'].create(candidate_vals)

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Đã tìm thấy bài viết",
                    "message": f"Tìm thấy {len(products)} bài viết phù hợp trên Website SEO.",
                    "type": "info",
                    "sticky": False,
                    "next": self._reopen_wizard_action(),
                }
            }
        else:
            self.api_status_state = 'danger'
            msg = "Không thể kết nối máy chủ API Express. Hãy kiểm tra server Express cổng 5000 đang bật hoặc dán link thủ công ở trên."
            self.api_status_message = msg
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Lỗi kết nối API",
                    "message": msg,
                    "type": "danger",
                    "sticky": False,
                    "next": self._reopen_wizard_action(),
                }
            }

    def action_search_by_code(self):
        """Tìm nhanh theo Mã SKU Odoo"""
        self.ensure_one()
        self.search_query = self.product_code or ''
        return self.action_search_web()

    def action_search_by_oe(self):
        """Tìm nhanh theo Mã OE đầu tiên của Odoo"""
        self.ensure_one()
        oe_codes = [oe.name.strip() for oe in self.product_tmpl_id.oe_code_ids if oe.name]
        self.search_query = oe_codes[0] if oe_codes else (self.product_oe_codes or '')
        return self.action_search_web()

    def action_search_by_name(self):
        """Tìm nhanh theo Tên sản phẩm Odoo"""
        self.ensure_one()
        self.search_query = self.product_name or ''
        return self.action_search_web()

    def action_test_connection(self):
        """Kiểm tra đường truyền tới API Web và xác thực chữ ký HMAC"""
        self.ensure_one()
        endpoints = self._get_candidate_endpoints()
        connected = False
        working_ep = None
        auth_failed = False
        headers = get_odoo_api_headers(self.env)

        for ep in endpoints:
            test_url = f"{ep}/products/verify-auth"
            try:
                resp = requests.get(test_url, headers=headers, timeout=3.0)
                if resp.status_code == 200:
                    connected = True
                    working_ep = ep
                    self.env['ir.config_parameter'].sudo().set_param('qba.website_api_url', working_ep)
                    self.api_url = working_ep
                    break
                elif resp.status_code == 401:
                    auth_failed = True
                    working_ep = ep
                    break
            except Exception:
                continue

        if auth_failed:
            self.api_status_state = 'danger'
            msg = f"Lỗi xác thực (401 Unauthorized): Khóa bí mật HMAC không khớp với cấu hình Backend! Vui lòng kiểm tra lại trong Cài đặt."
            self.api_status_message = msg
            title = "Xác thực HMAC thất bại"
            notif_type = "danger"
        elif connected:
            self.api_status_state = 'success'
            msg = f"Kết nối và xác thực chữ ký HMAC thành công tới Web qua [{working_ep}]!"
            self.api_status_message = msg
            title = "Kết nối API thành công"
            notif_type = "success"
        else:
            self.api_status_state = 'danger'
            msg = f"Không thể kết nối tới máy chủ Website Express! Vui lòng kiểm tra lại dịch vụ Backend trên cổng 5000."
            self.api_status_message = msg
            title = "Kết nối API thất bại"
            notif_type = "danger"

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": msg,
                "type": notif_type,
                "sticky": False,
                "next": self._reopen_wizard_action(),
            }
        }

    def action_confirm_link(self):
        """Xác nhận lưu đường link và ID sản phẩm web vào sản phẩm Odoo"""
        self.ensure_one()
        url = (self.target_url or '').strip()

        resolved_id = self.web_product_id
        resolved_slug = self.web_product_slug

        if url:
            detected_id, detected_slug, _ = self._resolve_url_to_product(url)
            if detected_id:
                resolved_id = detected_id
                resolved_slug = detected_slug
            elif not resolved_id:
                raise UserError(_("Không thể nhận diện được mã bài viết từ đường link đã nhập. Vui lòng kiểm tra lại URL hoặc dùng công cụ tra cứu phía trên."))

        if not url and not resolved_id:
            raise UserError(_("Vui lòng dán đường link website hoặc chọn một sản phẩm từ kết quả tìm kiếm."))

        if not url and resolved_id:
            site_url = (self.site_url or self._get_default_site_url()).rstrip('/')
            url = f"{site_url}/products/{resolved_slug or resolved_id}-{resolved_id}"

        # 1. Đồng bộ sang Backend Express TRƯỚC (nếu bật sync_to_web). Tuyệt đối KHÔNG sửa Odoo nếu API lỗi
        if self.sync_to_web and resolved_id:
            sync_success, sync_error = self._notify_express_web_linked(resolved_id, self.product_tmpl_id.id)
            if sync_error == "401_UNAUTHORIZED":
                raise UserError(_(
                    "Xác thực thất bại (401 Unauthorized)!\n\n"
                    "Khóa bí mật HMAC nhập trong Cài đặt không chính xác hoặc không khớp với cấu hình ODOO_SHARED_SECRET trên máy chủ Backend.\n\n"
                    "Thao tác liên kết đã bị HỦY BỎ. Dữ liệu trên Odoo được GIỮ NGUYÊN 100%."
                ))
            if not sync_success:
                raise UserError(_(
                    "Không thể đồng bộ với máy chủ Website Express!\n\n"
                    "Chi tiết lỗi: %s\n\n"
                    "Thao tác liên kết đã bị DỪNG LẠI để tránh lệch dữ liệu giữa 2 hệ thống. Dữ liệu Odoo được giữ nguyên."
                ) % sync_error)

        # 2. CHỈ KHI máy chủ Website đã xác nhận (hoặc không bật sync_to_web), mới lưu vào Odoo
        vals = {
            'website_product_url': url,
            'website_product_id': resolved_id,
            'website_product_slug': resolved_slug or '',
            'website_link_date': fields.Datetime.now(),
        }
        self.product_tmpl_id.write(vals)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Liên kết thành công",
                "message": f"Đã liên kết sản phẩm [{self.product_tmpl_id.name}] với bài viết Website SEO (ID: {resolved_id}) thành công trên cả 2 hệ thống!",
                "type": "success",
                "sticky": False,
            }
        }

    def _notify_express_web_linked(self, web_product_id, odoo_product_id):
        """Gửi thông báo tới Backend Express để lưu odoo_product_id vào PostgreSQL Web"""
        endpoints = self._get_candidate_endpoints()
        last_error = "Không kết nối được tới bất kỳ cổng API nào"
        headers = get_odoo_api_headers(self.env)
        for ep in endpoints:
            endpoint = f"{ep}/products/{web_product_id}/link-odoo"
            try:
                resp = requests.post(
                    endpoint,
                    json={'odooProductId': odoo_product_id},
                    headers=headers,
                    timeout=3.0
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('success'):
                        return True, ""
                    else:
                        last_error = data.get('error', {}).get('message', 'Lỗi không xác định từ API')
                elif resp.status_code == 401:
                    # Nếu trả về 401 Unauthorized, dừng ngay lập tức không thử tiếp
                    return False, "401_UNAUTHORIZED"
                else:
                    last_error = f"Mã HTTP {resp.status_code}: {resp.text[:100]}"
            except Exception as e:
                last_error = str(e)
                continue
        return False, last_error

    def action_unlink(self):
        """Hủy liên kết sản phẩm này trên cả Odoo và Web SEO"""
        self.ensure_one()
        return self.product_tmpl_id.action_unlink_website()


class QbaProductWebLinkCandidate(models.TransientModel):
    _name = "qba.product.web.link.candidate"
    _description = "Ứng viên sản phẩm tìm thấy từ Website SEO"

    wizard_id = fields.Many2one(
        "qba.product.web.link.wizard",
        string="Wizard liên kết",
        ondelete="cascade",
        required=True
    )
    web_id = fields.Integer(
        string="ID Web",
        required=True
    )
    name = fields.Char(
        string="Tên bài viết trên Web",
        required=True
    )
    slug = fields.Char(
        string="Slug"
    )
    part_number = fields.Char(
        string="Mã OE / Part No"
    )
    internal_code = fields.Char(
        string="Mã nội bộ Web"
    )
    price = fields.Float(
        string="Giá niêm yết"
    )
    image_url = fields.Char(
        string="Link ảnh"
    )
    web_url = fields.Char(
        string="Link bài viết Web"
    )
    is_odoo_linked = fields.Boolean(
        string="Đã nối Odoo"
    )

    def action_choose_candidate(self):
        """Chọn bài viết này và lưu liên kết với sản phẩm Odoo"""
        self.ensure_one()
        wizard = self.wizard_id
        wizard.web_product_id = self.web_id
        wizard.target_url = self.web_url
        wizard.web_product_slug = self.slug
        return wizard.action_confirm_link()
