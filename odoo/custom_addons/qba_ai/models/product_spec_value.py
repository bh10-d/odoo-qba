# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, AccessError


class QbaProductSpecValue(models.Model):
    _name = "qba.product.spec.value"
    _description = "Giá Trị Thông Số Kỹ Thuật Sản Phẩm"
    _order = "product_tmpl_id, spec_definition_id"

    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Sản phẩm",
        required=True,
        ondelete="cascade",
        index=True
    )
    spec_definition_id = fields.Many2one(
        "qba.product.spec.definition",
        string="Thông số kỹ thuật",
        required=True,
        ondelete="cascade",
        index=True
    )

    spec_code = fields.Char(
        string="Mã thông số",
        related="spec_definition_id.code",
        store=True,
        readonly=True
    )
    data_type = fields.Selection(
        string="Kiểu dữ liệu",
        related="spec_definition_id.data_type",
        readonly=True
    )
    uom = fields.Char(
        string="Đơn vị tính",
        related="spec_definition_id.uom",
        readonly=True
    )
    is_critical = fields.Boolean(
        string="Thông số cốt lõi",
        related="spec_definition_id.is_critical",
        readonly=True
    )

    # Các trường lưu trữ giá trị theo đúng kiểu chuẩn hóa quan hệ (Single source of truth)
    value_char = fields.Char(string="Giá trị chuỗi / Lựa chọn")
    value_integer = fields.Integer(string="Giá trị số nguyên")
    value_float = fields.Float(string="Giá trị số thực", digits=(16, 4))
    value_boolean = fields.Boolean(string="Giá trị Đúng / Sai")

    # Trường hiển thị đồng bộ hai chiều (giúp nhập liệu nhanh trên One2many list view)
    value_display = fields.Char(
        string="Giá trị",
        compute="_compute_value_display",
        inverse="_inverse_value_display",
        store=True,
        index=True,
        help="Giá trị của thông số kỹ thuật. Hệ thống sẽ tự động ép kiểu và lưu trữ chính xác theo định nghĩa."
    )

    validation_status = fields.Selection([
        ("unverified", "Chưa kiểm duyệt"),
        ("verified", "Đã xác thực"),
        ("conflicted", "Xung đột / Lỗi"),
    ], string="Trạng thái xác thực", default="unverified", required=True, index=True,
       help="Chỉ Quản trị viên AI mới có quyền duyệt thành 'Đã xác thực'. Dữ liệu chưa duyệt hoặc xung đột không được coi là chính thức.")

    source = fields.Selection([
        ("manual_entry", "Nhập thủ công"),
        ("parsed_from_name", "Trích xuất từ tên"),
    ], string="Nguồn dữ liệu", default="manual_entry", required=True)

    notes = fields.Text(string="Ghi chú / Lý do xung đột")

    verified_by_id = fields.Many2one(
        "res.users",
        string="Người xác thực",
        readonly=True,
        copy=False
    )
    verified_date = fields.Datetime(
        string="Ngày xác thực",
        readonly=True,
        copy=False
    )

    _sql_constraints = [
        ("uniq_product_spec", "unique(product_tmpl_id, spec_definition_id)",
         "Mỗi thông số kỹ thuật chỉ được có một giá trị duy nhất trên cùng một sản phẩm!"),
    ]

    def _compute_display_name(self):
        for rec in self:
            spec_name = rec.spec_definition_id.name or ""
            val = rec.value_display or ""
            uom_str = f" {rec.uom}" if rec.uom else ""
            prod_name = rec.product_tmpl_id.display_name or ""
            rec.display_name = f"{prod_name} - {spec_name}: {val}{uom_str}"

    @api.depends("spec_definition_id.data_type", "value_char", "value_integer", "value_float", "value_boolean")
    def _compute_value_display(self):
        for rec in self:
            dtype = rec.spec_definition_id.data_type
            if rec.value_char is False:
                # Giá trị chưa nhập / để trống (unknown)
                if dtype == "integer" and rec.value_integer:
                    rec.value_display = str(rec.value_integer)
                elif dtype == "float" and rec.value_float:
                    rec.value_display = f"{rec.value_float:g}"
                else:
                    rec.value_display = ""
                continue
            if dtype in ("char", "selection"):
                rec.value_display = rec.value_char or ""
            elif dtype == "integer":
                rec.value_display = str(rec.value_integer) if rec.value_char else ""
            elif dtype == "float":
                if rec.value_char:
                    if (rec.value_float == 0.0 or rec.value_float is False) and rec.value_char not in ("0", "0.0", "0,0"):
                        try:
                            rec.value_float = float(rec.value_char.replace(",", "."))
                        except (ValueError, TypeError):
                            pass
                    rec.value_display = f"{rec.value_float:g}" if rec.value_float is not False else ""
                else:
                    rec.value_display = f"{rec.value_float:g}" if rec.value_float else ""
            elif dtype == "boolean":
                rec.value_display = "Đúng" if rec.value_boolean else "Sai"
            else:
                rec.value_display = rec.value_char or ""

    def _inverse_value_display(self):
        for rec in self:
            val_str = (rec.value_display or "").strip()
            dtype = rec.spec_definition_id.data_type
            if not dtype or not val_str:
                rec.value_char = False
                rec.value_integer = 0
                rec.value_float = 0.0
                rec.value_boolean = False
                continue

            if dtype == "integer":
                try:
                    # Ràng buộc số nguyên: không chấp nhận số có phần thập phân (ví dụ: 10.5 hoặc 10,5)
                    if "." in val_str or "," in val_str:
                        raise ValueError()
                    rec.value_integer = int(val_str)
                    rec.value_char = str(rec.value_integer)
                    rec.value_display = str(rec.value_integer)
                except (ValueError, TypeError):
                    raise ValidationError(_(
                        "Giá trị '%s' cho thông số '%s' không phải là số nguyên hợp lệ!"
                    ) % (val_str, rec.spec_definition_id.name))
            elif dtype == "float":
                try:
                    clean_str = val_str.replace(",", ".")
                    rec.value_float = float(clean_str)
                    rec.value_char = clean_str
                    rec.value_display = f"{rec.value_float:g}"
                except (ValueError, TypeError):
                    raise ValidationError(_(
                        "Giá trị '%s' cho thông số '%s' không phải là số thực hợp lệ!"
                    ) % (val_str, rec.spec_definition_id.name))
            elif dtype == "boolean":
                lower_val = val_str.lower()
                if lower_val in ("true", "1", "có", "co", "dung", "đúng", "yes", "y"):
                    rec.value_boolean = True
                    rec.value_display = "Đúng"
                elif lower_val in ("false", "0", "không", "khong", "sai", "no", "n"):
                    rec.value_boolean = False
                    rec.value_display = "Sai"
                else:
                    raise ValidationError(_(
                        "Giá trị '%s' cho thông số '%s' không phải kiểu Đúng/Sai (chấp nhận: Đúng/Sai, Có/Không, 1/0)."
                    ) % (val_str, rec.spec_definition_id.name))
            elif dtype == "selection":
                allowed = rec.spec_definition_id._get_parsed_selection_options()
                if allowed and val_str not in allowed:
                    raise ValidationError(_(
                        "Giá trị '%s' không hợp lệ cho thông số '%s'. Các giá trị được phép: %s"
                    ) % (val_str, rec.spec_definition_id.name, ", ".join(allowed)))
                rec.value_char = val_str
                rec.value_display = val_str
            else:  # char
                rec.value_char = val_str
                rec.value_display = val_str

    @api.constrains("product_tmpl_id", "spec_definition_id")
    def _check_unique_product_spec(self):
        for rec in self:
            duplicates = self.search([
                ("id", "!=", rec.id),
                ("product_tmpl_id", "=", rec.product_tmpl_id.id),
                ("spec_definition_id", "=", rec.spec_definition_id.id),
            ], limit=1)
            if duplicates:
                raise ValidationError(_(
                    "Thông số '%s' đã được định nghĩa cho sản phẩm '%s'. Không thể tạo trùng lặp!"
                ) % (rec.spec_definition_id.name, rec.product_tmpl_id.display_name))

    @api.constrains("product_tmpl_id", "spec_definition_id")
    def _check_category_applicability(self):
        for rec in self:
            if not rec.spec_definition_id or not rec.product_tmpl_id:
                continue
            def_categs = rec.spec_definition_id.category_ids
            if not def_categs:
                continue  # Áp dụng chung cho mọi danh mục

            prod_categ = rec.product_tmpl_id.categ_id
            if not prod_categ:
                raise ValidationError(_(
                    "Sản phẩm '%s' chưa được gán danh mục, không thể gán thông số kỹ thuật '%s'."
                ) % (rec.product_tmpl_id.display_name, rec.spec_definition_id.name))

            applicable_ids = set(self.env["product.category"].search([("id", "child_of", def_categs.ids)]).ids)
            if prod_categ.id not in applicable_ids:
                raise ValidationError(_(
                    "Thông số '%s' chỉ áp dụng cho danh mục: %s. Sản phẩm hiện thuộc danh mục '%s' không phù hợp!"
                ) % (
                    rec.spec_definition_id.name,
                    ", ".join(def_categs.mapped("display_name")),
                    prod_categ.display_name
                ))

    @api.constrains("spec_definition_id", "value_char", "value_integer", "value_float", "value_boolean", "validation_status")
    def _check_value_data_type(self):
        for rec in self:
            if not rec.spec_definition_id:
                continue
            dtype = rec.spec_definition_id.data_type
            if dtype == "selection":
                allowed = rec.spec_definition_id._get_parsed_selection_options()
                if allowed and rec.value_char and rec.value_char not in allowed:
                    raise ValidationError(_(
                        "Giá trị '%s' không hợp lệ cho thông số '%s'. Các giá trị được phép: %s"
                    ) % (rec.value_char, rec.spec_definition_id.name, ", ".join(allowed)))
            # Bắt buộc nhập được áp dụng nghiêm ngặt khi phê duyệt chính thức
            if rec.validation_status == "verified" and rec.spec_definition_id.is_required:
                val_char = rec.value_char or rec.value_display
                if dtype in ("char", "selection") and not val_char:
                    raise ValidationError(_("Thông số '%s' là bắt buộc nhập giá trị trước khi phê duyệt.") % rec.spec_definition_id.name)
                elif dtype == "integer" and not val_char:
                    raise ValidationError(_("Thông số '%s' là bắt buộc nhập số nguyên trước khi phê duyệt.") % rec.spec_definition_id.name)
                elif dtype == "float" and not val_char:
                    raise ValidationError(_("Thông số '%s' là bắt buộc nhập số thực trước khi phê duyệt.") % rec.spec_definition_id.name)

    # =========================================================================
    # QUY TRÌNH PHÊ DUYỆT & BẢO VỆ DỮ LIỆU SERVER-SIDE (SECURITY ENFORCEMENT)
    # =========================================================================

    def action_verify(self):
        """Chỉ Quản trị viên AI có quyền duyệt chính thức"""
        if not self.env.user.has_group("qba_ai.group_qba_ai_manager"):
            raise AccessError(_("Chỉ Quản trị viên QBA AI (AI Manager) mới có quyền phê duyệt thông số kỹ thuật chính thức."))
        self.write({
            "validation_status": "verified",
            "verified_by_id": self.env.user.id,
            "verified_date": fields.Datetime.now(),
        })

    def action_reject(self):
        """Chỉ Quản trị viên AI có quyền đánh dấu xung đột / từ chối"""
        if not self.env.user.has_group("qba_ai.group_qba_ai_manager"):
            raise AccessError(_("Chỉ Quản trị viên QBA AI (AI Manager) mới có quyền từ chối / đánh dấu xung đột thông số kỹ thuật."))
        self.write({
            "validation_status": "conflicted",
        })

    def action_reset_unverified(self):
        """Chỉ Quản trị viên AI có quyền thu hồi xác thực về bản nháp"""
        if not self.env.user.has_group("qba_ai.group_qba_ai_manager"):
            raise AccessError(_("Chỉ Quản trị viên QBA AI (AI Manager) mới có quyền thu hồi xác thực thông số kỹ thuật."))
        self.write({
            "validation_status": "unverified",
            "verified_by_id": False,
            "verified_date": False,
        })

    @api.model_create_multi
    def create(self, vals_list):
        is_ai_manager = self.env.user.has_group("qba_ai.group_qba_ai_manager")
        for vals in vals_list:
            if "value_display" in vals:
                val_str = (vals["value_display"] or "").strip()
                spec_def = self.env["qba.product.spec.definition"].browse(vals.get("spec_definition_id"))
                dtype = spec_def.data_type if spec_def else False
                if not dtype or not val_str:
                    vals["value_char"] = False
                    vals["value_integer"] = 0
                    vals["value_float"] = 0.0
                    vals["value_boolean"] = False
                elif dtype == "integer":
                    try:
                        if "." in val_str or "," in val_str:
                            raise ValueError()
                        vals["value_integer"] = int(val_str)
                        vals["value_char"] = str(vals["value_integer"])
                        vals["value_display"] = str(vals["value_integer"])
                    except (ValueError, TypeError):
                        raise ValidationError(_(
                            "Giá trị '%s' cho thông số '%s' không phải là số nguyên hợp lệ!"
                        ) % (val_str, spec_def.name if spec_def else ""))
                elif dtype == "float":
                    try:
                        clean_str = val_str.replace(",", ".")
                        vals["value_float"] = float(clean_str)
                        vals["value_char"] = clean_str
                        vals["value_display"] = f"{vals['value_float']:g}"
                    except (ValueError, TypeError):
                        raise ValidationError(_(
                            "Giá trị '%s' cho thông số '%s' không phải là số thực hợp lệ!"
                        ) % (val_str, spec_def.name if spec_def else ""))
                elif dtype == "boolean":
                    lower_val = val_str.lower()
                    if lower_val in ("true", "1", "có", "co", "dung", "đúng", "yes", "y"):
                        vals["value_boolean"] = True
                        vals["value_display"] = "Đúng"
                    elif lower_val in ("false", "0", "không", "khong", "sai", "no", "n"):
                        vals["value_boolean"] = False
                        vals["value_display"] = "Sai"
                    else:
                        raise ValidationError(_(
                            "Giá trị '%s' cho thông số '%s' không phải kiểu Đúng/Sai."
                        ) % (val_str, spec_def.name if spec_def else ""))
                elif dtype == "selection":
                    allowed = spec_def._get_parsed_selection_options() if spec_def else []
                    if allowed and val_str not in allowed:
                        raise ValidationError(_(
                            "Giá trị '%s' không hợp lệ cho thông số '%s'. Các giá trị được phép: %s"
                        ) % (val_str, spec_def.name if spec_def else "", ", ".join(allowed)))
                    vals["value_char"] = val_str
                else:  # char
                    vals["value_char"] = val_str

            status = vals.get("validation_status")
            if status and status != "unverified":
                if not is_ai_manager:
                    raise AccessError(_("Chỉ Quản trị viên QBA AI mới có thể tạo thông số ở trạng thái khác 'Chưa kiểm duyệt'."))
                if status == "verified":
                    vals.setdefault("verified_by_id", self.env.user.id)
                    vals.setdefault("verified_date", fields.Datetime.now())
        return super().create(vals_list)

    def write(self, vals):
        is_ai_manager = self.env.user.has_group("qba_ai.group_qba_ai_manager")

        # 1. Bảo vệ trạng thái duyệt và thông tin xác thực khỏi người dùng không có quyền Quản trị viên AI
        if not is_ai_manager:
            if "validation_status" in vals:
                for rec in self:
                    if vals["validation_status"] != rec.validation_status:
                        raise AccessError(_("Chỉ Quản trị viên QBA AI mới có quyền thay đổi trạng thái phê duyệt ('validation_status') của thông số kỹ thuật."))
            if any(f in vals for f in ("verified_by_id", "verified_date")):
                raise AccessError(_("Chỉ Quản trị viên QBA AI mới có quyền thay đổi thông tin người duyệt và ngày duyệt."))

        # 2. Kiểm tra nếu người dùng không phải Quản trị viên AI sửa bản ghi ĐÃ XÁC THỰC
        if not is_ai_manager:
            critical_fields = {
                "value_char", "value_integer", "value_float", "value_boolean",
                "value_display", "spec_definition_id", "product_tmpl_id", "source", "notes"
            }
            if any(f in vals for f in critical_fields):
                for rec in self:
                    if rec.validation_status == "verified":
                        raise AccessError(_(
                            "Không thể sửa đổi thông số kỹ thuật đã được Quản trị viên AI xác thực ('%s' cho '%s'). "
                            "Vui lòng yêu cầu Quản trị viên AI thu hồi xác thực trước khi chỉnh sửa."
                        ) % (rec.spec_definition_id.name, rec.product_tmpl_id.display_name))

        if vals.get("validation_status") == "verified":
            vals.setdefault("verified_by_id", self.env.user.id)
            vals.setdefault("verified_date", fields.Datetime.now())
        elif "validation_status" in vals and vals["validation_status"] != "verified":
            vals["verified_by_id"] = False
            vals["verified_date"] = False

        return super().write(vals)

    def unlink(self):
        is_ai_manager = self.env.user.has_group("qba_ai.group_qba_ai_manager")
        if not is_ai_manager:
            for rec in self:
                if rec.validation_status == "verified":
                    raise AccessError(_(
                        "Chỉ Quản trị viên QBA AI mới có quyền xóa thông số kỹ thuật đã được xác thực ('%s')."
                    ) % rec.spec_definition_id.name)
        return super().unlink()

