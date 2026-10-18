# -*- coding: utf-8 -*-
import re
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, AccessError


class QbaProductSpecDefinition(models.Model):
    _name = "qba.product.spec.definition"
    _description = "Định Nghĩa Thông Số Kỹ Thuật"
    _order = "sequence, id"

    name = fields.Char(
        string="Tên thông số",
        required=True,
        translate=True,
        index=True,
        help="Tên hiển thị của thông số kỹ thuật (ví dụ: Đường kính ngoài, Số răng moay ơ, Chiều cao tổng...)"
    )
    code = fields.Char(
        string="Mã kỹ thuật (Code)",
        required=True,
        index=True,
        copy=False,
        help="Mã định danh kỹ thuật không đổi (ổn định) dùng cho logic hệ thống. Ví dụ: outer_diameter, spline_teeth..."
    )
    category_ids = fields.Many2many(
        "product.category",
        "qba_spec_def_category_rel",
        "spec_def_id",
        "category_id",
        string="Danh mục áp dụng",
        help="Các danh mục sản phẩm áp dụng thông số này (tự động áp dụng cho cả các danh mục con). "
             "Nếu để trống, thông số được áp dụng chung cho mọi danh mục."
    )
    data_type = fields.Selection([
        ("char", "Chuỗi / Văn bản (Text)"),
        ("integer", "Số nguyên (Integer)"),
        ("float", "Số thực / Thập phân (Float)"),
        ("boolean", "Đúng / Sai (Boolean)"),
        ("selection", "Danh sách lựa chọn (Selection)"),
    ], string="Kiểu dữ liệu", required=True, default="char",
       help="Kiểu dữ liệu quy chuẩn cho thông số này để đảm bảo tính toàn vẹn khi nhập liệu và tìm kiếm.")

    selection_options = fields.Text(
        string="Các lựa chọn (Selection Options)",
        help="Chỉ áp dụng khi kiểu dữ liệu là Selection. Nhập các lựa chọn được phép, mỗi lựa chọn trên 1 dòng hoặc cách nhau bởi dấu phẩy."
    )
    uom = fields.Char(
        string="Đơn vị tính",
        help="Đơn vị đo lường (ví dụ: mm, cm, inch, răng, lỗ, cái... hoặc để trống nếu không có đơn vị)."
    )
    description = fields.Text(
        string="Mô tả / Hướng dẫn đo",
        help="Ghi chú giải thích chi tiết ý nghĩa thông số hoặc vị trí cần đo trên sản phẩm."
    )
    is_required = fields.Boolean(
        string="Bắt buộc nhập",
        default=False,
        help="Đánh dấu bắt buộc phải nhập giá trị cho thông số này khi khai báo sản phẩm."
    )
    is_searchable = fields.Boolean(
        string="Cho phép tìm kiếm",
        default=True,
        help="Cho phép AI và người dùng tìm kiếm sản phẩm theo thông số này."
    )
    is_critical = fields.Boolean(
        string="Thông số cốt lõi (Matching)",
        default=False,
        help="Đánh dấu thông số quan trọng bắt buộc phải khớp khi AI tìm kiếm phụ tùng thay thế."
    )
    active = fields.Boolean(
        string="Có hiệu lực",
        default=True,
        help="Bỏ chọn để lưu trữ thay vì xóa thông số."
    )
    sequence = fields.Integer(
        string="Thứ tự hiển thị",
        default=10
    )

    value_count = fields.Integer(
        string="Số sản phẩm đang dùng",
        compute="_compute_value_count"
    )

    _sql_constraints = [
        ("code_uniq", "unique(code)", "Mã kỹ thuật (code) của thông số phải là duy nhất!"),
    ]

    @api.depends("code")
    def _compute_value_count(self):
        value_data = self.env["qba.product.spec.value"].read_group(
            [("spec_definition_id", "in", self.ids)],
            ["spec_definition_id"],
            ["spec_definition_id"]
        )
        mapped = {d["spec_definition_id"][0]: d["spec_definition_id_count"] for d in value_data}
        for rec in self:
            rec.value_count = mapped.get(rec.id, 0)

    @api.constrains("code")
    def _check_code_format(self):
        code_regex = re.compile(r"^[a-zA-Z0-9_.-]+$")
        for rec in self:
            if not rec.code or not code_regex.match(rec.code.strip()):
                raise ValidationError(_(
                    "Mã kỹ thuật '%s' không hợp lệ! Mã kỹ thuật chỉ được chứa chữ cái, chữ số, dấu gạch dưới, gạch ngang hoặc dấu chấm."
                ) % (rec.code or ""))

            # Kiểm tra trùng mã kỹ thuật (kể cả với bản ghi đã tắt hiệu lực / lưu trữ)
            duplicate = self.with_context(active_test=False).search([
                ("id", "!=", rec.id),
                ("code", "=", rec.code.strip()),
            ], limit=1)
            if duplicate:
                if not duplicate.active:
                    raise ValidationError(_(
                        "Mã kỹ thuật '%(code)s' đã tồn tại trong hệ thống nhưng đang ở trạng thái TẮT HIỆU LỰC (Thông số: '%(name)s').\n"
                        "Bạn có thể bật lại công tắc 'Có hiệu lực' cho thông số này trên danh mục, hoặc bấm 'Xóa hẳn' thông số cũ trước khi tạo lại!"
                    ) % {"code": rec.code.strip(), "name": duplicate.name})
                else:
                    raise ValidationError(_(
                        "Mã kỹ thuật '%(code)s' đã được sử dụng cho thông số '%(name)s'.\n"
                        "Mã kỹ thuật phải là duy nhất trong toàn bộ hệ thống!"
                    ) % {"code": rec.code.strip(), "name": duplicate.name})

    @api.constrains("data_type", "selection_options")
    def _check_selection_options(self):
        for rec in self:
            if rec.data_type == "selection":
                options = rec._get_parsed_selection_options()
                if not options:
                    raise ValidationError(_(
                        "Thông số '%s' có kiểu dữ liệu là 'Danh sách lựa chọn' nhưng chưa được khai báo các lựa chọn!"
                    ) % rec.name)

    def _get_parsed_selection_options(self):
        """Trả về danh sách các lựa chọn sạch từ selection_options"""
        self.ensure_one()
        if not self.selection_options:
            return []
        raw = [opt.strip() for line in self.selection_options.splitlines() for opt in line.split(",") if opt.strip()]
        return list(dict.fromkeys(raw))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            code = vals.get("code")
            if code:
                code_clean = code.strip()
                duplicate = self.with_context(active_test=False).search([
                    ("code", "=", code_clean),
                ], limit=1)
                if duplicate:
                    if not duplicate.active:
                        raise ValidationError(_(
                            "Mã kỹ thuật '%(code)s' đã tồn tại trong hệ thống nhưng đang ở trạng thái TẮT HIỆU LỰC (Thông số: '%(name)s').\n"
                            "Bạn có thể bật lại công tắc 'Có hiệu lực' cho thông số này trên danh mục, hoặc bấm 'Xóa hẳn' thông số cũ trước khi tạo lại!"
                        ) % {"code": code_clean, "name": duplicate.name})
                    else:
                        raise ValidationError(_(
                            "Mã kỹ thuật '%(code)s' đã được sử dụng cho thông số '%(name)s'.\n"
                            "Mã kỹ thuật phải là duy nhất trong toàn bộ hệ thống!"
                        ) % {"code": code_clean, "name": duplicate.name})
        return super().create(vals_list)

    def write(self, vals):
        if "code" in vals and vals["code"]:
            code_clean = vals["code"].strip()
            for rec in self:
                duplicate = self.with_context(active_test=False).search([
                    ("id", "!=", rec.id),
                    ("code", "=", code_clean),
                ], limit=1)
                if duplicate:
                    if not duplicate.active:
                        raise ValidationError(_(
                            "Mã kỹ thuật '%(code)s' đã tồn tại trong hệ thống nhưng đang ở trạng thái TẮT HIỆU LỰC (Thông số: '%(name)s').\n"
                            "Bạn có thể bật lại công tắc 'Có hiệu lực' cho thông số này trên danh mục, hoặc bấm 'Xóa hẳn' thông số cũ trước khi đổi mã!"
                        ) % {"code": code_clean, "name": duplicate.name})
                    else:
                        raise ValidationError(_(
                            "Mã kỹ thuật '%(code)s' đã được sử dụng cho thông số '%(name)s'.\n"
                            "Mã kỹ thuật phải là duy nhất trong toàn bộ hệ thống!"
                        ) % {"code": code_clean, "name": duplicate.name})

        target_type = vals.get("data_type")
        if target_type:
            for rec in self:
                if rec.data_type != target_type:
                    # Di chuyển dữ liệu trên các giá trị hiện có an toàn và có thể đảo ngược
                    values = self.env["qba.product.spec.value"].sudo().search([("spec_definition_id", "=", rec.id)])
                    for val in values:
                        if target_type == "float":
                            if val.value_char:
                                try:
                                    val.value_float = float(val.value_char.replace(",", "."))
                                except (ValueError, TypeError):
                                    if val.value_integer:
                                        val.value_float = float(val.value_integer)
                            elif val.value_integer:
                                val.value_float = float(val.value_integer)
                                val.value_char = str(val.value_integer)
                            if val.value_char is not False and val.value_char != "":
                                val.value_display = f"{val.value_float:g}"
                        elif target_type == "integer":
                            if val.value_char:
                                try:
                                    val.value_integer = int(float(val.value_char.replace(",", ".")))
                                except (ValueError, TypeError):
                                    val.value_integer = int(val.value_float)
                            elif val.value_float:
                                val.value_integer = int(val.value_float)
                                val.value_char = str(val.value_integer)
                            if val.value_char is not False and val.value_char != "":
                                val.value_display = str(val.value_integer)
        return super().write(vals)

    def action_open_spec_form(self):
        """Mở modal (dialog) chỉnh sửa chi tiết định nghĩa thông số kỹ thuật."""
        self.ensure_one()
        return {
            "name": _("Cấu hình chi tiết: %s") % (self.name or self.code or ""),
            "type": "ir.actions.act_window",
            "res_model": "qba.product.spec.definition",
            "res_id": self.id,
            "view_mode": "form",
            "views": [(self.env.ref("qba_ai.view_qba_product_spec_definition_form").id, "form")],
            "target": "new",
            "context": self.env.context,
        }

    # =========================================================================
    # BACKWARD COMPATIBILITY PROXIES (DEPRECATED IN PHASE 4.0 -> REMOVE IN 5.0)
    # Lý do: Bảo toàn tương thích ngược cho RPC/cached callers cũ.
    # Toàn bộ logic nghiệp vụ thực tế đã được chuyển sang qba.lc.spec.parser.
    # =========================================================================

    @api.model
    def preview_hub_diameter_split(self, category_id=None):
        """[DEPRECATED in Phase 4.0] Proxy chuyển tiếp sang qba.lc.spec.parser."""
        return self.env["qba.lc.spec.parser"].preview_hub_diameter_split(category_id=category_id)

    def action_apply_hub_diameter_split(self):
        """[DEPRECATED in Phase 4.0] Proxy chuyển tiếp sang qba.lc.spec.parser."""
        return self.env["qba.lc.spec.parser"].action_apply_hub_diameter_split()

    @api.model
    def action_rollback_hub_diameter_split(self, category_id=None):
        """[DEPRECATED in Phase 4.0] Proxy chuyển tiếp sang qba.lc.spec.parser."""
        return self.env["qba.lc.spec.parser"].action_rollback_hub_diameter_split(category_id=category_id)


    def action_delete_spec_definition(self):
        """Hành động xóa vĩnh viễn định nghĩa thông số kỹ thuật từ view (kèm dọn dẹp giá trị trên sản phẩm)."""
        self.ensure_one()
        if not self.id:
            return False

        is_manager = (
            self.env.user.has_group("qba_ai.group_qba_ai_manager")
            or self.env.user.has_group("base.group_system")
        )
        if not is_manager:
            raise AccessError(_("Chỉ Quản trị viên QBA AI hoặc Quản trị viên hệ thống mới có quyền xóa thông số kỹ thuật."))

        spec_name = self.name or self.code or ""
        self.unlink()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Đã xóa thành công!"),
                "message": _("Đã xóa vĩnh viễn thông số kỹ thuật '%s' khỏi hệ thống.") % spec_name,
                "type": "success",
                "sticky": False,
                "next": {
                    "type": "ir.actions.client",
                    "tag": "reload",
                },
            },
        }

    def unlink(self):
        is_manager = (
            self.env.user.has_group("qba_ai.group_qba_ai_manager")
            or self.env.user.has_group("base.group_system")
        )
        if not is_manager:
            raise AccessError(_("Chỉ Quản trị viên QBA AI hoặc Quản trị viên hệ thống mới có quyền xóa thông số kỹ thuật."))

        # Kiểm tra bảo vệ dữ liệu sản phẩm: Tuyệt đối không xóa định nghĩa đang có dữ liệu liên kết
        spec_values = self.env["qba.product.spec.value"].sudo().search([("spec_definition_id", "in", self.ids)])
        verified_values = spec_values.filtered(lambda v: v.validation_status == "verified")
        if verified_values:
            raise ValidationError(_(
                "Không thể xóa vĩnh viễn thông số kỹ thuật '%(spec)s' vì đã có %(count)d giá trị sản phẩm được phê duyệt chính thức (verified)!\n"
                "Để bảo toàn toàn vẹn dữ liệu và lịch sử kỹ thuật, vui lòng tắt công tắc 'Có hiệu lực' (active = False) thay vì xóa."
            ) % {
                "spec": ", ".join(self.mapped("name") or self.mapped("code")),
                "count": len(verified_values),
            })

        if spec_values:
            raise ValidationError(_(
                "Không thể xóa định nghĩa thông số kỹ thuật '%(spec)s' vì đang có %(count)d giá trị sản phẩm liên kết.\n"
                "Để tránh mất dữ liệu nháp hoặc lịch sử ngoài ý muốn, vui lòng xóa hoặc gỡ bỏ các giá trị liên kết trên sản phẩm trước, hoặc chuyển thông số sang trạng thái tắt hiệu lực (active = False)!"
            ) % {
                "spec": ", ".join(self.mapped("name") or self.mapped("code")),
                "count": len(spec_values),
            })

        return super().unlink()

