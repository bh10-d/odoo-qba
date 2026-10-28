# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class QbaProductBulkEditWizard(models.TransientModel):
    _name = "qba.product.bulk.edit.wizard"
    _description = "Chỉnh sửa thuộc tính sản phẩm hàng loạt (Admin)"

    # Phạm vi áp dụng
    scope = fields.Selection([
        ('selected', 'Chỉ áp dụng cho các sản phẩm đã tick chọn'),
        ('all', 'Áp dụng cho TẤT CẢ sản phẩm theo bộ lọc hiện tại'),
    ], string="Phạm vi áp dụng", default='selected', required=True)

    filter_domain_repr = fields.Char(string="Biểu thức bộ lọc")
    selected_count = fields.Integer(string="Số lượng đang chọn", compute="_compute_counts")
    total_filter_count = fields.Integer(string="Tổng số theo bộ lọc", compute="_compute_counts")

    product_tmpl_ids = fields.Many2many(
        "product.template",
        string="Sản phẩm được chọn",
    )
    product_count = fields.Integer(
        string="Số lượng sản phẩm áp dụng",
        compute="_compute_counts"
    )

    # 1. Theo dõi hàng tồn kho
    change_is_storable = fields.Boolean(
        string="Thay đổi Theo dõi hàng tồn kho",
        default=False
    )
    is_storable = fields.Boolean(
        string="Theo dõi hàng tồn kho",
        default=True,
        help="Tích chọn để Odoo quản lý số lượng tồn kho (stock.quant). "
             "Lịch sử các lần nhập xuất trước đó vẫn được bảo lưu đầy đủ."
    )

    # 2. Điểm bán hàng (POS)
    change_available_in_pos = fields.Boolean(
        string="Thay đổi Bán trên POS",
        default=False
    )
    available_in_pos = fields.Boolean(
        string="Điểm bán hàng (POS)",
        default=True,
        help="Tích chọn để hiển thị sản phẩm trên màn hình thu ngân POS bán lẻ nhanh."
    )
    change_pos_categ = fields.Boolean(
        string="Thay đổi Danh mục POS",
        default=False
    )
    pos_categ_ids = fields.Many2many(
        "pos.category",
        string="Danh mục POS"
    )

    # 3. Đơn vị tính
    change_uom = fields.Boolean(
        string="Thay đổi Đơn vị tính",
        default=False
    )
    uom_id = fields.Many2one(
        "uom.uom",
        string="Đơn vị tính mới",
        help="Đơn vị tính cơ bản của sản phẩm."
    )
    sync_uom_po = fields.Boolean(
        string="Đồng bộ Đơn vị tính mua hàng",
        default=True,
        help="Tự động đồng bộ Đơn vị tính mua hàng (uom_po_id) sang cùng đơn vị tính hoặc cùng nhóm."
    )

    # 4. Trạng thái Bán & Mua
    change_sale_ok = fields.Boolean(
        string="Thay đổi Trạng thái Bán hàng",
        default=False
    )
    sale_ok = fields.Boolean(
        string="Có thể bán",
        default=True
    )
    change_purchase_ok = fields.Boolean(
        string="Thay đổi Trạng thái Mua hàng",
        default=False
    )
    purchase_ok = fields.Boolean(
        string="Có thể mua",
        default=True
    )

    # 5. Khóa chốt an toàn xác nhận rủi ro (Fail-Safe Lock)
    confirm_risk = fields.Boolean(
        string="Xác nhận rủi ro kho & ĐVT",
        default=False,
        help="Bắt buộc tích chọn để xác nhận Quản trị viên đã hiểu rõ tác động đến số lượng tồn kho và đơn vị tính."
    )

    @api.model
    def default_get(self, fields_list):
        res = super(QbaProductBulkEditWizard, self).default_get(fields_list)
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids') or []
        active_domain = self.env.context.get('active_domain')

        # ƯU TIÊN 1: Nếu người dùng đã tick chọn các sản phẩm cụ thể (active_ids)
        if active_model == 'product.template' and active_ids:
            res['product_tmpl_ids'] = [(6, 0, active_ids)]
            res['scope'] = 'selected'
        else:
            res['scope'] = 'all'

        if active_domain:
            res['filter_domain_repr'] = str(active_domain)

        return res

    @api.depends('product_tmpl_ids', 'filter_domain_repr', 'scope')
    def _compute_counts(self):
        for rec in self:
            rec.selected_count = len(rec.product_tmpl_ids)
            total = 0
            if rec.filter_domain_repr:
                try:
                    domain = safe_eval(rec.filter_domain_repr)
                    total = self.env['product.template'].search_count(domain)
                except Exception:
                    total = rec.selected_count
            else:
                total = rec.selected_count
            rec.total_filter_count = total

            if rec.scope == 'all':
                rec.product_count = total
            else:
                rec.product_count = rec.selected_count

    def action_apply(self):
        """Thực hiện cập nhật hàng loạt cho các sản phẩm đã chọn (Dành riêng cho Admin)"""
        self.ensure_one()

        is_admin = self.env.is_admin() or self.env.user.has_group('base.group_system')
        if not is_admin:
            raise UserError(_("Chức năng này chỉ dành riêng cho Quản trị viên hệ thống (Admin)."))

        # Xác định danh sách sản phẩm mục tiêu theo phạm vi được chọn
        if self.scope == 'all' and self.filter_domain_repr:
            try:
                domain = safe_eval(self.filter_domain_repr)
                targets = self.env['product.template'].search(domain)
            except Exception:
                targets = self.product_tmpl_ids.exists()
        else:
            targets = self.product_tmpl_ids.exists()

        if not targets:
            raise UserError(_("Không tìm thấy sản phẩm nào để cập nhật."))

        # Kiểm tra xem người dùng có chọn ít nhất một tiêu chí cập nhật không
        has_change = any([
            self.change_is_storable,
            self.change_available_in_pos,
            self.change_pos_categ,
            self.change_uom,
            self.change_sale_ok,
            self.change_purchase_ok,
        ])
        if not has_change:
            raise UserError(_("Vui lòng chọn ít nhất một thuộc tính cần thay đổi bằng cách tích vào ô tương ứng."))

        # KHÓA AN TOÀN 1: Bắt buộc xác nhận rủi ro khi thay đổi Theo dõi tồn kho hoặc Đơn vị tính
        if (self.change_is_storable or self.change_uom) and not self.confirm_risk:
            raise UserError(_(
                "XÁC NHẬN BẢO VỆ AN TOÀN (BẮT BUỘC):\n\n"
                "Bạn đang thực hiện thay đổi thuộc tính có mức độ rủi ro cao (Theo dõi tồn kho hoặc Đơn vị tính).\n\n"
                "Để đảm bảo an toàn tuyệt đối cho số liệu doanh nghiệp, vui lòng đọc kỹ các cảnh báo nghiệp vụ màu đỏ "
                "và TÍCH CHỌN ô 'XÁC NHẬN RỦI RO & TRÁCH NHIỆM' trước khi bấm áp dụng!"
            ))

        # KHÓA AN TOÀN 2: Chặn tắt theo dõi tồn kho nếu sản phẩm đang có số lượng tồn khác 0
        if self.change_is_storable and not self.is_storable:
            storable_with_qty = targets.filtered(lambda t: t.is_storable and t.qty_available != 0)
            if storable_with_qty:
                first_name = storable_with_qty[0].display_name
                raise UserError(_(
                    "CẢNH BÁO BẢO VỆ TỒN KHO:\n\n"
                    "Có %d sản phẩm đang có số lượng tồn kho khác 0 (Ví dụ: %s với tồn %s).\n\n"
                    "Hệ thống không cho phép tắt 'Theo dõi tồn kho' đối với sản phẩm vẫn còn tồn kho thực tế. "
                    "Vui lòng kiểm kê xuất kho các sản phẩm này về 0 trước khi chuyển thành hàng tiêu dùng/dịch vụ!"
                ) % (len(storable_with_qty), first_name, storable_with_qty[0].qty_available))

        # KHÓA AN TOÀN 3: Chặn đổi ĐVT sai nhóm (category) nếu sản phẩm đã phát sinh phiếu kho
        if self.change_uom:
            if not self.uom_id:
                raise UserError(_("Vui lòng chọn Đơn vị tính mới trước khi áp dụng."))
            incompatible = targets.filtered(lambda t: t.uom_id and t.uom_id.category_id != self.uom_id.category_id)
            if incompatible:
                incompatible_with_moves = []
                for p in incompatible:
                    has_m = self.env['stock.move'].sudo().search_count([
                        ('product_id', 'in', p.with_context(active_test=False).mapped('product_variant_ids').ids)
                    ])
                    if has_m > 0:
                        incompatible_with_moves.append(p)
                if incompatible_with_moves:
                    first_bad = incompatible_with_moves[0]
                    raise UserError(_(
                        "NGHIÊM CẤM ĐỔI ĐƠN VỊ TÍNH SAI NHÓM:\n\n"
                        "Có %d sản phẩm đã phát sinh lịch sử dịch chuyển kho nhưng lại khác nhóm đơn vị tính mới "
                        "(Nhóm hiện tại: '%s' -> Nhóm mới: '%s').\n\n"
                        "Ví dụ: Sản phẩm '%s'.\n\n"
                        "Hệ thống không thể tự quy đổi giữa hai nhóm đơn vị tính khác loại (như Cái sang Kg hoặc Thể tích). "
                        "Vui lòng bỏ chọn các sản phẩm này hoặc chọn đúng đơn vị tính cùng nhóm!"
                    ) % (len(incompatible_with_moves), first_bad.uom_id.category_id.name, self.uom_id.category_id.name, first_bad.display_name))

        vals = {}

        if self.change_available_in_pos:
            vals['available_in_pos'] = self.available_in_pos

        if self.change_pos_categ:
            vals['pos_categ_ids'] = [(6, 0, self.pos_categ_ids.ids)]

        if self.change_sale_ok:
            vals['sale_ok'] = self.sale_ok

        if self.change_purchase_ok:
            vals['purchase_ok'] = self.purchase_ok

        if self.change_is_storable:
            vals['is_storable'] = self.is_storable

        if self.change_uom:
            vals['uom_id'] = self.uom_id.id
            if self.sync_uom_po:
                vals['uom_po_id'] = self.uom_id.id

        total_count = len(targets)
        _logger.warning("[AUDIT TRAIL] Admin %s (UID %s) đang cập nhật hàng loạt cho %d sản phẩm (phạm vi: %s): %s",
                        self.env.user.name, self.env.user.id, total_count, self.scope, vals)

        # Cập nhật thông qua write() đã được override an toàn cho Admin
        targets.write(vals)

        # Ghi vết kiểm toán (Audit Trail) vào Chatter từng sản phẩm
        log_items = []
        if self.change_is_storable:
            st_txt = "BẬT Theo dõi tồn kho (Lưu ý: Tồn kho ban đầu = 0, cần cập nhật số lượng/kiểm kê kho)" if self.is_storable else "TẮT Theo dõi tồn kho"
            log_items.append(f"<li>Theo dõi tồn kho: <b>{st_txt}</b></li>")
        if self.change_available_in_pos:
            pos_txt = "Có bán trên POS" if self.available_in_pos else "Không bán trên POS"
            log_items.append(f"<li>Điểm bán hàng (POS): <b>{pos_txt}</b></li>")
        if self.change_uom:
            log_items.append(f"<li>Đơn vị tính: Đổi sang <b>{self.uom_id.name}</b> (Cần kiểm tra lại bảng giá và kiểm kê lại tồn kho nếu cần)</li>")
        if self.change_sale_ok:
            s_txt = "Cho phép bán" if self.sale_ok else "Ngừng bán"
            log_items.append(f"<li>Trạng thái bán: <b>{s_txt}</b></li>")
        if self.change_purchase_ok:
            p_txt = "Cho phép mua" if self.purchase_ok else "Ngừng mua"
            log_items.append(f"<li>Trạng thái mua: <b>{p_txt}</b></li>")

        if log_items:
            audit_html = f"""
            <div class="alert alert-warning p-2 mb-0" style="font-size: 12px; border-left: 4px solid #ff9800;">
                <strong><i class="fa fa-shield me-1"></i>[KIỂM TOÁN ADMIN] CẬP NHẬT THUỘC TÍNH HÀNG LOẠT:</strong>
                <ul class="mb-1 mt-1 ps-3">{''.join(log_items)}</ul>
                <div class="text-muted small mt-1">Thực hiện bởi Quản trị viên: <b>{self.env.user.name}</b> (UID: {self.env.user.id}) vào lúc {fields.Datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</div>
            </div>
            """
            try:
                if total_count <= 50:
                    for t in targets:
                        t.message_post(body=audit_html, message_type='notification')
                else:
                    note_subtype = self.env.ref('mail.mt_note', raise_if_not_found=False)
                    subtype_id = note_subtype.id if note_subtype else False
                    mail_vals = [{
                        'model': 'product.template',
                        'res_id': t_id,
                        'body': audit_html,
                        'message_type': 'notification',
                        'subtype_id': subtype_id,
                        'author_id': self.env.user.partner_id.id,
                    } for t_id in targets.ids]
                    self.env['mail.message'].sudo().create(mail_vals)
            except Exception as e:
                _logger.warning("Không thể ghi log chatter tự động: %s", e)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Cập nhật thành công!"),
                "message": _("Đã cập nhật thuộc tính an toàn cho %d sản phẩm.") % total_count,
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            }
        }
