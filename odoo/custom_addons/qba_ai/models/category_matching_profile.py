# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class QbaCategoryMatchingProfile(models.Model):
    _name = "qba.category.matching.profile"
    _description = "Hồ Sơ Cấu Hình So Khớp Thông Số Theo Danh Mục (Category Matching Profile)"
    _order = "sequence, id"

    name = fields.Char(
        string="Tên hồ sơ",
        required=True,
        translate=True,
        help="Tên mô tả cấu hình so khớp (ví dụ: 'Hồ sơ so khớp Lá Côn', 'Hồ sơ so khớp Tăm Bua')."
    )
    category_id = fields.Many2one(
        "product.category",
        string="Danh mục sản phẩm áp dụng",
        required=True,
        index=True,
        ondelete="restrict",
        help="Danh mục sản phẩm áp dụng hồ sơ quy tắc này. Tự động áp dụng cho các danh mục con nếu danh mục con chưa có hồ sơ riêng."
    )
    active = fields.Boolean(
        string="Có hiệu lực",
        default=True,
        help="Bật/tắt hồ sơ so khớp."
    )
    sequence = fields.Integer(
        string="Thứ tự ưu tiên",
        default=10
    )
    min_score_threshold = fields.Float(
        string="Ngưỡng điểm tối thiểu (%)",
        default=80.0,
        help="Ngưỡng điểm kỹ thuật tối thiểu (0 - 100) để một sản phẩm được coi là Partial Match hợp lệ."
    )
    allow_partial_match = fields.Boolean(
        string="Cho phép đề xuất Partial Match",
        default=True,
        help="Nếu bật, hệ thống sẽ đề xuất các ứng viên khớp trong dung sai kỹ thuật khi không có ứng viên Exact Match."
    )
    rule_ids = fields.One2many(
        "qba.category.matching.rule",
        "profile_id",
        string="Danh sách quy tắc so khớp",
        copy=True,
        help="Các quy tắc so khớp, dung sai và trọng số cho từng thông số kỹ thuật."
    )
    notes = fields.Text(
        string="Ghi chú kỹ thuật",
        help="Mô tả tiêu chuẩn ngành, lưu ý dung sai lắp ráp của danh mục phụ tùng này."
    )

    _sql_constraints = [
        ("uniq_category_profile", "unique(category_id)",
         "Mỗi danh mục sản phẩm chỉ được có một Hồ sơ cấu hình so khớp (Matching Profile) duy nhất!"),
    ]

    @api.constrains("min_score_threshold")
    def _check_min_score_threshold(self):
        for rec in self:
            if rec.min_score_threshold < 0.0 or rec.min_score_threshold > 100.0:
                raise ValidationError(_("Ngưỡng điểm tối thiểu phải nằm trong khoảng từ 0% đến 100%!"))


class QbaCategoryMatchingRule(models.Model):
    _name = "qba.category.matching.rule"
    _description = "Quy Tắc So Khớp Thông Số Kỹ Thuật (Matching Rule)"
    _order = "sequence, id"

    profile_id = fields.Many2one(
        "qba.category.matching.profile",
        string="Hồ sơ so khớp",
        required=True,
        ondelete="cascade",
        index=True
    )
    active = fields.Boolean(
        string="Có hiệu lực",
        default=True,
        help="Bật/tắt quy tắc so khớp này mà không cần xóa."
    )
    spec_definition_id = fields.Many2one(
        "qba.product.spec.definition",
        string="Thông số kỹ thuật",
        required=True,
        ondelete="restrict",
        index=True,
        help="Thông số kỹ thuật được áp dụng quy tắc so khớp."
    )
    spec_code = fields.Char(
        string="Mã thông số",
        related="spec_definition_id.code",
        store=True,
        readonly=True
    )
    spec_name = fields.Char(
        string="Tên thông số",
        related="spec_definition_id.name",
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

    match_type = fields.Selection([
        ("exact", "Bắt buộc bằng tuyệt đối (Exact)"),
        ("tolerance", "Cho phép sai số dung sai (Tolerance)"),
        ("range", "Nằm trong khoảng (Range)"),
        ("subset", "Tập con / Chứa giá trị (Subset)"),
    ], string="Kiểu so khớp", required=True, default="exact",
       help="exact: phải bằng chính xác; tolerance: cho phép lệch trong khoảng ±; range: giá trị nằm trong min-max.")

    is_hard_constraint = fields.Boolean(
        string="Điều kiện bắt buộc (Hard Constraint)",
        default=False,
        help="Nếu bật: bắt buộc phải thỏa mãn. Nếu vi phạm, sản phẩm bị kết luận Mismatch ngay lập tức và không thể bù trừ bởi điểm số."
    )

    tolerance_type = fields.Selection([
        ("absolute", "Tuyệt đối (Đơn vị đo)"),
        ("percent", "Phần trăm (%)"),
    ], string="Kiểu dung sai", default="absolute")

    tolerance_plus = fields.Float(
        string="Dung sai dương (+)",
        default=0.0,
        help="Độ lệch dương tối đa cho phép (ví dụ: +0.5 mm)."
    )
    tolerance_minus = fields.Float(
        string="Dung sai âm (-)",
        default=0.0,
        help="Độ lệch âm tối đa cho phép (giá trị dương biểu thị độ lệch âm, ví dụ: 0.5 nghĩa là cho phép lệch -0.5 mm)."
    )

    weight = fields.Float(
        string="Trọng số tính điểm",
        default=10.0,
        help="Trọng số của thông số này trong tổng điểm kỹ thuật (1.0 - 100.0)."
    )
    penalty_per_unit = fields.Float(
        string="Tỷ lệ trừ điểm trên mỗi đơn vị lệch",
        default=0.0,
        help="Số điểm bị trừ trên mỗi đơn vị đo lệch trong khoảng dung sai."
    )

    allow_substitute = fields.Boolean(
        string="Cho phép thay thế kỹ thuật",
        default=False,
        help="Cho phép thay thế giá trị này bằng giá trị tương đương theo tiêu chuẩn kỹ thuật ngành."
    )
    substitute_values = fields.Char(
        string="Giá trị thay thế hợp lệ",
        help="Danh sách các giá trị tương đương được chấp nhận, cách nhau bởi dấu phẩy (ví dụ: '38, 38.5')."
    )
    substitute_note = fields.Char(
        string="Cơ sở kỹ thuật thay thế",
        help="Tài liệu hoặc căn cứ kỹ thuật cho phép thay thế (ví dụ: 'Cho phép thay thế theo tiêu chuẩn nhà sản xuất X')."
    )

    sequence = fields.Integer(
        string="Thứ tự",
        default=10
    )

    _sql_constraints = [
        ("uniq_profile_spec", "unique(profile_id, spec_definition_id)",
         "Mỗi thông số kỹ thuật chỉ được khai báo một quy tắc so khớp duy nhất trong cùng một Hồ sơ!"),
    ]

    @api.constrains("tolerance_plus", "tolerance_minus", "weight")
    def _check_tolerances(self):
        for rec in self:
            if rec.tolerance_plus < 0.0 or rec.tolerance_minus < 0.0:
                raise ValidationError(_("Dung sai dương và dung sai âm không được là số âm!"))
            if rec.weight <= 0.0:
                raise ValidationError(_("Trọng số tính điểm phải là số dương lớn hơn 0!"))

