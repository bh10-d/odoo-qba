# -*- coding: utf-8 -*-
import logging
import time
from odoo import models, api, _
from odoo.exceptions import AccessError
from odoo.tools import html_escape

_logger = logging.getLogger(__name__)


class QbaSpecMatchingEngine(models.AbstractModel):
    _name = "qba.spec.matching.engine"
    _description = "Động Cơ So Khớp Thông Số Kỹ Thuật Đa Danh Mục (Generic Spec Matching Engine)"

    # =========================================================================
    # 1. SPECIFICATION RESOLVER (Xác định Profile & Thông số theo danh mục)
    # =========================================================================

    @api.model
    def resolve_profile(self, category_id):
        """Xác định Category Matching Profile phù hợp cho danh mục.
        Hỗ trợ kế thừa từ danh mục cha nếu danh mục con chưa được cấu hình profile riêng.
        Nếu toàn bộ cây danh mục chưa có profile, tự động sinh Profile suy diễn (Inferred Profile).
        """
        category = self.env["product.category"].browse(category_id) if isinstance(category_id, int) else category_id
        if not category:
            return False

        profile_model = self.env["qba.category.matching.profile"]

        # 1. Tìm profile trực tiếp trên danh mục hoặc cây danh mục cha
        curr = category
        while curr:
            profile = profile_model.search([
                ("category_id", "=", curr.id),
                ("active", "=", True),
            ], limit=1)
            if profile:
                return profile
            curr = curr.parent_id

        # 2. Nếu chưa có profile trong DB, sinh cấu hình suy diễn an toàn từ qba.product.spec.definition
        return self._build_inferred_profile(category)

    @api.model
    def _build_inferred_profile(self, category):
        """Tạo cấu hình so khớp suy diễn an toàn từ định nghĩa thông số của danh mục"""
        parent_ids = self.env["product.category"].search([("id", "parent_of", category.id)]).ids
        spec_defs = self.env["qba.product.spec.definition"].search([
            "|",
            ("category_ids", "=", False),
            ("category_ids", "in", parent_ids),
            ("active", "=", True),
        ])

        if not spec_defs:
            return {
                "id": False,
                "name": _("Chưa có hồ sơ: %s") % category.display_name,
                "category_id": category.id,
                "min_score_threshold": 80.0,
                "allow_partial_match": False,
                "is_inferred": True,
                "has_valid_rules": False,
                "rule_dicts": [],
            }

        inferred_rules = []
        for s in spec_defs:
            is_critical = bool(s.is_critical)
            match_type = "tolerance" if s.data_type == "float" else "exact"
            inferred_rules.append({
                "spec_definition_id": s.id,
                "spec_code": s.code,
                "spec_name": s.name,
                "data_type": s.data_type,
                "uom": s.uom,
                "match_type": match_type,
                "is_hard_constraint": is_critical,
                "tolerance_type": "absolute",
                "tolerance_plus": 0.0,
                "tolerance_minus": 0.0,
                "weight": 20.0 if is_critical else 10.0,
                "allow_substitute": False,
                "substitute_values": "",
                "substitute_note": "",
                "penalty_per_unit": 0.0,
            })

        return {
            "id": False,
            "name": _("Hồ sơ suy diễn tự động: %s") % category.display_name,
            "category_id": category.id,
            "min_score_threshold": 80.0,
            "allow_partial_match": True,
            "is_inferred": True,
            "has_valid_rules": True,
            "rule_dicts": inferred_rules,
        }

    # =========================================================================
    # 2. VALUE NORMALIZATION (Chuẩn hóa giá trị & Đơn vị đo)
    # =========================================================================

    @api.model
    def normalize_value(self, raw_val, data_type, uom_from=None, uom_to=None):
        """Chuẩn hóa giá trị và chuyển đổi đơn vị đo nếu có quy ước hợp lệ.
        Trả về: (normalized_value, success_flag, message)
        """
        if raw_val is None or raw_val is False:
            return None, True, ""

        # Ép kiểu dữ liệu
        val = raw_val
        if data_type == "float":
            try:
                if isinstance(val, str):
                    val = float(val.strip().replace(",", "."))
                else:
                    val = float(val)
            except (ValueError, TypeError):
                return None, False, _("Không thể chuyển đổi '%s' sang số thực") % raw_val

        elif data_type == "integer":
            try:
                if isinstance(val, str):
                    val = int(float(val.strip().replace(",", ".")))
                else:
                    val = int(val)
            except (ValueError, TypeError):
                return None, False, _("Không thể chuyển đổi '%s' sang số nguyên") % raw_val

        elif data_type == "boolean":
            if isinstance(val, str):
                v_lower = val.strip().lower()
                val = v_lower in ("true", "1", "yes", "đúng", "dung", "t", "y")
            else:
                val = bool(val)

        elif data_type in ("char", "selection"):
            val = str(val).strip()

        # Chuyển đổi đơn vị đo (Unit Conversion) nếu cần
        if uom_from and uom_to and str(uom_from).strip().lower() != str(uom_to).strip().lower():
            val, converted = self._convert_uom(val, uom_from, uom_to)
            if not converted:
                return val, True, _("Đơn vị '%s' và '%s' không hỗ trợ chuyển đổi tự động") % (uom_from, uom_to)

        return val, True, ""

    @api.model
    def _convert_uom(self, val, uom_from, uom_to):
        """Chuyển đổi các đơn vị đo kỹ thuật cơ bản thường gặp"""
        if not isinstance(val, (int, float)):
            return val, False

        u_from = str(uom_from).strip().lower()
        u_to = str(uom_to).strip().lower()

        # Bảng hệ số chuyển đổi sang mm
        factors_to_mm = {
            "mm": 1.0,
            "milimet": 1.0,
            "millimeter": 1.0,
            "cm": 10.0,
            "centimet": 10.0,
            "centimeter": 10.0,
            "dm": 100.0,
            "decimet": 100.0,
            "m": 1000.0,
            "met": 1000.0,
            "meter": 1000.0,
            "inch": 25.4,
            "in": 25.4,
            '"': 25.4,
        }

        if u_from in factors_to_mm and u_to in factors_to_mm:
            val_in_mm = val * factors_to_mm[u_from]
            val_target = val_in_mm / factors_to_mm[u_to]
            return val_target, True

        return val, False

    # =========================================================================
    # 3. CANDIDATE RETRIEVAL (Truy xuất ứng viên an toàn)
    # =========================================================================

    @api.model
    def retrieve_candidates(self, category_id, input_specs=None, profile=None, domain=None, limit=100):
        """Truy xuất các sản phẩm ứng viên thuộc danh mục.
        Chỉ đọc dữ liệu, không sửa đổi bất kỳ thông tin nào.
        """
        category = self.env["product.category"].browse(category_id) if isinstance(category_id, int) else category_id
        if not category:
            return self.env["product.template"].browse()

        base_domain = [
            ("categ_id", "child_of", category.id),
            ("active", "=", True),
        ]
        if domain:
            base_domain += domain

        return self.env["product.template"].search(base_domain, limit=limit)

    # =========================================================================
    # 4. MATCHING EVALUATOR (Đánh giá từng thông số theo hồ sơ quy tắc)
    # =========================================================================

    @api.model
    def _get_category_spec_definitions(self, category):
        """Lấy toàn bộ định nghĩa thông số kỹ thuật (Spec Definitions) của danh mục và cây danh mục cha"""
        if not category:
            return self.env["qba.product.spec.definition"].browse()
        parent_ids = self.env["product.category"].search([("id", "parent_of", category.id)]).ids
        return self.env["qba.product.spec.definition"].search([
            "|",
            ("category_ids", "=", False),
            ("category_ids", "in", parent_ids),
            ("active", "=", True),
        ])

    @api.model
    def evaluate_candidate(self, candidate, input_specs, profile, category=None, preloaded_specs_map=None):
        """Đánh giá chi tiết một sản phẩm ứng viên theo bộ thông số đầu vào và quy tắc của Profile.
        QUY TẮC AN TOÀN:
        - Chỉ dùng dữ liệu có validation_status == 'verified' để kết luận tương thích.
        - Dữ liệu unverified hoặc conflicted KHÔNG ĐƯỢC khẳng định tương thích.
        - Điểm số không thể bù trừ cho một thông số bắt buộc (hard constraint) bị vi phạm.
        - Không bỏ qua thông số cốt lõi hoặc thông số trong input_specs chỉ vì thiếu rule trong profile.
        - Đầu vào một phần (như chỉ nhập 1 thông số) không được kết luận tương thích tổng thể 100%.
        """
        # Thu thập các spec_code bị vô hiệu hóa (active=False) trên profile
        inactive_codes = set()
        if hasattr(profile, "rule_ids"):
            for r in profile.rule_ids:
                if not getattr(r, "active", True) and r.spec_code:
                    inactive_codes.add(r.spec_code)
            if hasattr(profile, "id") and profile.id:
                inactive_recs = self.env["qba.category.matching.rule"].with_context(active_test=False).search([
                    ("profile_id", "=", profile.id),
                    ("active", "=", False),
                ])
                for r in inactive_recs:
                    if r.spec_code:
                        inactive_codes.add(r.spec_code)

        rules = self._get_rules_from_profile(profile)
        rules_by_code = {r["spec_code"]: dict(r) for r in rules if r.get("spec_code") not in inactive_codes}

        if not category:
            category = profile.category_id if getattr(profile, "category_id", False) else (candidate.categ_id if candidate else False)

        cat_defs = self._get_category_spec_definitions(category)
        cat_defs_by_code = {d.code: d for d in cat_defs}

        # Lấy bản đồ thông số kỹ thuật của sản phẩm ứng viên (hỗ trợ preloaded để tối ưu N+1)
        if preloaded_specs_map is not None:
            candidate_specs_map = preloaded_specs_map
        else:
            candidate_specs_map = {}
            for val_rec in candidate.spec_value_ids:
                if not val_rec.spec_definition_id or not val_rec.spec_definition_id.active:
                    continue
                code = val_rec.spec_code
                candidate_specs_map[code] = {
                    "val_rec": val_rec,
                    "validation_status": val_rec.validation_status,
                    "is_verified": val_rec.validation_status == "verified",
                    "raw_value": self._get_typed_spec_value(val_rec),
                    "uom": val_rec.uom,
                    "data_type": val_rec.data_type,
                }

        # Tập hợp danh sách thông số cần đánh giá theo thứ tự:
        # 1. Các rule đang hoạt động trong profile
        # 2. Các thông số do người dùng chỉ định trong input_specs (nếu chưa có rule và không bị inactive)
        all_spec_codes = list(rules_by_code.keys())
        for code in (input_specs or {}).keys():
            if code not in all_spec_codes and code not in inactive_codes:
                all_spec_codes.append(code)

        # Xây dựng danh sách rules đầy đủ (tổng hợp rule cấu hình + rule suy diễn tự động)
        combined_rules = []
        for spec_code in all_spec_codes:
            if spec_code in rules_by_code:
                r = rules_by_code[spec_code]
                combined_rules.append(r)
            else:
                d = cat_defs_by_code.get(spec_code) or self.env["qba.product.spec.definition"].search([
                    ("code", "=", spec_code), ("active", "=", True)
                ], limit=1)
                if not d:
                    continue
                is_crit = bool(d.is_critical or d.is_required)
                combined_rules.append({
                    "spec_definition_id": d.id,
                    "spec_code": d.code,
                    "spec_name": d.name,
                    "data_type": d.data_type,
                    "uom": d.uom or "",
                    "match_type": "tolerance" if d.data_type == "float" else "exact",
                    "is_hard_constraint": is_crit,
                    "tolerance_type": "absolute",
                    "tolerance_plus": 0.0,
                    "tolerance_minus": 0.0,
                    "weight": 20.0 if is_crit else 10.0,
                    "allow_substitute": False,
                    "substitute_values": "",
                    "substitute_note": "",
                    "penalty_per_unit": 0.0,
                    "is_missing_profile_rule": True,
                })

        comparison_lines = []
        violated_hard_constraints = []
        missing_critical_specs = []
        has_unverified_critical_data = False

        total_weight = 0.0
        achieved_weight = 0.0
        has_partial_match_spec = False

        # Xác định tổng số thông số cốt lõi trong danh mục/profile để nhận diện tra cứu một phần
        total_critical_codes = set()
        for r in combined_rules:
            if r.get("is_hard_constraint"):
                total_critical_codes.add(r["spec_code"])

        evaluated_critical_codes = set()
        evaluated_specs_count = 0

        for rule in combined_rules:
            spec_code = rule["spec_code"]
            spec_name = rule["spec_name"]
            data_type = rule["data_type"]
            rule_uom = rule.get("uom") or ""
            is_hard = rule["is_hard_constraint"]
            weight = rule.get("weight", 10.0)
            is_missing_rule = rule.get("is_missing_profile_rule", False)

            # Lấy giá trị đầu vào
            raw_input = input_specs.get(spec_code) if input_specs else None
            input_uom = rule_uom
            if isinstance(raw_input, dict):
                input_uom = raw_input.get("uom", rule_uom)
                raw_input = raw_input.get("value")

            if raw_input is None or raw_input == "":
                # Người dùng không cung cấp thông số này trong yêu cầu
                continue

            evaluated_specs_count += 1
            if is_hard:
                evaluated_critical_codes.add(spec_code)

            input_val, input_ok, _msg = self.normalize_value(raw_input, data_type, uom_from=input_uom, uom_to=rule_uom)

            # Lấy giá trị của ứng viên
            cand_info = candidate_specs_map.get(spec_code)
            if not cand_info:
                # Ứng viên thiếu thông số này
                if is_hard:
                    missing_critical_specs.append({
                        "spec_code": spec_code,
                        "spec_name": spec_name,
                        "input_val": input_val,
                        "candidate_val": None,
                        "reason": _("Chưa có dữ liệu verified trong hệ thống (Không thể thay thế nếu chưa xác minh kích thước)"),
                    })
                comparison_lines.append({
                    "spec_code": spec_code,
                    "spec_name": spec_name,
                    "input_val": input_val,
                    "candidate_val": None,
                    "delta": None,
                    "uom": rule_uom,
                    "line_status": "insufficient_data" if is_hard else "skipped_missing",
                    "score": 0.0,
                    "weight": weight,
                    "notes": _("Chưa có dữ liệu verified trong hệ thống (Hard constraint: Không thể thay thế nếu chưa xác minh)") if is_hard else _("Thiếu dữ liệu thông số trên sản phẩm"),
                    "is_hard_constraint": is_hard,
                    "is_missing_profile_rule": is_missing_rule,
                })
                continue

            # Kiểm tra trạng thái xác thực của ứng viên (Verified Protection)
            if not cand_info["is_verified"]:
                # Dữ liệu chưa xác thực hoặc xung đột! Tuyệt đối không khẳng định tương thích kỹ thuật!
                if is_hard:
                    has_unverified_critical_data = True
                    missing_critical_specs.append({
                        "spec_code": spec_code,
                        "spec_name": spec_name,
                        "input_val": input_val,
                        "candidate_val": cand_info["raw_value"],
                        "reason": _("Thông số chưa được Quản trị viên duyệt (trạng thái: %s)") % cand_info["validation_status"],
                    })
                comparison_lines.append({
                    "spec_code": spec_code,
                    "spec_name": spec_name,
                    "input_val": input_val,
                    "candidate_val": cand_info["raw_value"],
                    "delta": None,
                    "uom": cand_info["uom"] or rule_uom,
                    "line_status": "unverified_data",
                    "score": 0.0,
                    "weight": weight,
                    "notes": _("Dữ liệu thông số chưa được xác thực (trạng thái: %s)") % cand_info["validation_status"],
                    "is_hard_constraint": is_hard,
                    "is_missing_profile_rule": is_missing_rule,
                })
                continue

            # Chuẩn hóa giá trị ứng viên
            cand_val, cand_ok, _msg = self.normalize_value(
                cand_info["raw_value"], data_type,
                uom_from=cand_info["uom"], uom_to=rule_uom
            )

            # Đánh giá so khớp theo quy tắc
            line_result = self._evaluate_spec_rule(rule, input_val, cand_val)
            line_status = line_result["line_status"]
            spec_score = line_result["score"]
            delta = line_result["delta"]
            notes = line_result["notes"]
            if is_missing_rule:
                notes = f"{notes} ({_('Chưa có quy tắc riêng trong hồ sơ')})"

            total_weight += weight
            achieved_weight += spec_score

            if line_status == "partial":
                has_partial_match_spec = True
            elif line_status == "mismatch":
                if is_hard:
                    violated_hard_constraints.append({
                        "spec_code": spec_code,
                        "spec_name": spec_name,
                        "input_val": input_val,
                        "candidate_val": cand_val,
                        "delta": delta,
                        "notes": notes,
                    })

            comparison_lines.append({
                "spec_code": spec_code,
                "spec_name": spec_name,
                "input_val": input_val,
                "candidate_val": cand_val,
                "delta": delta,
                "uom": rule_uom,
                "line_status": line_status,
                "score": spec_score,
                "weight": weight,
                "notes": notes,
                "is_hard_constraint": is_hard,
                "is_missing_profile_rule": is_missing_rule,
            })

        # =====================================================================
        # TỔNG HỢP TRẠNG THÁI CUỐI CÙNG THEO NGUYÊN TẮC AN TOÀN
        # =====================================================================
        min_threshold = profile.get("min_score_threshold", 80.0) if isinstance(profile, dict) else profile.min_score_threshold
        allow_partial = profile.get("allow_partial_match", True) if isinstance(profile, dict) else profile.allow_partial_match

        spec_match_score = (achieved_weight / total_weight * 100.0) if total_weight > 0 else 0.0

        # Kiểm tra xem đây có phải là tra cứu một phần (Partial Spec Query) không
        total_rules_count = len(combined_rules)
        is_partial_query = bool(
            (len(total_critical_codes) > 1 and len(evaluated_critical_codes) < len(total_critical_codes)) or
            (len(input_specs or {}) == 1 and total_rules_count > 1)
        )

        has_violations = bool(violated_hard_constraints)
        has_missing = bool(missing_critical_specs)

        # 1. Có vi phạm điều kiện bắt buộc -> MISMATCH
        # (Nếu đồng thời thiếu dữ liệu thì ghi nhận rõ cả 2 yếu tố, phân loại ưu tiên vi phạm)
        if has_violations:
            match_status = "mismatch"
            match_score = 0.0
            if has_missing:
                status_reason = _("Vi phạm %d điều kiện bắt buộc (Hard Constraints) và thiếu dữ liệu xác thực cho %d thông số cốt lõi") % (
                    len(violated_hard_constraints), len(missing_critical_specs)
                )
            else:
                status_reason = _("Vi phạm %d điều kiện bắt buộc (Hard Constraints)") % len(violated_hard_constraints)

        # 2. Thiếu thông số cốt lõi hoặc dữ liệu chưa xác thực -> INSUFFICIENT_DATA
        elif has_missing:
            match_status = "insufficient_data"
            match_score = 0.0
            spec_names_missing = ", ".join(m["spec_name"] for m in missing_critical_specs)
            if has_unverified_critical_data:
                status_reason = _("Chưa đủ dữ liệu xác thực: Chứa thông số cốt lõi chưa được duyệt (%s)") % spec_names_missing
            else:
                status_reason = _("Chưa đủ dữ liệu xác thực: Thiếu %d thông số cốt lõi cần thiết để kết luận kỹ thuật (%s)") % (
                    len(missing_critical_specs), spec_names_missing
                )

        # 3. Không có thông số nào được đánh giá -> INSUFFICIENT_DATA
        elif total_weight == 0:
            match_status = "insufficient_data"
            match_score = 0.0
            status_reason = _("Không có thông số nào được đối chiếu")

        # 4. Tra cứu một phần (query chưa cung cấp đủ toàn bộ thông số cốt lõi của profile) -> INSUFFICIENT_DATA
        elif is_partial_query:
            match_status = "insufficient_data"
            match_score = 0.0
            if evaluated_specs_count == 1:
                status_reason = _("Khớp thông số đã cung cấp; Chưa đủ dữ liệu để xác nhận tương thích tổng thể.")
            else:
                status_reason = _("Khớp thông số đã cung cấp (%d/%d thông số cốt lõi); Chưa đủ dữ liệu để xác nhận tương thích tổng thể.") % (
                    len(evaluated_critical_codes), len(total_critical_codes)
                )

        # 5. Đủ dữ liệu và đáp ứng toàn bộ điều kiện
        else:
            if not has_partial_match_spec and spec_match_score >= 99.9:
                match_status = "exact_match"
                match_score = 100.0
                status_reason = _("Khớp chính xác 100% tất cả thông số kỹ thuật đã đối chiếu")
            else:
                if allow_partial and spec_match_score >= min_threshold:
                    match_status = "partial_match"
                    match_score = spec_match_score
                    status_reason = _("Khớp trong dung sai kỹ thuật cho phép (Điểm: %.1f%%)") % spec_match_score
                else:
                    match_status = "mismatch"
                    match_score = 0.0
                    status_reason = _("Điểm kỹ thuật (%.1f%%) dưới ngưỡng cho phép (%.1f%%) hoặc không cấu hình partial match") % (spec_match_score, min_threshold)

        return {
            "candidate_id": candidate.id,
            "candidate_name": candidate.display_name,
            "candidate_code": candidate.default_code or "",
            "match_status": match_status,
            "compatibility_status": match_status,
            "match_score": round(match_score, 2),
            "spec_match_score": round(spec_match_score, 2),
            "status_reason": status_reason,
            "comparison_lines": comparison_lines,
            "violated_hard_constraints": violated_hard_constraints,
            "missing_critical_specs": missing_critical_specs,
            "has_unverified_data": has_unverified_critical_data,
            "has_violation": has_violations,
            "has_missing_data": has_missing,
            "total_weight": total_weight,
            "achieved_weight": achieved_weight,
            "is_partial_query": is_partial_query,
            "evaluated_critical_count": len(evaluated_critical_codes),
            "total_critical_count": len(total_critical_codes),
        }

    @api.model
    def _evaluate_spec_rule(self, rule, input_val, cand_val):
        """Đánh giá chi tiết 1 thông số theo quy tắc match_type, tolerance và substitution"""
        match_type = rule.get("match_type", "exact")
        weight = rule.get("weight", 10.0)

        # 1. So khớp Bắt buộc bằng tuyệt đối (exact)
        if match_type == "exact":
            if input_val == cand_val:
                return {
                    "line_status": "exact",
                    "score": weight,
                    "delta": 0,
                    "notes": _("Khớp chính xác"),
                }

            # Kiểm tra quy tắc cho phép thay thế kỹ thuật (substitute)
            if rule.get("allow_substitute"):
                raw_subs = [s.strip() for s in str(rule.get("substitute_values") or "").split(",") if s.strip()]
                is_sub = False
                cand_str = str(cand_val).strip()
                for s in raw_subs:
                    if cand_str.lower() == s.lower():
                        is_sub = True
                        break
                    try:
                        if isinstance(cand_val, (int, float)) and float(s) == float(cand_val):
                            is_sub = True
                            break
                    except (ValueError, TypeError):
                        pass

                if is_sub:
                    penalty = float(rule.get("penalty_per_unit", 1.0) or 0.0)
                    score = max(weight - penalty, weight * 0.8)
                    note = rule.get("substitute_note") or _("Thay thế hợp lệ theo quy tắc cấu hình")
                    return {
                        "line_status": "partial",
                        "score": score,
                        "delta": None,
                        "notes": note,
                    }

            return {
                "line_status": "mismatch",
                "score": 0.0,
                "delta": None,
                "notes": _("Giá trị khác nhau ('%s' != '%s')") % (input_val, cand_val),
            }

        # 2. So khớp theo Dung sai số học (tolerance)
        elif match_type == "tolerance":
            if not isinstance(input_val, (int, float)) or not isinstance(cand_val, (int, float)):
                # Nếu giá trị không phải số thì so sánh trực tiếp
                matched = (input_val == cand_val)
                return {
                    "line_status": "exact" if matched else "mismatch",
                    "score": weight if matched else 0.0,
                    "delta": 0 if matched else None,
                    "notes": _("Khớp chính xác") if matched else _("Không khớp"),
                }

            delta = round(cand_val - input_val, 4)
            if delta == 0.0:
                return {
                    "line_status": "exact",
                    "score": weight,
                    "delta": 0.0,
                    "notes": _("Khớp chính xác"),
                }

            tol_type = rule.get("tolerance_type", "absolute")
            tol_plus = float(rule.get("tolerance_plus", 0.0))
            tol_minus = float(rule.get("tolerance_minus", 0.0))

            is_within_tol = False
            max_allowed = 0.0

            if tol_type == "percent":
                pct_delta = (delta / input_val * 100.0) if input_val != 0 else 0.0
                is_within_tol = (-tol_minus <= pct_delta <= tol_plus)
                max_allowed = tol_plus if delta > 0 else tol_minus
            else:
                is_within_tol = (-tol_minus <= delta <= tol_plus)
                max_allowed = tol_plus if delta > 0 else tol_minus

            if is_within_tol:
                # Tính điểm trong khoảng dung sai
                penalty_ratio = (abs(delta) / max_allowed * 0.5) if max_allowed > 0 else 0.0
                penalty_fixed = abs(delta) * float(rule.get("penalty_per_unit", 0.0))
                score = max(weight * (1.0 - penalty_ratio) - penalty_fixed, weight * 0.5)

                return {
                    "line_status": "partial",
                    "score": round(score, 2),
                    "delta": delta,
                    "notes": _("Lệch %s trong khoảng dung sai (-%s / +%s)") % (delta, tol_minus, tol_plus),
                }
            else:
                return {
                    "line_status": "mismatch",
                    "score": 0.0,
                    "delta": delta,
                    "notes": _("Lệch %s vượt quá dung sai (-%s / +%s)") % (delta, tol_minus, tol_plus),
                }

        # 3. So khớp dạng khoảng giá trị (range)
        elif match_type == "range":
            tol_min = float(rule.get("tolerance_minus", 0.0) or 0.0)
            tol_max = float(rule.get("tolerance_plus", 0.0) or 0.0)
            if isinstance(cand_val, (int, float)):
                if tol_min <= cand_val <= tol_max:
                    return {
                        "line_status": "exact",
                        "score": weight,
                        "delta": 0.0,
                        "notes": _("Nằm trong khoảng cho phép [%s - %s]") % (tol_min, tol_max),
                    }
                else:
                    delta = round(tol_min - cand_val if cand_val < tol_min else cand_val - tol_max, 4)
                    return {
                        "line_status": "mismatch",
                        "score": 0.0,
                        "delta": delta,
                        "notes": _("Nằm ngoài khoảng cho phép [%s - %s]") % (tol_min, tol_max),
                    }
            matched = (input_val == cand_val)
            return {
                "line_status": "exact" if matched else "mismatch",
                "score": weight if matched else 0.0,
                "delta": 0 if matched else None,
                "notes": _("Khớp") if matched else _("Không khớp"),
            }

        # 4. So khớp dạng tập hợp (subset)
        elif match_type == "subset":
            in_str = str(input_val).lower()
            cand_str = str(cand_val).lower()
            if in_str in cand_str or cand_str in in_str:
                return {
                    "line_status": "exact" if in_str == cand_str else "partial",
                    "score": weight if in_str == cand_str else weight * 0.85,
                    "delta": 0,
                    "notes": _("Khớp tập hợp / chuỗi"),
                }
            return {
                "line_status": "mismatch",
                "score": 0.0,
                "delta": None,
                "notes": _("Không thuộc tập hợp"),
            }

        # Mặc định
        matched = (input_val == cand_val)
        return {
            "line_status": "exact" if matched else "mismatch",
            "score": weight if matched else 0.0,
            "delta": 0 if matched else None,
            "notes": _("Khớp") if matched else _("Không khớp"),
        }

    # =========================================================================
    # 5. RANKING (Xếp hạng các ứng viên đủ điều kiện)
    # =========================================================================

    @api.model
    def rank_candidates(self, evaluated_candidates, profile=None, options=None):
        """Xếp hạng các ứng viên:
        - Tách riêng danh sách đủ điều kiện (exact_match, partial_match) và không đủ điều kiện (mismatch, insufficient_data).
        - Sắp xếp thứ tự ưu tiên: exact_match -> partial_match -> điểm số kỹ thuật giảm dần.
        - Các tiêu chí phụ (tồn kho, giá) được giữ tách biệt và chỉ dùng làm thứ tự phụ nếu được yêu cầu.
        """
        options = options or {}
        eligible = []
        ineligible = []
        mismatch_list = []
        insufficient_list = []

        for cand in evaluated_candidates:
            st = cand.get("match_status")
            if st in ("exact_match", "partial_match"):
                eligible.append(cand)
            elif st == "mismatch":
                ineligible.append(cand)
                mismatch_list.append(cand)
            else:  # "insufficient_data"
                ineligible.append(cand)
                insufficient_list.append(cand)

        # Sắp xếp danh sách đủ điều kiện
        status_priority = {"exact_match": 1, "partial_match": 2}
        eligible.sort(
            key=lambda x: (
                status_priority.get(x["match_status"], 99),
                -x.get("match_score", 0.0),
            )
        )

        # Đánh số thứ tự hạng (Rank)
        for idx, item in enumerate(eligible, start=1):
            item["rank"] = idx

        # Sắp xếp danh sách chưa đủ dữ liệu theo spec_match_score giảm dần
        insufficient_list.sort(key=lambda x: -x.get("spec_match_score", 0.0))

        return {
            "ranked_matches": eligible,
            "rejected_candidates": ineligible,
            "mismatch_candidates": mismatch_list,
            "insufficient_candidates": insufficient_list,
            "total_evaluated": len(evaluated_candidates),
            "total_eligible": len(eligible),
        }

    # =========================================================================
    # 6. EXPLANATION (Bảng đối chiếu & Giải thích chi tiết)
    # =========================================================================

    @api.model
    def format_explanation(self, evaluated_candidate):
        """Tạo bảng giải thích đối chiếu HTML chi tiết cho một ứng viên (Đảm bảo an toàn XSS)"""
        status_badges = {
            "exact_match": "<span class='badge bg-success'>Khớp chính xác (Exact Match)</span>",
            "partial_match": "<span class='badge bg-warning text-dark'>Khớp tương đương (Partial Match)</span>",
            "mismatch": "<span class='badge bg-danger'>Không tương thích (Mismatch)</span>",
            "insufficient_data": "<span class='badge bg-secondary'>Chưa đủ dữ liệu xác thực (Insufficient Data)</span>",
        }

        is_partial = evaluated_candidate.get("is_partial_query", False)
        raw_status = str(evaluated_candidate.get("match_status") or "")
        cand_name = html_escape(str(evaluated_candidate.get("candidate_name") or ""))
        cand_code = html_escape(str(evaluated_candidate.get("candidate_code") or "N/A"))
        status_reason = html_escape(str(evaluated_candidate.get("status_reason") or ""))
        spec_score = evaluated_candidate.get("spec_match_score", evaluated_candidate.get("match_score", 0.0))
        match_score = evaluated_candidate.get("match_score", 0.0)

        if is_partial and raw_status == "insufficient_data":
            badge = "<span class='badge bg-secondary'>Chưa đủ dữ liệu xác thực (Insufficient Data)</span>"
            eval_c = evaluated_candidate.get("evaluated_critical_count", 1)
            tot_c = evaluated_candidate.get("total_critical_count", 1)
            points_sub = f"{status_reason} | Điểm thông số đã đối chiếu: <b>{spec_score}%</b> (Phạm vi: {eval_c}/{tot_c} thông số cốt lõi)"
        elif raw_status == "insufficient_data":
            badge = status_badges.get(raw_status, html_escape(raw_status))
            points_sub = f"{status_reason} | Điểm thông số đã đối chiếu: <b>{spec_score}%</b> (Chưa đủ điều kiện kết luận thay thế)"
        elif raw_status == "mismatch":
            badge = status_badges.get(raw_status, html_escape(raw_status))
            points_sub = f"{status_reason} | Điểm kỹ thuật: <b>0.0%</b> (Không tương thích)"
        else:
            badge = status_badges.get(raw_status, html_escape(raw_status))
            points_sub = f"{status_reason} | Điểm kỹ thuật: <b>{match_score}%</b>"

        html = [
            f"<div class='spec-matching-explanation mb-3 p-3 border rounded'>",
            f"  <h5>{cand_name} ({cand_code}) - {badge}</h5>",
            f"  <p class='text-muted small mb-2'>{points_sub}</p>",
            f"  <table class='table table-sm table-bordered align-middle'>",
            f"    <thead class='table-light'>",
            f"      <tr>",
            f"        <th>Thông số</th>",
            f"        <th>Yêu cầu</th>",
            f"        <th>Sản phẩm</th>",
            f"        <th>Độ lệch</th>",
            f"        <th>Đơn vị</th>",
            f"        <th>Đánh giá</th>",
            f"        <th>Ghi chú</th>",
            f"      </tr>",
            f"    </thead>",
            f"    <tbody>",
        ]

        for line in evaluated_candidate.get("comparison_lines", []):
            st = line["line_status"]
            if st == "exact":
                status_cell = "<span class='text-success fw-bold'>Khớp 100%</span>"
            elif st == "partial":
                status_cell = "<span class='text-warning fw-bold'>Trong dung sai</span>"
            elif st == "mismatch":
                status_cell = "<span class='text-danger fw-bold'>Không khớp</span>"
            elif st == "unverified_data":
                status_cell = "<span class='text-danger'>Chưa duyệt</span>"
            elif st == "skipped_missing":
                status_cell = "<span class='text-muted'>Không có số liệu</span>"
            elif st == "insufficient_data":
                status_cell = "<span class='text-secondary fw-bold'>Chưa xác minh</span>"
            else:
                status_cell = "<span class='text-danger fw-bold'>Thiếu số liệu (Bắt buộc)</span>"

            delta_str = html_escape(f"{line['delta']:+g}") if line.get("delta") is not None else "-"
            input_str = html_escape(str(line["input_val"])) if line.get("input_val") is not None else "-"
            cand_str = html_escape(str(line["candidate_val"])) if line.get("candidate_val") is not None else "<span class='text-muted'>Chưa có dữ liệu verified</span>"
            spec_name = html_escape(str(line.get("spec_name") or ""))
            uom_str = html_escape(str(line.get("uom") or ""))
            notes_str = html_escape(str(line.get("notes") or ""))
            hard_badge = '<span class="badge bg-danger ms-1">Bắt buộc</span>' if line.get("is_hard_constraint") else ''

            html.append(
                f"      <tr>"
                f"        <td><b>{spec_name}</b> {hard_badge}</td>"
                f"        <td>{input_str}</td>"
                f"        <td>{cand_str}</td>"
                f"        <td>{delta_str}</td>"
                f"        <td>{uom_str}</td>"
                f"        <td>{status_cell}</td>"
                f"        <td class='small'>{notes_str}</td>"
                f"      </tr>"
            )

        html.append("    </tbody>")
        html.append("  </table>")
        html.append("</div>")

        return "\n".join(html)

    # =========================================================================
    # 7. PUBLIC ENGINE API (Điểm gọi dịch vụ tích hợp cho toàn hệ thống)
    # =========================================================================

    @api.model
    def find_matching_products(self, category_id, input_specs, options=None):
        """API chính của Matching Engine:
        Nhận danh mục và thông số đầu vào -> Trả về danh sách ứng viên đã xếp hạng và giải thích chi tiết.
        100% READ-ONLY, không sửa đổi dữ liệu kinh doanh.
        Đo lường thời gian monotonic clock và tải theo lô EAV để triệt tiêu N+1 queries.
        """
        t_engine_start = time.perf_counter()
        options = options or {}
        category = self.env["product.category"].browse(category_id) if isinstance(category_id, int) else category_id
        if not category:
            return {
                "success": False,
                "error": _("Không tìm thấy danh mục sản phẩm"),
                "ranked_matches": [],
                "rejected_candidates": [],
                "timing": {
                    "retrieval_sec": 0.0,
                    "specs_load_sec": 0.0,
                    "eval_sec": 0.0,
                    "rank_explain_sec": 0.0,
                    "total_engine_sec": 0.0,
                },
            }

        # 1. Resolve Profile
        profile = self.resolve_profile(category)
        rules_count = len(profile.rule_ids) if hasattr(profile, "rule_ids") else len(profile.get("rule_dicts", []))
        if rules_count == 0:
            return {
                "success": False,
                "has_profile": False,
                "error": _("Danh mục '%s' hiện chưa có Hồ sơ so khớp kỹ thuật (Matching Profile) hoặc định nghĩa thông số để thực hiện so khớp thay thế.") % category.display_name,
                "category_id": category.id,
                "category_name": category.display_name,
                "profile_name": None,
                "retrieved_count": 0,
                "evaluated_count": 0,
                "compatible_count": 0,
                "insufficient_count": 0,
                "rejected_count": 0,
                "total_candidates": 0,
                "total_matches": 0,
                "ranked_matches": [],
                "rejected_candidates": [],
                "mismatch_candidates": [],
                "insufficient_candidates": [],
                "best_match": None,
                "explanation_html": f"<div class='alert alert-info py-2 mb-2'><strong>{_('Thông báo:')}</strong> {_('Danh mục')} <b>{html_escape(category.display_name)}</b> {_('chưa được cấu hình Hồ sơ so khớp kỹ thuật (Matching Profile). Vui lòng cấu hình thông số và quy tắc tại Cấu hình > Hồ sơ so khớp trước khi thực hiện tra cứu thay thế kỹ thuật.')}</div>",
                "timing": {
                    "retrieval_sec": 0.0,
                    "specs_load_sec": 0.0,
                    "eval_sec": 0.0,
                    "rank_explain_sec": 0.0,
                    "total_engine_sec": round(time.perf_counter() - t_engine_start, 4),
                },
            }

        # 2. Candidate Retrieval
        t0 = time.perf_counter()
        candidates = self.retrieve_candidates(
            category.id,
            input_specs=input_specs,
            profile=profile,
            domain=options.get("domain"),
            limit=options.get("limit", 100),
        )
        t_retrieval = time.perf_counter() - t0

        # 3. Batch Loading EAV Specs (N+1 Elimination)
        t1 = time.perf_counter()
        cand_specs_by_id = {}
        if candidates:
            all_spec_values = self.env["qba.product.spec.value"].search([
                ("product_tmpl_id", "in", candidates.ids),
            ])
            for val_rec in all_spec_values:
                if not val_rec.spec_definition_id or not val_rec.spec_definition_id.active:
                    continue
                pid = val_rec.product_tmpl_id.id
                if pid not in cand_specs_by_id:
                    cand_specs_by_id[pid] = {}
                cand_specs_by_id[pid][val_rec.spec_code] = {
                    "val_rec": val_rec,
                    "validation_status": val_rec.validation_status,
                    "is_verified": val_rec.validation_status == "verified",
                    "raw_value": self._get_typed_spec_value(val_rec),
                    "uom": val_rec.uom,
                    "data_type": val_rec.data_type,
                }
        t_specs_load = time.perf_counter() - t1

        # 4. Evaluate từng candidate (sử dụng preloaded specs map)
        t2 = time.perf_counter()
        evaluated_list = []
        for cand in candidates:
            preloaded = cand_specs_by_id.get(cand.id, {})
            eval_res = self.evaluate_candidate(
                cand, input_specs, profile,
                category=category,
                preloaded_specs_map=preloaded
            )
            evaluated_list.append(eval_res)
        t_eval = time.perf_counter() - t2

        # 5. Rank candidates & format HTML explanations
        t3 = time.perf_counter()
        ranked_res = self.rank_candidates(evaluated_list, profile=profile, options=options)
        html_explanations = []
        for match in ranked_res["ranked_matches"]:
            html_explanations.append(self.format_explanation(match))
        if not ranked_res["ranked_matches"] and ranked_res.get("insufficient_candidates"):
            for match in ranked_res["insufficient_candidates"][:5]:
                html_explanations.append(self.format_explanation(match))
        t_rank_explain = time.perf_counter() - t3

        engine_timing = {
            "retrieval_sec": round(t_retrieval, 4),
            "specs_load_sec": round(t_specs_load, 4),
            "eval_sec": round(t_eval, 4),
            "rank_explain_sec": round(t_rank_explain, 4),
            "total_engine_sec": round(time.perf_counter() - t_engine_start, 4),
        }

        retrieved_count = len(candidates)
        evaluated_count = ranked_res["total_evaluated"]
        compatible_count = ranked_res["total_eligible"]
        insufficient_count = len(ranked_res.get("insufficient_candidates", []))
        rejected_count = len(ranked_res.get("mismatch_candidates", []))

        return {
            "success": True,
            "has_profile": True,
            "category_id": category.id,
            "category_name": category.display_name,
            "profile_name": profile.get("name") if isinstance(profile, dict) else profile.name,
            "retrieved_count": retrieved_count,
            "evaluated_count": evaluated_count,
            "compatible_count": compatible_count,
            "insufficient_count": insufficient_count,
            "rejected_count": rejected_count,
            "total_candidates": evaluated_count,
            "total_matches": compatible_count,
            "ranked_matches": ranked_res["ranked_matches"],
            "rejected_candidates": ranked_res["rejected_candidates"],
            "mismatch_candidates": ranked_res.get("mismatch_candidates", []),
            "insufficient_candidates": ranked_res.get("insufficient_candidates", []),
            "best_match": ranked_res["ranked_matches"][0] if ranked_res["ranked_matches"] else None,
            "explanation_html": "\n".join(html_explanations),
            "timing": engine_timing,
        }

    @api.model
    def match_product_to_candidates(self, product_id, domain=None, options=None):
        """Tìm sản phẩm phụ tùng thay thế kỹ thuật cho một sản phẩm có sẵn trong kho.
        Tự động đọc thông số verified của sản phẩm nguồn -> gọi matching engine.
        """
        product = self.env["product.template"].browse(product_id) if isinstance(product_id, int) else product_id
        if not product or not product.categ_id:
            return {"success": False, "error": _("Sản phẩm không tồn tại hoặc chưa phân loại danh mục")}

        # Đọc thông số verified của sản phẩm nguồn
        input_specs = {}
        for val in product.spec_value_ids:
            if val.validation_status == "verified" and val.spec_definition_id.active:
                typed_val = self._get_typed_spec_value(val)
                if typed_val is not None:
                    input_specs[val.spec_code] = {
                        "value": typed_val,
                        "uom": val.uom,
                    }

        # Loại trừ chính sản phẩm nguồn khỏi danh sách ứng viên
        filter_domain = [("id", "!=", product.id)]
        if domain:
            filter_domain += domain

        opts = dict(options or {})
        opts["domain"] = filter_domain

        return self.find_matching_products(product.categ_id.id, input_specs, options=opts)

    # =========================================================================
    # CÁC HÀM TIỆN ÍCH TRỢ GIÚP NỘI BỘ
    # =========================================================================

    @api.model
    def _get_typed_spec_value(self, val_rec):
        """Lấy giá trị đúng kiểu chuẩn từ bản ghi qba.product.spec.value"""
        dtype = val_rec.data_type
        if dtype == "float":
            return val_rec.value_float
        elif dtype == "integer":
            return val_rec.value_integer
        elif dtype == "boolean":
            return val_rec.value_boolean
        else:
            return val_rec.value_char or val_rec.value_display

    @api.model
    def _get_rules_from_profile(self, profile):
        """Trích xuất danh sách rules dạng dict chuẩn hóa từ profile record hoặc inferred dict"""
        if isinstance(profile, dict):
            return profile.get("rule_dicts", [])

        rules_list = []
        for r in profile.rule_ids:
            if not getattr(r, "active", True) or not r.spec_definition_id or not r.spec_definition_id.active:
                continue
            rules_list.append({
                "spec_definition_id": r.spec_definition_id.id,
                "spec_code": r.spec_code,
                "spec_name": r.spec_name,
                "data_type": r.data_type,
                "uom": r.uom,
                "match_type": r.match_type,
                "is_hard_constraint": r.is_hard_constraint or r.spec_definition_id.is_critical,
                "tolerance_type": r.tolerance_type,
                "tolerance_plus": r.tolerance_plus,
                "tolerance_minus": r.tolerance_minus,
                "weight": r.weight,
                "penalty_per_unit": r.penalty_per_unit,
                "allow_substitute": r.allow_substitute,
                "substitute_values": r.substitute_values,
                "substitute_note": r.substitute_note,
            })
        return rules_list

