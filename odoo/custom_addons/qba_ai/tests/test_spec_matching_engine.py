# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, AccessError


class TestSpecMatchingEngine(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.engine = cls.env["qba.spec.matching.engine"]

        # Nhóm quyền
        cls.group_ai_user = cls.env.ref("qba_ai.group_qba_ai_user")
        cls.group_ai_manager = cls.env.ref("qba_ai.group_qba_ai_manager")

        cls.user_normal = cls.env["res.users"].create({
            "name": "Normal AI Match User",
            "login": "normal_ai_match_user",
            "email": "normal_ai_match@example.com",
            "groups_id": [(6, 0, [cls.env.ref("base.group_user").id, cls.group_ai_user.id])],
        })

        cls.user_ai_admin = cls.env["res.users"].create({
            "name": "Admin AI Match Manager",
            "login": "admin_ai_match_manager",
            "email": "admin_ai_match@example.com",
            "groups_id": [(6, 0, [cls.env.ref("base.group_user").id, cls.group_ai_manager.id])],
        })

        # Danh mục thử nghiệm 1: Lá Côn (LC)
        cls.categ_lc = cls.env["product.category"].search([("name", "ilike", "LC")], limit=1)
        if not cls.categ_lc:
            cls.categ_lc = cls.env["product.category"].create({"name": "LC - Lá côn"})

        # Danh mục thử nghiệm 2: Tăm Bua (TBUA)
        cls.categ_tbua = cls.env["product.category"].search([("name", "ilike", "TBUA")], limit=1)
        if not cls.categ_tbua:
            cls.categ_tbua = cls.env["product.category"].create({"name": "TBUA - Tăm bua"})

        # Thông số kỹ thuật cho LC
        cls.spec_lc_diam = cls._get_or_create_spec("match_lc_outer_diam", "Đường kính ngoài LC", "float", "mm", [cls.categ_lc.id], True)
        cls.spec_lc_teeth = cls._get_or_create_spec("match_lc_teeth", "Số răng moay ơ LC", "integer", "răng", [cls.categ_lc.id], True)
        cls.spec_lc_hub_c = cls._get_or_create_spec("match_lc_hub_c", "Đường kính moay ơ C", "float", "mm", [cls.categ_lc.id], True)
        cls.spec_lc_springs = cls._get_or_create_spec("match_lc_springs", "Số lò xo LC", "integer", "lò xo", [cls.categ_lc.id], False)

        # Thông số kỹ thuật cho TBUA
        cls.spec_tbua_diam = cls._get_or_create_spec("match_tbua_inner_diam", "Đường kính lòng tăm bua", "float", "mm", [cls.categ_tbua.id], True)
        cls.spec_tbua_holes = cls._get_or_create_spec("match_tbua_holes", "Số lỗ tắc kê", "integer", "lỗ", [cls.categ_tbua.id], True)
        cls.spec_tbua_height = cls._get_or_create_spec("match_tbua_height", "Chiều cao bát phanh", "float", "mm", [cls.categ_tbua.id], False)

        # Profile cấu hình so khớp cho danh mục LC
        cls.profile_lc = cls.env["qba.category.matching.profile"].search([("category_id", "=", cls.categ_lc.id)], limit=1)
        if not cls.profile_lc:
            cls.profile_lc = cls.env["qba.category.matching.profile"].create({
                "name": "Profile So Khớp Lá Côn",
                "category_id": cls.categ_lc.id,
                "min_score_threshold": 80.0,
                "allow_partial_match": True,
            })
        else:
            cls.profile_lc.write({
                "min_score_threshold": 80.0,
                "allow_partial_match": True,
            })
            cls.profile_lc.rule_ids.unlink()

        cls.env["qba.category.matching.rule"].create([
            {
                "profile_id": cls.profile_lc.id,
                "spec_definition_id": cls.spec_lc_diam.id,
                "match_type": "tolerance",
                "tolerance_type": "absolute",
                "tolerance_plus": 1.0,
                "tolerance_minus": 1.0,
                "weight": 35.0,
                "is_hard_constraint": True,
            },
            {
                "profile_id": cls.profile_lc.id,
                "spec_definition_id": cls.spec_lc_teeth.id,
                "match_type": "exact",
                "weight": 35.0,
                "is_hard_constraint": True,
            },
            {
                "profile_id": cls.profile_lc.id,
                "spec_definition_id": cls.spec_lc_hub_c.id,
                "match_type": "exact",
                "weight": 20.0,
                "is_hard_constraint": True,
                "allow_substitute": True,
                "substitute_values": "31, 31.5",
                "substitute_note": "Cho phép thay thế Moay ơ 31.5 trong tiêu chuẩn nhà sản xuất",
            },
            {
                "profile_id": cls.profile_lc.id,
                "spec_definition_id": cls.spec_lc_springs.id,
                "match_type": "exact",
                "weight": 10.0,
                "is_hard_constraint": False,
            },
        ])

        # Profile cấu hình so khớp cho danh mục TBUA
        cls.profile_tbua = cls.env["qba.category.matching.profile"].search([("category_id", "=", cls.categ_tbua.id)], limit=1)
        if not cls.profile_tbua:
            cls.profile_tbua = cls.env["qba.category.matching.profile"].create({
                "name": "Profile So Khớp Tăm Bua",
                "category_id": cls.categ_tbua.id,
                "min_score_threshold": 85.0,
                "allow_partial_match": True,
            })
        else:
            cls.profile_tbua.write({
                "min_score_threshold": 85.0,
                "allow_partial_match": True,
            })
            cls.profile_tbua.rule_ids.unlink()

        cls.env["qba.category.matching.rule"].create([
            {
                "profile_id": cls.profile_tbua.id,
                "spec_definition_id": cls.spec_tbua_diam.id,
                "match_type": "tolerance",
                "tolerance_plus": 0.5,
                "tolerance_minus": 0.5,
                "weight": 50.0,
                "is_hard_constraint": True,
            },
            {
                "profile_id": cls.profile_tbua.id,
                "spec_definition_id": cls.spec_tbua_holes.id,
                "match_type": "exact",
                "weight": 50.0,
                "is_hard_constraint": True,
            },
        ])

        # Dữ liệu sản phẩm mẫu LC
        # 1. Sản phẩm tham chiếu (gốc)
        cls.prod_lc_base = cls._create_product("Lá Côn Howo 325 Gốc", "TEST-LC-BASE", cls.categ_lc.id, 1500000.0)
        cls._set_spec(cls.prod_lc_base, cls.spec_lc_diam, "325.0", 325.0, "verified")
        cls._set_spec(cls.prod_lc_base, cls.spec_lc_teeth, "10", 10, "verified")
        cls._set_spec(cls.prod_lc_base, cls.spec_lc_hub_c, "31.0", 31.0, "verified")
        cls._set_spec(cls.prod_lc_base, cls.spec_lc_springs, "6", 6, "verified")

        # 2. Sản phẩm Exact Match
        cls.prod_lc_exact = cls._create_product("Lá Côn Dongfeng 325 Chuẩn", "TEST-LC-EXACT", cls.categ_lc.id, 1450000.0)
        cls._set_spec(cls.prod_lc_exact, cls.spec_lc_diam, "325.0", 325.0, "verified")
        cls._set_spec(cls.prod_lc_exact, cls.spec_lc_teeth, "10", 10, "verified")
        cls._set_spec(cls.prod_lc_exact, cls.spec_lc_hub_c, "31.0", 31.0, "verified")
        cls._set_spec(cls.prod_lc_exact, cls.spec_lc_springs, "6", 6, "verified")

        # 3. Sản phẩm Partial Match (đường kính 325.5 lệch +0.5mm nằm trong dung sai ±1.0mm)
        cls.prod_lc_partial = cls._create_product("Lá Côn Faw 325.5 Lệch Nhẹ", "TEST-LC-PARTIAL", cls.categ_lc.id, 1400000.0)
        cls._set_spec(cls.prod_lc_partial, cls.spec_lc_diam, "325.5", 325.5, "verified")
        cls._set_spec(cls.prod_lc_partial, cls.spec_lc_teeth, "10", 10, "verified")
        cls._set_spec(cls.prod_lc_partial, cls.spec_lc_hub_c, "31.0", 31.0, "verified")
        cls._set_spec(cls.prod_lc_partial, cls.spec_lc_springs, "6", 6, "verified")

        # 4. Sản phẩm Mismatch do vượt dung sai đường kính (328.0 lệch 3.0mm > 1.0mm)
        cls.prod_lc_mismatch_tol = cls._create_product("Lá Côn 328 Sai Đường Kính", "TEST-LC-MISMATCH-TOL", cls.categ_lc.id, 1300000.0)
        cls._set_spec(cls.prod_lc_mismatch_tol, cls.spec_lc_diam, "328.0", 328.0, "verified")
        cls._set_spec(cls.prod_lc_mismatch_tol, cls.spec_lc_teeth, "10", 10, "verified")
        cls._set_spec(cls.prod_lc_mismatch_tol, cls.spec_lc_hub_c, "31.0", 31.0, "verified")

        # 5. Sản phẩm Mismatch do sai số răng moay ơ (14 răng != 10 răng bắt buộc)
        cls.prod_lc_mismatch_teeth = cls._create_product("Lá Côn 325 14 Răng", "TEST-LC-MISMATCH-TEETH", cls.categ_lc.id, 1350000.0)
        cls._set_spec(cls.prod_lc_mismatch_teeth, cls.spec_lc_diam, "325.0", 325.0, "verified")
        cls._set_spec(cls.prod_lc_mismatch_teeth, cls.spec_lc_teeth, "14", 14, "verified")
        cls._set_spec(cls.prod_lc_mismatch_teeth, cls.spec_lc_hub_c, "31.0", 31.0, "verified")

        # 6. Sản phẩm Insufficient Data (thiếu moay ơ C bắt buộc)
        cls.prod_lc_missing_spec = cls._create_product("Lá Côn Thiếu Moay Ơ C", "TEST-LC-MISSING-HUB", cls.categ_lc.id, 1200000.0)
        cls._set_spec(cls.prod_lc_missing_spec, cls.spec_lc_diam, "325.0", 325.0, "verified")
        cls._set_spec(cls.prod_lc_missing_spec, cls.spec_lc_teeth, "10", 10, "verified")

        # 7. Sản phẩm Unverified Data (có thông số đúng nhưng chưa được Quản trị viên duyệt)
        cls.prod_lc_unverified = cls._create_product("Lá Côn Chưa Duyệt Thông Số", "TEST-LC-UNVERIFIED", cls.categ_lc.id, 1250000.0)
        cls._set_spec(cls.prod_lc_unverified, cls.spec_lc_diam, "325.0", 325.0, "unverified")
        cls._set_spec(cls.prod_lc_unverified, cls.spec_lc_teeth, "10", 10, "unverified")
        cls._set_spec(cls.prod_lc_unverified, cls.spec_lc_hub_c, "31.0", 31.0, "unverified")

        # Dữ liệu sản phẩm mẫu TBUA
        cls.prod_tbua_exact = cls._create_product("Tăm Bua Sau Howo 420 10 Lỗ", "TEST-TBUA-EXACT", cls.categ_tbua.id, 2500000.0)
        cls._set_spec(cls.prod_tbua_exact, cls.spec_tbua_diam, "420.0", 420.0, "verified")
        cls._set_spec(cls.prod_tbua_exact, cls.spec_tbua_holes, "10", 10, "verified")

        cls.prod_tbua_mismatch = cls._create_product("Tăm Bua Sau 420 8 Lỗ", "TEST-TBUA-MISMATCH", cls.categ_tbua.id, 2400000.0)
        cls._set_spec(cls.prod_tbua_mismatch, cls.spec_tbua_diam, "420.0", 420.0, "verified")
        cls._set_spec(cls.prod_tbua_mismatch, cls.spec_tbua_holes, "8", 8, "verified")

    @classmethod
    def _get_or_create_spec(cls, code, name, data_type, uom, category_ids, is_critical):
        spec = cls.env["qba.product.spec.definition"].with_context(active_test=False).search([("code", "=", code)], limit=1)
        if not spec:
            spec = cls.env["qba.product.spec.definition"].create({
                "name": name,
                "code": code,
                "data_type": data_type,
                "uom": uom,
                "category_ids": [(6, 0, category_ids)],
                "is_critical": is_critical,
                "active": True,
            })
        else:
            spec.write({
                "name": name,
                "data_type": data_type,
                "uom": uom,
                "category_ids": [(6, 0, category_ids)],
                "is_critical": is_critical,
                "active": True,
            })
        return spec

    @classmethod
    def _create_product(cls, name, code, categ_id, price):
        return cls.env["product.template"].create({
            "name": name,
            "default_code": code,
            "categ_id": categ_id,
            "list_price": price,
            "standard_price": price * 0.8,
        })

    @classmethod
    def _set_spec(cls, prod, spec_def, val_display, typed_val, status):
        vals = {
            "product_tmpl_id": prod.id,
            "spec_definition_id": spec_def.id,
            "value_display": val_display,
            "validation_status": status,
        }
        if spec_def.data_type == "float":
            vals["value_float"] = float(typed_val)
        elif spec_def.data_type == "integer":
            vals["value_integer"] = int(typed_val)
        elif spec_def.data_type == "boolean":
            vals["value_boolean"] = bool(typed_val)
        else:
            vals["value_char"] = str(typed_val)

        return cls.env["qba.product.spec.value"].create(vals)

    # =========================================================================
    # CÁC TEST CASES ĐA DANH MỤC PHASE 4.1
    # =========================================================================

    def test_01_exact_match(self):
        """1. Kiểm tra Exact Match: Khớp 100% tất cả thông số verified.
        Sản phẩm đáp ứng điểm số 100.0, được xếp hạng đầu tiên.
        """
        input_specs = {
            "match_lc_outer_diam": 325.0,
            "match_lc_teeth": 10,
            "match_lc_hub_c": 31.0,
            "match_lc_springs": 6,
        }
        res = self.engine.find_matching_products(self.categ_lc.id, input_specs)
        self.assertTrue(res["success"])
        self.assertTrue(res["total_matches"] >= 2)

        # Ứng viên prod_lc_exact phải đạt exact_match và điểm 100%
        cand_exact = next(m for m in res["ranked_matches"] if m["candidate_id"] == self.prod_lc_exact.id)
        self.assertEqual(cand_exact["match_status"], "exact_match")
        self.assertEqual(cand_exact["match_score"], 100.0)
        self.assertFalse(cand_exact["violated_hard_constraints"])
        self.assertFalse(cand_exact["missing_critical_specs"])

    def test_02_violate_hard_constraint_mismatch(self):
        """2. Vi phạm thông số bắt buộc (Hard Constraint):
        - Sai số răng moay ơ (14 vs 10 bắt buộc) -> Mismatch, điểm = 0.
        - Sai đường kính vượt dung sai (328.0 vs 325.0, tol ±1.0) -> Mismatch, điểm = 0.
        - Điểm số từ thông số khác không thể bù trừ cho hard constraint bị vi phạm.
        """
        input_specs = {
            "match_lc_outer_diam": 325.0,
            "match_lc_teeth": 10,
            "match_lc_hub_c": 31.0,
        }
        res = self.engine.find_matching_products(self.categ_lc.id, input_specs)

        # Kiểm tra sản phẩm sai số răng
        cand_teeth = next(c for c in res["rejected_candidates"] if c["candidate_id"] == self.prod_lc_mismatch_teeth.id)
        self.assertEqual(cand_teeth["match_status"], "mismatch")
        self.assertEqual(cand_teeth["match_score"], 0.0)
        self.assertTrue(len(cand_teeth["violated_hard_constraints"]) >= 1)
        self.assertEqual(cand_teeth["violated_hard_constraints"][0]["spec_code"], "match_lc_teeth")

        # Kiểm tra sản phẩm vượt dung sai đường kính
        cand_tol = next(c for c in res["rejected_candidates"] if c["candidate_id"] == self.prod_lc_mismatch_tol.id)
        self.assertEqual(cand_tol["match_status"], "mismatch")
        self.assertEqual(cand_tol["match_score"], 0.0)
        self.assertTrue(any(v["spec_code"] == "match_lc_outer_diam" for v in cand_tol["violated_hard_constraints"]))

    def test_03_partial_match_within_tolerance_and_substitution(self):
        """3. Partial match có cấu hình hợp lệ:
        - Độ lệch +0.5mm nằm trong dung sai cho phép ±1.0mm -> partial_match.
        - Giá trị moay ơ thay thế 31.5 hợp lệ theo cấu hình -> partial_match.
        """
        input_specs = {
            "match_lc_outer_diam": 325.0,
            "match_lc_teeth": 10,
            "match_lc_hub_c": 31.0,
        }
        res = self.engine.find_matching_products(self.categ_lc.id, input_specs)

        # prod_lc_partial có đường kính 325.5 (lệch +0.5mm)
        cand_partial = next(m for m in res["ranked_matches"] if m["candidate_id"] == self.prod_lc_partial.id)
        self.assertEqual(cand_partial["match_status"], "partial_match")
        self.assertTrue(cand_partial["match_score"] >= 80.0)
        self.assertFalse(cand_partial["violated_hard_constraints"])

        # Kiểm tra thay thế hợp lệ (allow_substitute)
        prod_sub = self._create_product("Lá Côn Moay Ơ 31.5 Thay Thế", "TEST-LC-SUB", self.categ_lc.id, 1400000.0)
        self._set_spec(prod_sub, self.spec_lc_diam, "325.0", 325.0, "verified")
        self._set_spec(prod_sub, self.spec_lc_teeth, "10", 10, "verified")
        self._set_spec(prod_sub, self.spec_lc_hub_c, "31.5", 31.5, "verified")

        eval_sub = self.engine.evaluate_candidate(prod_sub, input_specs, self.profile_lc)
        self.assertEqual(eval_sub["match_status"], "partial_match")
        self.assertFalse(eval_sub["violated_hard_constraints"])

    def test_04_partial_match_disabled_or_below_threshold(self):
        """4. Partial match không có quy tắc cho phép hoặc bị tắt:
        - Khi Profile đặt allow_partial_match = False -> sản phẩm lệch dung sai bị từ chối thành mismatch.
        - Khi điểm số dưới min_score_threshold -> chuyển thành mismatch.
        """
        input_specs = {
            "match_lc_outer_diam": 325.0,
            "match_lc_teeth": 10,
            "match_lc_hub_c": 31.0,
        }
        # Tắt allow_partial_match
        self.profile_lc.allow_partial_match = False
        res = self.engine.find_matching_products(self.categ_lc.id, input_specs)

        cand_partial = next(c for c in res["rejected_candidates"] if c["candidate_id"] == self.prod_lc_partial.id)
        self.assertEqual(cand_partial["match_status"], "mismatch")

        # Khôi phục lại
        self.profile_lc.allow_partial_match = True

    def test_05_insufficient_data(self):
        """5. Insufficient Data: Thiếu thông số cốt lõi/bắt buộc:
        - Ứng viên thiếu thông số hub_c -> Trạng thái 'insufficient_data', điểm = 0.
        - Không tự động suy diễn khả năng tương thích khi thiếu dữ liệu.
        """
        input_specs = {
            "match_lc_outer_diam": 325.0,
            "match_lc_teeth": 10,
            "match_lc_hub_c": 31.0,
        }
        res = self.engine.find_matching_products(self.categ_lc.id, input_specs)

        cand_missing = next(c for c in res["rejected_candidates"] if c["candidate_id"] == self.prod_lc_missing_spec.id)
        self.assertEqual(cand_missing["match_status"], "insufficient_data")
        self.assertEqual(cand_missing["match_score"], 0.0)
        self.assertTrue(len(cand_missing["missing_critical_specs"]) >= 1)

    def test_06_unverified_and_conflicted_data_protection(self):
        """6. Quy tắc an toàn: Dữ liệu unverified hoặc conflicted KHÔNG ĐƯỢC khẳng định tương thích kỹ thuật.
        Sản phẩm có giá trị đúng 100% nhưng chưa được Quản trị viên duyệt (validation_status='unverified')
        phải nhận trạng thái 'insufficient_data', không được kết luận exact_match hay partial_match.
        """
        input_specs = {
            "match_lc_outer_diam": 325.0,
            "match_lc_teeth": 10,
            "match_lc_hub_c": 31.0,
        }
        eval_unverified = self.engine.evaluate_candidate(self.prod_lc_unverified, input_specs, self.profile_lc)
        self.assertEqual(eval_unverified["match_status"], "insufficient_data")
        self.assertEqual(eval_unverified["match_score"], 0.0)
        self.assertTrue(eval_unverified["has_unverified_data"])

        # Kiểm tra trường hợp conflicted
        prod_conflict = self._create_product("Lá Côn Xung Đột", "TEST-LC-CONFLICT", self.categ_lc.id, 1200000.0)
        self._set_spec(prod_conflict, self.spec_lc_diam, "325.0", 325.0, "verified")
        self._set_spec(prod_conflict, self.spec_lc_teeth, "10", 10, "conflicted")
        self._set_spec(prod_conflict, self.spec_lc_hub_c, "31.0", 31.0, "verified")

        eval_conflict = self.engine.evaluate_candidate(prod_conflict, input_specs, self.profile_lc)
        self.assertEqual(eval_conflict["match_status"], "insufficient_data")
        self.assertTrue(eval_conflict["has_unverified_data"])

    def test_07_unit_conversion_normalization(self):
        """7. Chuẩn hóa đơn vị đo (Unit Conversion):
        Input '32.5 cm' đối chiếu với sản phẩm '325 mm' -> Tự động chuyển đổi sang mm và khớp chính xác.
        """
        # Input bằng cm
        val_norm, ok, _msg = self.engine.normalize_value(32.5, "float", uom_from="cm", uom_to="mm")
        self.assertTrue(ok)
        self.assertEqual(val_norm, 325.0)

        # Thử nghiệm so khớp với input có uom dạng dict
        input_specs = {
            "match_lc_outer_diam": {"value": 32.5, "uom": "cm"},
            "match_lc_teeth": 10,
            "match_lc_hub_c": 31.0,
        }
        eval_res = self.engine.evaluate_candidate(self.prod_lc_exact, input_specs, self.profile_lc)
        diam_line = next(l for l in eval_res["comparison_lines"] if l["spec_code"] == "match_lc_outer_diam")
        self.assertEqual(diam_line["line_status"], "exact")
        self.assertEqual(diam_line["input_val"], 325.0)
        self.assertEqual(diam_line["candidate_val"], 325.0)

    def test_08_empty_candidates_and_category_isolation(self):
        """8. Danh mục khác (TBUA) hoặc không có ứng viên:
        - So khớp TBUA độc lập với LC.
        - Không có ứng viên nào khớp -> Trả về danh sách rỗng an toàn, không bị lỗi hệ thống.
        """
        # So khớp TBUA
        input_tbua = {
            "match_tbua_inner_diam": 420.0,
            "match_tbua_holes": 10,
        }
        res_tbua = self.engine.find_matching_products(self.categ_tbua.id, input_tbua)
        self.assertTrue(res_tbua["success"])
        self.assertEqual(res_tbua["total_matches"], 1)
        self.assertEqual(res_tbua["ranked_matches"][0]["candidate_id"], self.prod_tbua_exact.id)

        # Ứng viên 8 lỗ bị Mismatch
        cand_8holes = next(c for c in res_tbua["rejected_candidates"] if c["candidate_id"] == self.prod_tbua_mismatch.id)
        self.assertEqual(cand_8holes["match_status"], "mismatch")

        # Thử nghiệm thông số không tưởng -> Không có ứng viên nào
        res_empty = self.engine.find_matching_products(self.categ_tbua.id, {"match_tbua_inner_diam": 999.0, "match_tbua_holes": 50})
        self.assertEqual(res_empty["total_matches"], 0)
        self.assertIsNone(res_empty["best_match"])

    def test_09_pure_readonly_guarantee(self):
        """9. Tính chất thuần chỉ đọc (Pure Read-Only):
        Matching Engine tuyệt đối không làm thay đổi giá niêm yết, giá vốn, mã SKU, tên, hoặc thông số sản phẩm.
        """
        orig_name = self.prod_lc_exact.name
        orig_code = self.prod_lc_exact.default_code
        orig_price = self.prod_lc_exact.list_price
        orig_cost = self.prod_lc_exact.standard_price
        orig_specs_count = len(self.prod_lc_exact.spec_value_ids)

        # Chạy engine nhiều lần
        input_specs = {"match_lc_outer_diam": 325.0, "match_lc_teeth": 10, "match_lc_hub_c": 31.0}
        self.engine.find_matching_products(self.categ_lc.id, input_specs)
        self.engine.match_product_to_candidates(self.prod_lc_base.id)

        self.prod_lc_exact.invalidate_recordset()
        self.assertEqual(self.prod_lc_exact.name, orig_name)
        self.assertEqual(self.prod_lc_exact.default_code, orig_code)
        self.assertEqual(self.prod_lc_exact.list_price, orig_price)
        self.assertEqual(self.prod_lc_exact.standard_price, orig_cost)
        self.assertEqual(len(self.prod_lc_exact.spec_value_ids), orig_specs_count)

    def test_10_dynamic_new_category_without_core_modification(self):
        """10. Thêm danh mục mới hoàn toàn qua cấu hình (ví dụ: Bi Moay Ơ - BEARING) mà không sửa 1 dòng code Core.
        Hệ thống tự động tra cứu Profile và so khớp chuẩn xác.
        """
        # Tạo danh mục mới
        categ_bearing = self.env["product.category"].create({"name": "BEARING - Vòng bi moay ơ"})

        # Tạo thông số mới
        spec_inner_d = self.env["qba.product.spec.definition"].create({
            "name": "Đường kính trong vòng bi",
            "code": "bearing_inner_d",
            "data_type": "float",
            "uom": "mm",
            "category_ids": [(6, 0, [categ_bearing.id])],
            "is_critical": True,
        })
        spec_outer_d = self.env["qba.product.spec.definition"].create({
            "name": "Đường kính ngoài vòng bi",
            "code": "bearing_outer_d",
            "data_type": "float",
            "uom": "mm",
            "category_ids": [(6, 0, [categ_bearing.id])],
            "is_critical": True,
        })

        # Tạo Profile mới
        profile_bearing = self.env["qba.category.matching.profile"].create({
            "name": "Profile Vòng Bi Moay Ơ",
            "category_id": categ_bearing.id,
            "min_score_threshold": 80.0,
            "allow_partial_match": True,
        })
        self.env["qba.category.matching.rule"].create([
            {
                "profile_id": profile_bearing.id,
                "spec_definition_id": spec_inner_d.id,
                "match_type": "exact",
                "weight": 50.0,
                "is_hard_constraint": True,
            },
            {
                "profile_id": profile_bearing.id,
                "spec_definition_id": spec_outer_d.id,
                "match_type": "tolerance",
                "tolerance_plus": 0.2,
                "tolerance_minus": 0.2,
                "weight": 50.0,
                "is_hard_constraint": True,
            },
        ])

        # Tạo sản phẩm vòng bi
        prod_b1 = self._create_product("Vòng Bi Koyo 32215", "BEARING-01", categ_bearing.id, 450000.0)
        self._set_spec(prod_b1, spec_inner_d, "75.0", 75.0, "verified")
        self._set_spec(prod_b1, spec_outer_d, "130.0", 130.0, "verified")

        prod_b2 = self._create_product("Vòng Bi NSK 32215 Lệch Nhẹ", "BEARING-02", categ_bearing.id, 460000.0)
        self._set_spec(prod_b2, spec_inner_d, "75.0", 75.0, "verified")
        self._set_spec(prod_b2, spec_outer_d, "130.1", 130.1, "verified")

        # So khớp trên danh mục hoàn toàn mới
        res = self.engine.find_matching_products(categ_bearing.id, {
            "bearing_inner_d": 75.0,
            "bearing_outer_d": 130.0,
        })

        self.assertTrue(res["success"])
        self.assertEqual(res["total_matches"], 2)
        self.assertEqual(res["ranked_matches"][0]["match_status"], "exact_match")
        self.assertEqual(res["ranked_matches"][1]["match_status"], "partial_match")

    def test_11_match_product_to_candidates_and_explanation(self):
        """11. Kiểm tra API tìm sản phẩm thay thế (match_product_to_candidates) và sinh bảng giải thích:
        - Tự động lấy thông số verified từ sản phẩm nguồn.
        - Loại trừ chính sản phẩm nguồn.
        - Sinh bảng đối chiếu HTML rõ ràng, đầy đủ các cột và giải thích kỹ thuật.
        """
        res = self.engine.match_product_to_candidates(self.prod_lc_base.id)
        self.assertTrue(res["success"])

        # Không chứa chính sản phẩm nguồn
        match_ids = [m["candidate_id"] for m in res["ranked_matches"]]
        self.assertNotIn(self.prod_lc_base.id, match_ids)
        self.assertIn(self.prod_lc_exact.id, match_ids)

        # Kiểm tra bảng đối chiếu HTML
        self.assertTrue(res["explanation_html"])
        self.assertIn("spec-matching-explanation", res["explanation_html"])
        self.assertIn("Đường kính ngoài LC", res["explanation_html"])
        self.assertIn("Khớp chính xác", res["explanation_html"])

    def test_12_parent_category_profile_inheritance(self):
        """12. Kế thừa Profile từ Danh Mục Cha (Parent Category Inheritance):
        - Danh mục cha có profile cấu hình.
        - Danh mục con không có profile -> Tự động kế thừa profile từ cha.
        - Khi danh mục con có profile riêng bị inactive -> Kế thừa profile từ cha.
        - Khi cả cha và con không có profile -> Fallback về Inferred Profile an toàn.
        """
        categ_parent = self.env["product.category"].create({"name": "TEST_PARENT_DRIVETRAIN"})
        categ_child = self.env["product.category"].create({"name": "TEST_CHILD_LC", "parent_id": categ_parent.id})

        spec_inherited = self._get_or_create_spec("test_inherited_diam", "Đường kính thừa kế", "float", "mm", [categ_parent.id], True)

        profile_parent = self.env["qba.category.matching.profile"].create({
            "name": "Profile Cha - Drivetrain",
            "category_id": categ_parent.id,
            "min_score_threshold": 80.0,
            "allow_partial_match": True,
        })
        self.env["qba.category.matching.rule"].create({
            "profile_id": profile_parent.id,
            "spec_definition_id": spec_inherited.id,
            "match_type": "exact",
            "weight": 50.0,
            "is_hard_constraint": True,
        })

        # Danh mục con chưa có profile -> Phải resolve ra profile của cha
        resolved = self.engine.resolve_profile(categ_child.id)
        self.assertEqual(resolved.id, profile_parent.id)

        # Tạo sản phẩm ở danh mục con và so khớp
        prod_child = self._create_product("Sản phẩm con", "TEST-CHILD-01", categ_child.id, 1000000.0)
        self._set_spec(prod_child, spec_inherited, "300.0", 300.0, "verified")

        res = self.engine.find_matching_products(categ_child.id, {"test_inherited_diam": 300.0})
        self.assertTrue(res["success"])
        self.assertEqual(res["total_matches"], 1)
        self.assertEqual(res["ranked_matches"][0]["candidate_id"], prod_child.id)

        # Trường hợp danh mục con có profile riêng nhưng active=False -> Vẫn kế thừa từ cha
        self.env["qba.category.matching.profile"].create({
            "name": "Profile Con Bị Vô Hiệu",
            "category_id": categ_child.id,
            "active": False,
        })
        resolved_after_inactive = self.engine.resolve_profile(categ_child.id)
        self.assertEqual(resolved_after_inactive.id, profile_parent.id)

        # Trường hợp danh mục không có profile ở cả cha và con -> Trả về Inferred Profile an toàn
        categ_standalone = self.env["product.category"].create({"name": "TEST_STANDALONE"})
        inferred = self.engine.resolve_profile(categ_standalone.id)
        self.assertTrue(isinstance(inferred, dict))
        self.assertTrue(inferred.get("is_inferred"))

    def test_13_inactive_rule_and_profile_deactivation(self):
        """13. Tắt/bật quy tắc so khớp (active=False trên rule):
        - Khi rule có active=False -> Engine hoàn toàn bỏ qua quy tắc này.
        - Không áp đặt điều kiện hard constraint của rule đã bị tắt.
        """
        rule_teeth = self.profile_lc.rule_ids.filtered(lambda r: r.spec_code == "match_lc_teeth")
        self.assertTrue(rule_teeth)

        input_specs = {"match_lc_outer_diam": 325.0, "match_lc_teeth": 10, "match_lc_hub_c": 31.0}
        eval_before = self.engine.evaluate_candidate(self.prod_lc_mismatch_teeth, input_specs, self.profile_lc)
        self.assertEqual(eval_before["match_status"], "mismatch")

        # Tắt rule răng moay ơ
        rule_teeth.write({"active": False})

        # Đánh giá lại: không còn kiểm tra răng moay ơ nữa, sản phẩm đạt exact match
        eval_after = self.engine.evaluate_candidate(self.prod_lc_mismatch_teeth, input_specs, self.profile_lc)
        self.assertEqual(eval_after["match_status"], "exact_match")

        # Bật lại rule
        rule_teeth.write({"active": True})
        eval_restored = self.engine.evaluate_candidate(self.prod_lc_mismatch_teeth, input_specs, self.profile_lc)
        self.assertEqual(eval_restored["match_status"], "mismatch")

    def test_14_range_match_type_and_boundary_conditions(self):
        """14. Kiểu so khớp theo khoảng (match_type='range') và điều kiện biên:
        - Giá trị nằm trong [min, max] -> Khớp exact.
        - Giá trị ngay tại biên min hoặc max -> Khớp exact.
        - Giá trị ngoài khoảng -> Mismatch.
        """
        rule_range = {
            "spec_code": "pad_thickness",
            "spec_name": "Độ dày má phanh",
            "data_type": "float",
            "match_type": "range",
            "tolerance_minus": 12.0,  # Min
            "tolerance_plus": 18.0,   # Max
            "weight": 20.0,
            "is_hard_constraint": True,
        }

        # Trong khoảng: 15.0
        res_inside = self.engine._evaluate_spec_rule(rule_range, 15.0, 15.0)
        self.assertEqual(res_inside["line_status"], "exact")
        self.assertEqual(res_inside["score"], 20.0)

        # Tại biên: 12.0 và 18.0
        res_min = self.engine._evaluate_spec_rule(rule_range, 12.0, 12.0)
        self.assertEqual(res_min["line_status"], "exact")
        res_max = self.engine._evaluate_spec_rule(rule_range, 18.0, 18.0)
        self.assertEqual(res_max["line_status"], "exact")

        # Ngoài khoảng: 11.9 và 18.1
        res_below = self.engine._evaluate_spec_rule(rule_range, 15.0, 11.9)
        self.assertEqual(res_below["line_status"], "mismatch")
        self.assertEqual(res_below["score"], 0.0)

        res_above = self.engine._evaluate_spec_rule(rule_range, 15.0, 18.1)
        self.assertEqual(res_above["line_status"], "mismatch")
        self.assertEqual(res_above["score"], 0.0)

    def test_15_hard_constraint_overrides_high_composite_score(self):
        """15. Hard constraint luôn có quyền ưu tiên tuyệt đối:
        Kể cả khi ứng viên đạt đa số điểm từ các thông số phụ khác, chỉ cần 1 hard constraint vi phạm
        thì match_status bắt buộc là 'mismatch' và điểm số cuối cùng phải bằng 0.0.
        """
        input_specs = {
            "match_lc_outer_diam": 325.0,
            "match_lc_teeth": 10,  # Hard constraint vi phạm trên prod_lc_mismatch_teeth
            "match_lc_hub_c": 31.0,
            "match_lc_springs": 6,
        }
        eval_res = self.engine.evaluate_candidate(self.prod_lc_mismatch_teeth, input_specs, self.profile_lc)
        self.assertEqual(eval_res["match_status"], "mismatch")
        self.assertEqual(eval_res["match_score"], 0.0)
        self.assertTrue(len(eval_res["violated_hard_constraints"]) >= 1)

    def test_16_html_explanation_xss_safety(self):
        """16. An toàn dữ liệu HTML (XSS Protection):
        Mọi ký tự đặc biệt như <script>, <img>, &, ", ' trong tên sản phẩm, mã SKU, ghi chú
        phải được escape an toàn bằng html_escape, không gây lỗi bảo mật XSS.
        """
        malicious_cand = {
            "candidate_id": 9999,
            "candidate_name": "<script>alert('XSS_NAME')</script>",
            "candidate_code": "<img src=x onerror=alert(1)>",
            "match_status": "exact_match",
            "match_score": 100.0,
            "status_reason": "Lý do chứa ký tự <tag> & ký tự đặc biệt",
            "comparison_lines": [
                {
                    "spec_code": "code_xss",
                    "spec_name": "<b onmouseover=evil()>Thông số độc hại</b>",
                    "input_val": "<script>alert(2)</script>",
                    "candidate_val": "\"><script>alert(3)</script>",
                    "delta": 0,
                    "uom": "<uom>",
                    "line_status": "exact",
                    "score": 10.0,
                    "weight": 10.0,
                    "notes": "<payload alert=yes>",
                    "is_hard_constraint": True,
                }
            ],
            "violated_hard_constraints": [],
            "missing_critical_specs": [],
        }

        html = self.engine.format_explanation(malicious_cand)
        self.assertNotIn("<script>", html)
        self.assertNotIn("<img src=x", html)
        self.assertNotIn("<b onmouseover", html)
        self.assertIn("&lt;script&gt;alert(&#39;XSS_NAME&#39;)&lt;/script&gt;", html)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", html)
        self.assertIn("&lt;b onmouseover=evil()&gt;", html)

    def test_17_security_access_rights_rpc(self):
        """17. Kiểm tra phân quyền truy cập ACL & Server-Side Security:
        - User thường (group_qba_ai_user): CHỈ được đọc (read-only), không được tạo, sửa, xóa profile hay rule.
        - Manager (group_qba_ai_manager): Có toàn quyền tạo, sửa, xóa profile và rule.
        """
        # User thường ĐỌC profile và rule: THÀNH CÔNG
        profiles_read = self.env["qba.category.matching.profile"].with_user(self.user_normal).search([])
        self.assertTrue(len(profiles_read) >= 1)

        # User thường TẠO profile mới: BỊ CHẶN AccessError
        with self.assertRaises(AccessError):
            self.env["qba.category.matching.profile"].with_user(self.user_normal).create({
                "name": "Profile Trái Phép",
                "category_id": self.categ_lc.id,
            })

        # User thường SỬA profile: BỊ CHẶN AccessError
        with self.assertRaises(AccessError):
            self.profile_lc.with_user(self.user_normal).write({"min_score_threshold": 50.0})

        # User thường XÓA profile: BỊ CHẶN AccessError
        with self.assertRaises(AccessError):
            self.profile_lc.with_user(self.user_normal).unlink()

        # User thường TẠO rule: BỊ CHẶN AccessError
        with self.assertRaises(AccessError):
            self.env["qba.category.matching.rule"].with_user(self.user_normal).create({
                "profile_id": self.profile_lc.id,
                "spec_definition_id": self.spec_lc_diam.id,
                "match_type": "exact",
            })

        # Manager TẠO, SỬA, XÓA: THÀNH CÔNG
        categ_temp = self.env["product.category"].create({"name": "TEST_TEMP_SEC"})
        prof_admin = self.env["qba.category.matching.profile"].with_user(self.user_ai_admin).create({
            "name": "Profile Quản Trị Hợp Lệ",
            "category_id": categ_temp.id,
            "min_score_threshold": 80.0,
        })
        self.assertTrue(prof_admin.id)

        prof_admin.write({"min_score_threshold": 85.0})
        self.assertEqual(prof_admin.min_score_threshold, 85.0)

        rule_admin = self.env["qba.category.matching.rule"].with_user(self.user_ai_admin).create({
            "profile_id": prof_admin.id,
            "spec_definition_id": self.spec_lc_diam.id,
            "match_type": "exact",
        })
        self.assertTrue(rule_admin.id)

        rule_admin.unlink()
        prof_admin.unlink()

    def test_18_ai_assistant_integration_and_empty_fallback(self):
        """18. Tích hợp AI Assistant với Matching Engine:
        - Khi câu hỏi tìm ra sản phẩm có thông số -> Tự động gọi engine và hiển thị matching_explanation_html.
        - Khi câu hỏi tìm ra sản phẩm CHƯA có thông số verified -> Hiển thị cảnh báo rõ ràng.
        - Khi câu hỏi không tìm ra sản phẩm và không có thông số -> Hiển thị hướng dẫn tra cứu cơ sở.
        - Khi câu hỏi nhập thông số kỹ thuật trực tiếp -> Tự động trích xuất và chạy Matching Engine.
        """
        # 1. Trường hợp tìm thấy sản phẩm có thông số verified (TEST-LC-BASE)
        assistant = self.env["qba.ai.assistant"].create({
            "user_query": "TEST-LC-BASE",
        })
        assistant.action_ask_ai()
        self.assertTrue(assistant.matched_product_ids)
        self.assertTrue(assistant.matching_explanation_html)
        self.assertIn("spec-matching-explanation", assistant.matching_explanation_html)

        # 2. Trường hợp câu hỏi không tìm thấy sản phẩm và không có thông số
        assistant_empty = self.env["qba.ai.assistant"].create({
            "user_query": "Sản phẩm không hề tồn tại trong vũ trụ XYZ123456",
        })
        assistant_empty.action_ask_ai()
        self.assertFalse(assistant_empty.matched_product_ids)
        self.assertTrue(assistant_empty.matching_explanation_html)
        self.assertIn("Không có sản phẩm cơ sở", assistant_empty.matching_explanation_html)

        # 3. Trường hợp tìm thấy sản phẩm CHƯA có thông số verified
        unverified_prod = self.env["product.template"].create({
            "name": "TEST-NO-SPECS-PRODUCT-999",
            "default_code": "TEST-NO-SPECS-999",
            "categ_id": self.categ_lc.id,
        })
        assistant_unverified = self.env["qba.ai.assistant"].create({
            "user_query": "TEST-NO-SPECS-999",
        })
        assistant_unverified.action_ask_ai()
        self.assertTrue(assistant_unverified.matched_product_ids)
        self.assertTrue(assistant_unverified.matching_explanation_html)
        self.assertIn("chưa có thông số kỹ thuật đã duyệt", assistant_unverified.matching_explanation_html)

        # 4. Trường hợp nhập trực tiếp thông số kỹ thuật (Direct Specs)
        assistant_direct = self.env["qba.ai.assistant"].create({
            "user_query": "Lá côn phi 325 10R",
        })
        assistant_direct.action_ask_ai()
        self.assertTrue(assistant_direct.matching_explanation_html)
        self.assertTrue(
            "spec-matching-explanation" in assistant_direct.matching_explanation_html
            or "Sản phẩm cơ sở" in assistant_direct.matching_explanation_html
            or "Đối Chiếu Kỹ Thuật" in assistant_direct.matching_explanation_html
        )


