# -*- coding: utf-8 -*-
import re
from odoo import models, fields, api, _
from odoo.exceptions import AccessError, ValidationError


class QbaLcSpecParser(models.AbstractModel):
    _name = "qba.lc.spec.parser"
    _description = "Bộ Phân Tích Thông Số Kỹ Thuật Tên Sản Phẩm LC (Lá Côn)"

    # Regex patterns định danh chặt chẽ các thông số kỹ thuật LC
    RE_OUTER_DIAMETER = re.compile(
        r"(?:(?:phi|ø|\bđk\b|\bđường\s+kính(?:\s+ngoài)?\b)\s*[:=]?\s*(\d+(?:[.,]\d+)?)|(\d+(?:[.,]\d+)?)\s*mm)\b",
        re.IGNORECASE
    )
    RE_SPLINE_TEETH = re.compile(
        r"(?:^|[\s\-/])(\d+)\s*[rR]\b|(?:^|[\s\-/])(\d+)\s*răng\b|(?:răng|rang|teeth)\s*[:=]?\s*(\d+)",
        re.IGNORECASE
    )
    RE_HUB_CD = re.compile(r"(?:^|[\s\-])(\d+(?:[.,]\d+)?)\s*[/|]\s*(\d+(?:[.,]\d+)?)(?:[\s\-]|$|\b)")
    RE_SPRING_COUNT = re.compile(r"(?:^|[\s\-(/])(\d+)\s*lò\s*xo\b", re.IGNORECASE)

    @api.model
    def parse_lc_name(self, name):
        """Trích xuất các ứng viên thông số kỹ thuật từ chuỗi tên sản phẩm LC."""
        if not name:
            return {}

        results = {}

        # 1. Đường kính ngoài (Outer Diameter)
        m_outer = self.RE_OUTER_DIAMETER.search(name)
        if m_outer:
            try:
                num_str = m_outer.group(1) or m_outer.group(2)
                num = float(num_str.replace(",", "."))
                results["duong_kinh_ngoai"] = {
                    "value": num,
                    "value_display": f"{num:g}",
                    "token": m_outer.group(0).strip(),
                }
            except (ValueError, TypeError):
                pass

        # 2. Số răng moay ơ (Spline Teeth)
        m_teeth = self.RE_SPLINE_TEETH.search(name)
        if m_teeth:
            teeth_val = m_teeth.group(1) or m_teeth.group(2) or m_teeth.group(3)
            try:
                num = int(teeth_val)
                results["rang"] = {
                    "value": num,
                    "value_display": str(num),
                    "token": m_teeth.group(0).strip(),
                }
            except (ValueError, TypeError):
                pass

        # 3. Kích thước moay ơ C & D (Hub Measurements C & D)
        m_hub = self.RE_HUB_CD.search(name)
        if m_hub:
            c_str, d_str = m_hub.group(1), m_hub.group(2)
            try:
                c_val = float(c_str.replace(",", "."))
                d_val = float(d_str.replace(",", "."))
                token_str = m_hub.group(0).strip()
                results["duong_kinh_moay_o_c"] = {
                    "value": c_val,
                    "value_display": f"{c_val:g}",
                    "token": token_str,
                }
                results["duong_kinh_moay_o_d"] = {
                    "value": d_val,
                    "value_display": f"{d_val:g}",
                    "token": token_str,
                }
            except (ValueError, TypeError):
                pass

        # 4. Số lò xo (Spring Count)
        m_spring = self.RE_SPRING_COUNT.search(name)
        if m_spring:
            try:
                num = int(m_spring.group(1))
                results["lo_xo"] = {
                    "value": num,
                    "value_display": str(num),
                    "token": m_spring.group(0).strip(),
                }
            except (ValueError, TypeError):
                pass

        return results

    # Alias phương thức chung cho Spec Parser Registry
    parse_product_name = parse_lc_name

    @api.model
    def _get_lc_spec_definitions(self, category_id=None):
        """Lấy 5 định nghĩa thông số kỹ thuật chuẩn của danh mục LC (CHỈ ĐỌC - không tự tạo, không tự bật active).
        Nếu thiếu định nghĩa hoặc đang bị vô hiệu hóa, thông báo lỗi cấu hình.
        """
        required_defs = [
            ("duong_kinh_ngoai", "Đường kính ngoài"),
            ("rang", "Số răng"),
            ("duong_kinh_moay_o_c", "Đường kính moay ơ C"),
            ("duong_kinh_moay_o_d", "Đường kính moay ơ D"),
            ("lo_xo", "Số lò xo"),
        ]
        required_codes = [code for code, _ in required_defs]
        spec_def_env = self.env["qba.product.spec.definition"]

        # Tìm các định nghĩa đang active=True
        active_defs = spec_def_env.search([("code", "in", required_codes)])
        defs_by_code = {d.code: d for d in active_defs}

        missing_codes = [code for code in required_codes if code not in defs_by_code]
        if missing_codes:
            # Kiểm tra xem có định nghĩa nào đang bị inactive (active=False) không
            inactive_defs = spec_def_env.with_context(active_test=False).search([("code", "in", missing_codes)])
            inactive_codes = inactive_defs.mapped("code")
            truly_missing = [c for c in missing_codes if c not in inactive_codes]

            err_parts = []
            if inactive_codes:
                err_parts.append(_(
                    "Các thông số kỹ thuật chuẩn sau đang bị vô hiệu hóa (active = False): %(codes)s.\n"
                    "Vui lòng vào 'Cấu hình thông số kỹ thuật' để bật lại hiệu lực trước khi thực hiện phân tích."
                ) % {"codes": ", ".join(inactive_codes)})
            if truly_missing:
                err_parts.append(_(
                    "Thiếu cấu hình định nghĩa thông số kỹ thuật chuẩn: %(codes)s.\n"
                    "Vui lòng tạo các định nghĩa thông số này trước khi thực hiện phân tích."
                ) % {"codes": ", ".join(truly_missing)})

            raise ValidationError("\n\n".join(err_parts))

        return defs_by_code

    @api.model
    def _ensure_lc_spec_definitions(self, category_id=None):
        """Hàm trợ giúp thiết lập định nghĩa LC chuẩn (chỉ dùng cho setup/migration, KHÔNG dùng trong Preview)."""
        if not (self.env.user.has_group("qba_ai.group_qba_ai_manager") or self.env.user.has_group("base.group_system")):
            raise AccessError(_("Chỉ Quản trị viên QBA AI mới có quyền khởi tạo/đồng bộ định nghĩa thông số."))
        categ_lc = self.env["product.category"].browse(category_id) if category_id else self.env["product.category"].search([("name", "ilike", "LC")], limit=1)
        categ_ids = [(6, 0, [categ_lc.id])] if categ_lc else []

        spec_def_env = self.env["qba.product.spec.definition"]
        required_defs = [
            ("duong_kinh_ngoai", "Đường kính ngoài", "float", "mm", "A: Đo Ø ngoài lá côn"),
            ("rang", "răng", "integer", "cái", "B: số nia (răng)"),
            ("duong_kinh_moay_o_c", "Đường kính moay ơ C", "float", "mm", "C: Đo Ø trong, dưới nia lá côn"),
            ("duong_kinh_moay_o_d", "Đường kính moay ơ D", "float", "mm", "D: Đo vòng sắt giữa lá côn"),
            ("lo_xo", "lò xo", "integer", "cái", "Số lò xo giảm chấn"),
        ]

        defs_by_code = {}
        for code, name, data_type, uom, desc in required_defs:
            d = spec_def_env.with_context(active_test=False).search([("code", "=", code)], limit=1)
            if not d:
                d = spec_def_env.create({
                    "name": name,
                    "code": code,
                    "data_type": data_type,
                    "uom": uom,
                    "description": desc,
                    "category_ids": categ_ids,
                    "active": True,
                })
            else:
                # Đồng bộ kiểu dữ liệu và danh mục nếu chưa chuẩn
                vals = {}
                if d.data_type != data_type:
                    vals["data_type"] = data_type
                if categ_lc and categ_lc.id not in d.category_ids.ids:
                    vals["category_ids"] = [(4, categ_lc.id)]
                if not d.active:
                    vals["active"] = True
                if vals:
                    d.write(vals)
            defs_by_code[code] = d

        return defs_by_code

    # =========================================================================
    # TIỆN ÍCH BẢO TRÌ & CHUẨN HÓA THÔNG SỐ ĐƯỜNG KÍNH MOAY Ơ LC (HUB C & D SPLIT)
    # =========================================================================

    @api.model
    def preview_hub_diameter_split(self, category_id=None):
        """Xem trước việc tách thông số 'đường kính moay ơ' dạng 31|38 hoặc 31/38.5 thành C và D.
        Trả về kết quả phân tích:
        - ready: các bản ghi có định dạng chuẩn (ví dụ: 31|38, 31/38.5) có thể tách đề xuất
        - manual_review_required: các bản ghi mơ hồ, thiếu số hoặc không hợp lệ cần kiểm tra thủ công.
        """
        domain = [("spec_definition_id.code", "=", "duong_kinh_moay_o")]
        if category_id:
            domain.append(("product_tmpl_id.categ_id", "child_of", category_id))

        spec_values = self.env["qba.product.spec.value"].search(domain)
        pattern = re.compile(r"^(\d+(?:[.,]\d+)?)\s*[/|\-xX]\s*(\d+(?:[.,]\d+)?)$")

        preview_list = []
        for val in spec_values:
            text = (val.value_char or val.value_display or "").strip()
            match = pattern.match(text)
            if match:
                c_str, d_str = match.groups()
                try:
                    c_float = float(c_str.replace(",", "."))
                    d_float = float(d_str.replace(",", "."))
                    preview_list.append({
                        "product_id": val.product_tmpl_id.id,
                        "product_name": val.product_tmpl_id.display_name,
                        "original_val_id": val.id,
                        "original_text": text,
                        "c_value": c_float,
                        "d_value": d_float,
                        "status": "ready",
                        "proposed_validation_status": "unverified",
                    })
                except ValueError:
                    preview_list.append({
                        "product_id": val.product_tmpl_id.id,
                        "product_name": val.product_tmpl_id.display_name,
                        "original_val_id": val.id,
                        "original_text": text,
                        "status": "manual_review_required",
                        "reason": _("Không thể chuyển đổi chuỗi số sang số thực"),
                    })
            else:
                preview_list.append({
                    "product_id": val.product_tmpl_id.id,
                    "product_name": val.product_tmpl_id.display_name,
                    "original_val_id": val.id,
                    "original_text": text,
                    "status": "manual_review_required",
                    "reason": _("Định dạng không khớp cú pháp hai số (ví dụ: 31|38 hoặc 31/38.5)"),
                })
        return preview_list

    @api.model
    def action_apply_hub_diameter_split(self, category_id=None):
        """Thực hiện tách thông số 'đường kính moay ơ' thành 'Đường kính moay ơ C' và 'Đường kính moay ơ D'
        - Giữ nguyên định nghĩa và các bản ghi giá trị gốc 31|38.
        - Tạo bản ghi mới cho C và D ở trạng thái 'unverified' (chưa duyệt) để Admin kiểm duyệt.
        - Ghi chú rõ nguồn gốc chuyển đổi.
        """
        if not self.env.user.has_group("qba_ai.group_qba_ai_manager"):
            raise AccessError(_("Chỉ Quản trị viên QBA AI mới có quyền thực hiện chuyển đổi thông số."))

        categ_lc = self.env["product.category"].browse(category_id) if category_id else self.env["product.category"].search([("name", "ilike", "LC")], limit=1)
        categ_ids = [(6, 0, [categ_lc.id])] if categ_lc else []

        spec_def_env = self.env["qba.product.spec.definition"]

        def_c = spec_def_env.search([("code", "=", "duong_kinh_moay_o_c")], limit=1)
        if not def_c:
            def_c = spec_def_env.create({
                "name": "Đường kính moay ơ C",
                "code": "duong_kinh_moay_o_c",
                "data_type": "float",
                "uom": "mm",
                "description": "C: Đo Ø trong, dưới nia lá côn",
                "category_ids": categ_ids,
            })
        elif categ_lc and categ_lc.id not in def_c.category_ids.ids:
            def_c.category_ids = [(4, categ_lc.id)]

        def_d = spec_def_env.search([("code", "=", "duong_kinh_moay_o_d")], limit=1)
        if not def_d:
            def_d = spec_def_env.create({
                "name": "Đường kính moay ơ D",
                "code": "duong_kinh_moay_o_d",
                "data_type": "float",
                "uom": "mm",
                "description": "D: Đo vòng sắt giữa lá côn",
                "category_ids": categ_ids,
            })
        elif categ_lc and categ_lc.id not in def_d.category_ids.ids:
            def_d.category_ids = [(4, categ_lc.id)]

        preview_data = self.preview_hub_diameter_split(category_id=categ_lc.id if categ_lc else None)
        migrated_count = 0
        manual_review_count = 0

        for item in preview_data:
            if item.get("status") != "ready":
                manual_review_count += 1
                continue
            prod_id = item["product_id"]
            orig_text = item["original_text"]
            c_val = item["c_value"]
            d_val = item["d_value"]
            note = _("Đề xuất tách từ thông số cũ 'đường kính moay ơ': %s") % orig_text

            val_c = self.env["qba.product.spec.value"].search([
                ("product_tmpl_id", "=", prod_id),
                ("spec_definition_id", "=", def_c.id),
            ], limit=1)
            if not val_c:
                self.env["qba.product.spec.value"].create({
                    "product_tmpl_id": prod_id,
                    "spec_definition_id": def_c.id,
                    "value_display": f"{c_val:g}",
                    "validation_status": "unverified",
                    "source": "manual_entry",
                    "notes": note,
                })

            val_d = self.env["qba.product.spec.value"].search([
                ("product_tmpl_id", "=", prod_id),
                ("spec_definition_id", "=", def_d.id),
            ], limit=1)
            if not val_d:
                self.env["qba.product.spec.value"].create({
                    "product_tmpl_id": prod_id,
                    "spec_definition_id": def_d.id,
                    "value_display": f"{d_val:g}",
                    "validation_status": "unverified",
                    "source": "manual_entry",
                    "notes": note,
                })
            migrated_count += 1

        msg = _("Đã tạo đề xuất tách C & D cho %d sản phẩm (ở trạng thái Chưa duyệt để Admin kiểm tra). "
                "Có %d sản phẩm cần kiểm tra thủ công.") % (migrated_count, manual_review_count)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Chuẩn hóa thông số Moay ơ hoàn tất!"),
                "message": msg,
                "type": "success",
                "sticky": True,
            },
        }

    @api.model
    def action_rollback_hub_diameter_split(self, category_id=None):
        """Khôi phục: Xóa các bản ghi C và D chưa duyệt đã tạo tự động mà không làm ảnh hưởng thông số gốc"""
        if not self.env.user.has_group("qba_ai.group_qba_ai_manager"):
            raise AccessError(_("Chỉ Quản trị viên QBA AI mới có quyền thực hiện khôi phục."))
        spec_def_env = self.env["qba.product.spec.definition"]
        def_c = spec_def_env.search([("code", "=", "duong_kinh_moay_o_c")], limit=1)
        def_d = spec_def_env.search([("code", "=", "duong_kinh_moay_o_d")], limit=1)
        def_ids = [d.id for d in (def_c | def_d) if d]
        if not def_ids:
            return 0
        domain = [
            ("spec_definition_id", "in", def_ids),
            ("validation_status", "=", "unverified"),
        ]
        if category_id:
            domain.append(("product_tmpl_id.categ_id", "child_of", category_id))
        vals = self.env["qba.product.spec.value"].search(domain)
        count = len(vals)
        vals.unlink()
        return count

    # =========================================================================
    # GIAO DIỆN ĐĂNG KÝ VỚI PARSER REGISTRY / DISPATCHER
    # =========================================================================

    @api.model
    def is_category_supported(self, category):
        """Xác định danh mục có thuộc phạm vi phân tích của bộ Parser Lá Côn hay không.
        Chỉ chấp nhận danh mục Lá côn (LC) hoặc danh mục con của nó.
        """
        if not category:
            return False

        # Kiểm tra theo quy ước định danh danh mục (tên / mã LC trong chuỗi cha con)
        categ_hierarchy = category
        curr = category
        while curr.parent_id:
            curr = curr.parent_id
            categ_hierarchy |= curr

        for cat in categ_hierarchy:
            cat_name = (cat.name or "").upper()
            if "LC" in cat_name or "LÁ CÔN" in cat_name or "LA CON" in cat_name:
                return True
        return False

    @api.model
    def open_product_wizard(self, product):
        """Mở wizard trích xuất thông số cho một sản phẩm Lá Côn cụ thể."""
        wizard = self.env["qba.lc.spec.parser.wizard"].create({
            "product_ids": [(6, 0, product.ids)],
            "category_id": product.categ_id.id if product.categ_id else False,
        })
        wizard.action_parse_preview()
        return {
            "name": _("Xem trước trích xuất thông số: %s") % (product.default_code or product.name),
            "type": "ir.actions.act_window",
            "res_model": "qba.lc.spec.parser.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_category_id": product.categ_id.id if product.categ_id else False,
                "default_product_ids": product.ids,
            },
        }

    @api.model
    def open_category_wizard(self, category):
        """Mở wizard trích xuất thông số cho toàn bộ sản phẩm thuộc danh mục Lá Côn."""
        products = self.env["product.template"].search([("categ_id", "child_of", category.id)])
        wizard = self.env["qba.lc.spec.parser.wizard"].create({
            "category_id": category.id,
            "product_ids": [(6, 0, products.ids)],
        })
        wizard.action_parse_preview()
        return {
            "name": _("Xem trước trích xuất thông số danh mục: %s") % category.display_name,
            "type": "ir.actions.act_window",
            "res_model": "qba.lc.spec.parser.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_category_id": category.id,
                "default_product_ids": products.ids,
            },
        }


class QbaLcSpecParserWizard(models.TransientModel):
    _name = "qba.lc.spec.parser.wizard"
    _description = "Wizard Xem Trước & Áp Dụng Trích Xuất Thông Số LC (Parser)"

    category_id = fields.Many2one(
        "product.category",
        string="Danh mục lọc",
        default=lambda self: self.env["product.category"].search([("name", "ilike", "LC")], limit=1)
    )
    product_ids = fields.Many2many(
        "product.template",
        string="Sản phẩm áp dụng",
        help="Để trống để tự động quét toàn bộ sản phẩm thuộc danh mục LC."
    )
    line_ids = fields.One2many(
        "qba.lc.spec.parser.wizard.line",
        "wizard_id",
        string="Chi tiết đề xuất thông số"
    )

    total_products = fields.Integer(string="Số sản phẩm", compute="_compute_stats")
    total_proposals = fields.Integer(string="Tổng số thông số", compute="_compute_stats")
    total_draft_ready = fields.Integer(string="Sẵn sàng tạo nháp", compute="_compute_stats")
    total_conflicts = fields.Integer(string="Xung đột / Cần xem xét", compute="_compute_stats")
    total_skipped = fields.Integer(string="Bỏ qua / Đã có", compute="_compute_stats")
    total_missing = fields.Integer(string="Thiếu trong tên", compute="_compute_stats")

    @api.depends("line_ids", "line_ids.proposed_action", "line_ids.parsing_status")
    def _compute_stats(self):
        for rec in self:
            rec.total_products = len(rec.line_ids.mapped("product_tmpl_id"))
            rec.total_proposals = len(rec.line_ids)
            rec.total_draft_ready = len(rec.line_ids.filtered(lambda l: l.proposed_action == "create_draft"))
            rec.total_conflicts = len(rec.line_ids.filtered(lambda l: l.parsing_status == "conflict" or l.proposed_action == "manual_review"))
            rec.total_skipped = len(rec.line_ids.filtered(lambda l: l.proposed_action == "skip"))
            rec.total_missing = len(rec.line_ids.filtered(lambda l: l.parsing_status == "missing"))

    def action_parse_preview(self):
        """Thực hiện quét phân tích tên sản phẩm và tạo bảng xem trước (preview) KHÔNG làm thay đổi DB persistent."""
        self.ensure_one()

        if not self.env.user.has_group("qba_ai.group_qba_ai_manager"):
            raise AccessError(_("Chỉ Quản trị viên QBA AI (AI Manager) mới có quyền thực hiện xem trước (Preview) trích xuất thông số kỹ thuật."))

        # 1. Đảm bảo các định nghĩa thông số LC chuẩn đã tồn tại (CHỈ ĐỌC: không tự bật active, không tự tạo)
        defs_by_code = self.env["qba.lc.spec.parser"]._get_lc_spec_definitions(self.category_id.id if self.category_id else None)

        # 2. Xác định danh sách sản phẩm cần phân tích
        if self.product_ids:
            products = self.product_ids
        elif self.category_id:
            products = self.env["product.template"].search([("categ_id", "child_of", self.category_id.id)], order="default_code, id")
        else:
            categ_lc = self.env["product.category"].search([("name", "ilike", "LC")], limit=1)
            products = self.env["product.template"].search([("categ_id", "child_of", categ_lc.id)], order="default_code, id") if categ_lc else self.env["product.template"]

        # Xóa các dòng preview cũ nếu có (trên TransientModel wizard line)
        self.line_ids.unlink()

        ordered_spec_codes = [
            ("duong_kinh_ngoai", "Đường kính ngoài"),
            ("rang", "Số răng"),
            ("duong_kinh_moay_o_c", "Đường kính moay ơ C"),
            ("duong_kinh_moay_o_d", "Đường kính moay ơ D"),
            ("lo_xo", "Số lò xo"),
        ]

        lines_to_create = []

        for prod in products:
            parsed_data = self.env["qba.lc.spec.parser"].parse_lc_name(prod.name)

            # Kiểm tra xem sản phẩm có thông số moay ơ cũ (duong_kinh_moay_o) đã xác thực hay không
            # (tìm cả trong trường hợp định nghĩa đang active hay inactive)
            old_hub_spec = prod.spec_value_ids.filtered(
                lambda v: v.spec_definition_id.code == "duong_kinh_moay_o" and v.validation_status == "verified"
            )
            old_hub_val = old_hub_spec.value_display if old_hub_spec else False

            # Quy tắc phát hiện bất thường dữ liệu (Data Anomaly Detection):
            # Tiêu chí:
            # 1. Sản phẩm có ghi chú kỹ thuật / nội bộ chỉ định bất thường (từ khóa [ANOMALY], 'bất thường', 'chưa rõ lịch sử')
            # 2. Hoặc mã SKU 'LC.007' chưa có thông số moay ơ cũ 20mm trong DB (fallback an toàn Phase 3.2 trong thời gian chuyển tiếp)
            notes_text = f"{prod.internal_notes or ''} {prod.technical_specs or ''}".lower()
            is_anomaly = (
                "[anomaly]" in notes_text
                or "bất thường" in notes_text
                or "chưa rõ lịch sử" in notes_text
                or (prod.default_code == "LC.007" and not old_hub_val)
            )

            for spec_code, spec_label in ordered_spec_codes:
                spec_def = defs_by_code.get(spec_code)
                if not spec_def:
                    continue

                existing_val_rec = prod.spec_value_ids.filtered(lambda v: v.spec_definition_id.id == spec_def.id)
                existing_val = existing_val_rec.value_display if existing_val_rec else False
                existing_status = existing_val_rec.validation_status if existing_val_rec else False

                proposal = parsed_data.get(spec_code)
                proposed_val = proposal["value_display"] if proposal else False
                source_token = proposal["token"] if proposal else False

                # Đánh giá trạng thái và hành động đề xuất
                parsing_status = "confident"
                proposed_action = "create_draft"
                notes = ""

                # 1. Phát hiện bất thường dữ liệu lịch sử moay ơ: PHẢI yêu cầu xác minh thủ công
                if spec_code in ("duong_kinh_moay_o_c", "duong_kinh_moay_o_d") and is_anomaly:
                    parsing_status = "conflict"
                    proposed_action = "manual_review"
                    if "[anomaly]" in notes_text or "bất thường" in notes_text:
                        anomaly_msg = prod.internal_notes or _("Sản phẩm có ghi nhận bất thường dữ liệu lịch sử cần thẩm định thủ công.")
                    elif prod.default_code == "LC.007":
                        anomaly_msg = _("Sản phẩm LC.007 có ghi nhận lịch sử moay ơ cũ (20mm) nhưng chưa được khôi phục trong DB.")
                    else:
                        anomaly_msg = _("Sản phẩm có ghi nhận bất thường dữ liệu lịch sử cần thẩm định thủ công.")

                    notes = _(
                        "Cảnh báo: %s "
                        "Không tự động chấp nhận đề xuất C/D ('%s'). Cần Quản trị viên AI xác minh thủ công."
                    ) % (anomaly_msg, proposed_val or source_token or "")

                # 2. Kiểm tra xung đột với thông số moay ơ cũ đã xác thực (nếu có trong DB)
                elif spec_code in ("duong_kinh_moay_o_c", "duong_kinh_moay_o_d") and old_hub_val:
                    is_compatible = False
                    if proposal:
                        hub_c_prop = parsed_data.get("duong_kinh_moay_o_c", {}).get("value_display")
                        hub_d_prop = parsed_data.get("duong_kinh_moay_o_d", {}).get("value_display")
                        compatible_strings = [
                            f"{hub_c_prop}|{hub_d_prop}",
                            f"{hub_c_prop}/{hub_d_prop}",
                            hub_c_prop,
                            hub_d_prop,
                        ]
                        if old_hub_val in compatible_strings:
                            is_compatible = True

                    if not is_compatible:
                        parsing_status = "conflict"
                        proposed_action = "manual_review"
                        notes = _("Xung đột: Sản phẩm đã có giá trị moay ơ đã duyệt '%s', khác với giá trị trích xuất từ tên ('%s'). Không thể tự động ghi đè.") % (old_hub_val, source_token or "")

                if not notes:
                    if not proposed_val:
                        # Không tìm thấy thông số trong tên
                        parsing_status = "missing"
                        proposed_action = "skip"
                        notes = _("Không tìm thấy thông số '%s' trong tên sản phẩm (để trống khi không có).") % spec_label
                    elif existing_status == "verified":
                        # Giá trị đã được Admin duyệt chính thức trong hệ thống
                        is_match = False
                        try:
                            if spec_def.data_type in ("float", "integer"):
                                is_match = (float(existing_val) == float(proposed_val))
                            else:
                                is_match = (str(existing_val).strip() == str(proposed_val).strip())
                        except (ValueError, TypeError):
                            is_match = (str(existing_val).strip() == str(proposed_val).strip())

                        if is_match:
                            parsing_status = "match"
                            proposed_action = "skip"
                            notes = _("Đã tồn tại giá trị '%s' đã xác thực chính thức (trùng khớp đề xuất).") % existing_val
                        else:
                            parsing_status = "conflict"
                            proposed_action = "manual_review"
                            notes = _("Xung đột: Giá trị trong hệ thống đã duyệt là '%s', khác với đề xuất '%s'. Cần Admin kiểm tra thủ công.") % (existing_val, proposed_val)
                    elif existing_status == "unverified":
                        # Đã có bản nháp
                        is_match = False
                        try:
                            if spec_def.data_type in ("float", "integer"):
                                is_match = (float(existing_val) == float(proposed_val))
                            else:
                                is_match = (str(existing_val).strip() == str(proposed_val).strip())
                        except (ValueError, TypeError):
                            is_match = (str(existing_val).strip() == str(proposed_val).strip())

                        if is_match:
                            parsing_status = "match"
                            proposed_action = "skip"
                            notes = _("Đã có bản nháp với giá trị '%s' (trùng khớp đề xuất).") % existing_val
                        else:
                            parsing_status = "ambiguous"
                            proposed_action = "manual_review"
                            notes = _("Đã có bản nháp '%s' khác với giá trị đề xuất '%s'. Cần Admin xem xét.") % (existing_val, proposed_val)
                    else:
                        # Chưa có giá trị trong hệ thống -> Sẵn sàng tạo bản nháp
                        parsing_status = "confident"
                        proposed_action = "create_draft"
                        notes = _("Trích xuất tự động từ mẫu cú pháp: '%s'") % source_token

                # QUY TẮC BẢO VỆ: Chỉ tự động chọn khi đủ điều kiện:
                # - Hành động là create_draft
                # - Trạng thái phân tích là confident
                # - Có giá trị đề xuất
                # - Định nghĩa thông số hợp lệ và đang active
                is_auto_selected = (
                    proposed_action == "create_draft"
                    and parsing_status == "confident"
                    and bool(proposed_val)
                    and bool(spec_def and spec_def.active)
                )

                lines_to_create.append({
                    "wizard_id": self.id,
                    "product_tmpl_id": prod.id,
                    "spec_definition_id": spec_def.id,
                    "proposed_value": proposed_val or "",
                    "source_pattern": source_token or "",
                    "existing_value": existing_val or "",
                    "existing_status": existing_status or "",
                    "parsing_status": parsing_status,
                    "proposed_action": proposed_action,
                    "notes": notes,
                    "selected": is_auto_selected,
                })

        if lines_to_create:
            self.env["qba.lc.spec.parser.wizard.line"].create(lines_to_create)

        return {
            "name": _("Xem Trước Trích Xuất Thông Số LC (Parser Preview)"),
            "type": "ir.actions.act_window",
            "res_model": "qba.lc.spec.parser.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_apply_proposals(self):
        """Áp dụng các đề xuất hợp lệ:
        - Chỉ Quản trị viên QBA AI mới có quyền thực thi.
        - Tạo các thông số mới ở trạng thái 'unverified' (Chưa kiểm duyệt).
        - Tuyệt đối KHÔNG tự động duyệt 'verified'.
        - Tuyệt đối KHÔNG ghi đè giá trị 'verified' sẵn có.
        - Server-side validation: Chặn mọi dòng conflict, manual_review, missing, ambiguous kể cả khi client gửi selected=True.
        - Chặn mọi định nghĩa spec không active hoặc không tồn tại.
        - Idempotent: chạy nhiều lần không tạo bản ghi trùng lặp.
        - Tuyệt đối KHÔNG làm thay đổi bất kỳ trường nghiệp vụ nào của sản phẩm (tên, default_code, giá, kho...).
        """
        if not self.env.user.has_group("qba_ai.group_qba_ai_manager"):
            raise AccessError(_("Chỉ Quản trị viên QBA AI (AI Manager) mới có quyền áp dụng các đề xuất trích xuất thông số kỹ thuật."))

        created_count = 0
        skipped_count = 0
        conflict_count = 0
        rejected_security_count = 0

        spec_val_env = self.env["qba.product.spec.value"]

        # Lọc các dòng được client đánh dấu selected
        selected_lines = self.line_ids.filtered(lambda l: l.selected)

        for line in selected_lines:
            # SERVER-SIDE DEFENSE:
            # 1. Từ chối ngay nếu dòng có trạng thái conflict, manual_review, missing hoặc ambiguous
            if line.parsing_status in ("conflict", "manual_review", "missing", "ambiguous") or line.proposed_action != "create_draft":
                rejected_security_count += 1
                continue

            # 2. Từ chối nếu giá trị đề xuất rỗng
            if not line.proposed_value:
                continue

            # 3. Từ chối nếu định nghĩa thông số không hợp lệ hoặc không active
            spec_def = line.spec_definition_id
            if not spec_def or not spec_def.exists() or not spec_def.active:
                rejected_security_count += 1
                continue

            prod = line.product_tmpl_id
            if not prod or not prod.exists():
                continue

            # 4. Kiểm tra an toàn trong DB: Nếu đã có bản ghi thì không tạo trùng
            existing_val = spec_val_env.search([
                ("product_tmpl_id", "=", prod.id),
                ("spec_definition_id", "=", spec_def.id),
            ], limit=1)

            if existing_val:
                if existing_val.validation_status == "verified":
                    # Tuyệt đối không bao giờ ghi đè bản ghi đã xác thực
                    conflict_count += 1
                    continue
                elif existing_val.value_display == line.proposed_value:
                    skipped_count += 1
                    continue
                else:
                    # Cập nhật bản nháp unverified
                    existing_val.write({
                        "value_display": line.proposed_value,
                        "source": "parsed_from_name",
                        "notes": _("Cập nhật từ trích xuất tên sản phẩm: '%s'") % line.source_pattern,
                    })
                    created_count += 1
            else:
                # Tạo bản ghi mới ở trạng thái unverified
                spec_val_env.create({
                    "product_tmpl_id": prod.id,
                    "spec_definition_id": spec_def.id,
                    "value_display": line.proposed_value,
                    "validation_status": "unverified",
                    "source": "parsed_from_name",
                    "notes": _("Trích xuất tự động từ tên sản phẩm: '%s'") % line.source_pattern,
                })
                created_count += 1

        msg = _("Đã áp dụng thành công %d thông số kỹ thuật (dưới dạng bản nháp 'Chưa kiểm duyệt' để Admin duyệt). "
                "Bỏ qua %d thông số đã có. Không ghi đè %d thông số đã xác thực.") % (created_count, skipped_count, conflict_count)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Áp dụng thông số thành công!"),
                "message": msg,
                "type": "success",
                "sticky": True,
                "next": {
                    "type": "ir.actions.client",
                    "tag": "reload",
                },
            },
        }


class QbaLcSpecParserWizardLine(models.TransientModel):
    _name = "qba.lc.spec.parser.wizard.line"
    _description = "Dòng Đề Xuất Thông Số Kỹ Thuật LC (Parser Line)"
    _order = "product_code, id"

    wizard_id = fields.Many2one("qba.lc.spec.parser.wizard", string="Wizard", ondelete="cascade", required=True)
    product_tmpl_id = fields.Many2one("product.template", string="Sản phẩm", required=True)
    product_code = fields.Char(related="product_tmpl_id.default_code", string="Mã sản phẩm")
    product_name = fields.Char(related="product_tmpl_id.name", string="Tên sản phẩm")

    spec_definition_id = fields.Many2one("qba.product.spec.definition", string="Thông số", required=True)
    spec_code = fields.Char(related="spec_definition_id.code", string="Mã thông số")
    uom = fields.Char(related="spec_definition_id.uom", string="Đơn vị")

    proposed_value = fields.Char(string="Giá trị đề xuất")
    source_pattern = fields.Char(string="Cú pháp nguồn", help="Mẫu ký tự trong tên sản phẩm được trích xuất (ví dụ: phi 325, 10R, 31/38)")

    existing_value = fields.Char(string="Giá trị hiện tại trong DB")
    existing_status = fields.Char(string="Trạng thái hiện tại")

    parsing_status = fields.Selection([
        ("confident", "Hợp lệ / Tự tin"),
        ("match", "Khớp giá trị hiện có"),
        ("conflict", "Xung đột với dữ liệu đã duyệt"),
        ("missing", "Thiếu trong tên"),
        ("ambiguous", "Mơ hồ / Cần xem xét"),
    ], string="Trạng thái trích xuất", default="confident")

    proposed_action = fields.Selection([
        ("create_draft", "Tạo bản nháp (unverified)"),
        ("skip", "Bỏ qua (Đã có / Khớp)"),
        ("manual_review", "Kiểm tra thủ công"),
    ], string="Hành động đề xuất", default="create_draft")

    notes = fields.Text(string="Ghi chú / Giải thích")
    selected = fields.Boolean(string="Chọn áp dụng", default=False)

