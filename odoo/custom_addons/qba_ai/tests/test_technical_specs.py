from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, AccessError
from odoo.tools.misc import mute_logger


class TestTechnicalSpecs(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Nhóm quyền
        cls.group_ai_user = cls.env.ref("qba_ai.group_qba_ai_user")
        cls.group_ai_manager = cls.env.ref("qba_ai.group_qba_ai_manager")

        # Tạo user thường (chỉ là user nội bộ / AI user, KHÔNG có quyền Quản trị viên AI)
        cls.user_normal = cls.env["res.users"].create({
            "name": "Normal AI User",
            "login": "normal_ai_user_test",
            "email": "normal_ai_user@example.com",
            "groups_id": [(6, 0, [cls.env.ref("base.group_user").id, cls.group_ai_user.id])],
        })

        # Tạo user Quản trị viên AI (có group_qba_ai_manager)
        cls.user_ai_admin = cls.env["res.users"].create({
            "name": "AI Admin Manager",
            "login": "ai_admin_manager_test",
            "email": "ai_admin_manager@example.com",
            "groups_id": [(6, 0, [cls.env.ref("base.group_user").id, cls.group_ai_manager.id])],
        })

        # Tạo user Quản lý kho (Stock Manager - KHÔNG thuộc group_qba_ai_manager)
        cls.user_stock_manager = cls.env["res.users"].create({
            "name": "Stock Manager Test",
            "login": "stock_manager_test",
            "email": "stock_manager@example.com",
            "groups_id": [(6, 0, [cls.env.ref("base.group_user").id, cls.env.ref("stock.group_stock_manager").id, cls.group_ai_user.id])],
        })

        # Tạo user Quản lý mua hàng (Purchase Manager - KHÔNG thuộc group_qba_ai_manager)
        cls.user_purchase_manager = cls.env["res.users"].create({
            "name": "Purchase Manager Test",
            "login": "purchase_manager_test",
            "email": "purchase_manager@example.com",
            "groups_id": [(6, 0, [cls.env.ref("base.group_user").id, cls.env.ref("purchase.group_purchase_manager").id, cls.group_ai_user.id])],
        })

        # Tạo user Quản lý bán hàng (Sales Manager - KHÔNG thuộc group_qba_ai_manager)
        cls.user_sales_manager = cls.env["res.users"].create({
            "name": "Sales Manager Test",
            "login": "sales_manager_test",
            "email": "sales_manager@example.com",
            "groups_id": [(6, 0, [cls.env.ref("base.group_user").id, cls.env.ref("sales_team.group_sale_manager").id, cls.group_ai_user.id])],
        })

        # Tìm hoặc tạo danh mục LC và TBUA
        cls.categ_lc = cls.env["product.category"].search([("name", "ilike", "LC")], limit=1)
        if not cls.categ_lc:
            cls.categ_lc = cls.env["product.category"].create({"name": "LC - Lá côn"})

        cls.categ_tbua = cls.env["product.category"].search([("name", "ilike", "TBUA")], limit=1)
        if not cls.categ_tbua:
            cls.categ_tbua = cls.env["product.category"].create({"name": "TBUA - Tăm bua"})

        # Tạo sản phẩm mẫu cho LC và TBUA
        cls.product_lc = cls.env["product.template"].create({
            "name": "Test Lá Côn Howo 430",
            "default_code": "TEST-LC-001",
            "categ_id": cls.categ_lc.id,
        })
        cls.product_tbua = cls.env["product.template"].create({
            "name": "Test Tăm Bua Sau 16030FT",
            "default_code": "TEST-TBUA-001",
            "categ_id": cls.categ_tbua.id,
        })

    def test_01_spec_definition_creation_and_reusability(self):
        """Kiểm tra tạo thông số động tùy ý cho LC và TBUA mà không cần sửa code."""
        # Thông số dùng chung cho cả LC và TBUA: Đường kính ngoài
        spec_diameter = self.env["qba.product.spec.definition"].create({
            "name": "Đường kính ngoài",
            "code": "outer_diameter",
            "data_type": "float",
            "uom": "mm",
            "is_critical": True,
            "category_ids": [(6, 0, [self.categ_lc.id, self.categ_tbua.id])],
        })
        self.assertTrue(spec_diameter.id)
        self.assertEqual(len(spec_diameter.category_ids), 2)

        # Thông số riêng cho LC: Số răng moay ơ (integer)
        spec_teeth = self.env["qba.product.spec.definition"].create({
            "name": "Số răng moay ơ",
            "code": "spline_teeth",
            "data_type": "integer",
            "uom": "răng",
            "is_critical": True,
            "category_ids": [(6, 0, [self.categ_lc.id])],
        })
        self.assertTrue(spec_teeth.id)

        # Thông số riêng cho TBUA: Số lỗ bu lông (integer)
        spec_holes = self.env["qba.product.spec.definition"].create({
            "name": "Số lỗ tắc kê",
            "code": "bolt_holes",
            "data_type": "integer",
            "uom": "lỗ",
            "is_critical": True,
            "category_ids": [(6, 0, [self.categ_tbua.id])],
        })
        self.assertTrue(spec_holes.id)

        # Kiểm tra ràng buộc mã code trùng lặp
        with mute_logger("odoo.sql_db"), self.assertRaises(Exception), self.cr.savepoint():
            self.env["qba.product.spec.definition"].create({
                "name": "Đường kính trùng",
                "code": "outer_diameter",
                "data_type": "float",
            })

    def test_02_spec_value_datatypes_and_formatting(self):
        """Kiểm tra các kiểu dữ liệu và ép kiểu 2 chiều chính xác."""
        # 1. Kiểu float
        spec_float = self.env["qba.product.spec.definition"].create({
            "name": "Chiều cao tổng",
            "code": "total_height",
            "data_type": "float",
            "uom": "mm",
        })
        val_float = self.env["qba.product.spec.value"].create({
            "product_tmpl_id": self.product_tbua.id,
            "spec_definition_id": spec_float.id,
            "value_display": "220.5",
        })
        self.assertEqual(val_float.value_float, 220.5)
        self.assertEqual(val_float.value_display, "220.5")

        # 2. Kiểu integer
        spec_int = self.env["qba.product.spec.definition"].create({
            "name": "Số lỗ ốc",
            "code": "hole_count_test",
            "data_type": "integer",
            "uom": "lỗ",
        })
        val_int = self.env["qba.product.spec.value"].create({
            "product_tmpl_id": self.product_tbua.id,
            "spec_definition_id": spec_int.id,
            "value_display": "10",
        })
        self.assertEqual(val_int.value_integer, 10)
        self.assertEqual(val_int.value_display, "10")

        # 3. Kiểu boolean
        spec_bool = self.env["qba.product.spec.definition"].create({
            "name": "Có đệm giảm chấn",
            "code": "has_cushion",
            "data_type": "boolean",
        })
        val_bool = self.env["qba.product.spec.value"].create({
            "product_tmpl_id": self.product_lc.id,
            "spec_definition_id": spec_bool.id,
            "value_display": "Có",
        })
        self.assertTrue(val_bool.value_boolean)
        self.assertEqual(val_bool.value_display, "Đúng")

        # 4. Kiểu Selection
        spec_sel = self.env["qba.product.spec.definition"].create({
            "name": "Loại xương mâm",
            "code": "hub_type",
            "data_type": "selection",
            "selection_options": "Mâm cao\nMâm thấp\nMâm phẳng",
        })
        val_sel = self.env["qba.product.spec.value"].create({
            "product_tmpl_id": self.product_lc.id,
            "spec_definition_id": spec_sel.id,
            "value_display": "Mâm cao",
        })
        self.assertEqual(val_sel.value_char, "Mâm cao")

        # Thử nhập giá trị không nằm trong danh sách selection -> phải báo lỗi
        with self.assertRaises(ValidationError):
            val_sel.write({"value_display": "Mâm lạ không tồn tại"})

    def test_03_prevent_duplicate_spec_per_product(self):
        """Kiểm tra ngăn chặn trùng lặp thông số trên cùng 1 sản phẩm."""
        spec = self.env["qba.product.spec.definition"].create({
            "name": "Góc nghiêng",
            "code": "bevel_angle",
            "data_type": "float",
        })
        self.env["qba.product.spec.value"].create({
            "product_tmpl_id": self.product_lc.id,
            "spec_definition_id": spec.id,
            "value_display": "15.0",
        })
        # Tạo bản ghi thứ 2 cùng product và spec -> Bị từ chối
        with mute_logger("odoo.sql_db"), self.assertRaises(Exception), self.cr.savepoint():
            self.env["qba.product.spec.value"].create({
                "product_tmpl_id": self.product_lc.id,
                "spec_definition_id": spec.id,
                "value_display": "20.0",
            })

    def test_04_category_applicability_validation(self):
        """Kiểm tra chỉ định danh mục: không thể gán thông số ngoài danh mục áp dụng."""
        spec_tbua_only = self.env["qba.product.spec.definition"].create({
            "name": "Đường kính gờ lắp moay ơ",
            "code": "hub_pilot_diam",
            "data_type": "float",
            "category_ids": [(6, 0, [self.categ_tbua.id])],
        })
        # Gán cho sản phẩm Lá côn (LC) -> Phải raise ValidationError
        with self.assertRaises(ValidationError):
            self.env["qba.product.spec.value"].create({
                "product_tmpl_id": self.product_lc.id,
                "spec_definition_id": spec_tbua_only.id,
                "value_display": "295.0",
            })

        # Gán cho sản phẩm Tăm bua (TBUA) -> Thành công
        val = self.env["qba.product.spec.value"].create({
            "product_tmpl_id": self.product_tbua.id,
            "spec_definition_id": spec_tbua_only.id,
            "value_display": "295.0",
        })
        self.assertTrue(val.id)

    def test_05_security_approval_boundaries(self):
        """Kiểm tra phân quyền: Chỉ Quản trị viên AI (group_qba_ai_manager) mới có quyền duyệt/sửa dữ liệu chính thức."""
        spec = self.env["qba.product.spec.definition"].create({
            "name": "Độ dày đĩa",
            "code": "disc_thickness",
            "data_type": "float",
        })

        # 1. User thường tạo bản ghi -> Trạng thái mặc định là 'unverified'
        spec_val_normal = self.env["qba.product.spec.value"].with_user(self.user_normal).create({
            "product_tmpl_id": self.product_lc.id,
            "spec_definition_id": spec.id,
            "value_display": "12.5",
        })
        self.assertEqual(spec_val_normal.validation_status, "unverified")

        # 2. User thường cố tình tạo bản ghi với trạng thái 'verified' -> Bị AccessError
        with self.assertRaises(AccessError):
            self.env["qba.product.spec.value"].with_user(self.user_normal).create({
                "product_tmpl_id": self.product_tbua.id,
                "spec_definition_id": spec.id,
                "value_display": "14.0",
                "validation_status": "verified",
            })

        # 3. User thường gọi action_verify qua RPC/ORM -> Bị AccessError
        with self.assertRaises(AccessError):
            spec_val_normal.with_user(self.user_normal).action_verify()

        # 4. User thường gọi write({'validation_status': 'verified'}) -> Bị AccessError
        with self.assertRaises(AccessError):
            spec_val_normal.with_user(self.user_normal).write({"validation_status": "verified"})

        # 5. Quản trị viên AI duyệt -> Thành công
        spec_val_admin = spec_val_normal.with_user(self.user_ai_admin)
        spec_val_admin.action_verify()
        self.assertEqual(spec_val_admin.validation_status, "verified")
        self.assertEqual(spec_val_admin.verified_by_id.id, self.user_ai_admin.id)
        self.assertTrue(spec_val_admin.verified_date)

        # 6. User thường cố sửa bản ghi đã xác thực -> Bị AccessError
        with self.assertRaises(AccessError):
            spec_val_normal.with_user(self.user_normal).write({"value_display": "15.0"})

        # 7. User thường cố xóa bản ghi đã xác thực -> Bị AccessError
        with self.assertRaises(AccessError):
            spec_val_normal.with_user(self.user_normal).unlink()

        # 8. Quản trị viên AI có thể thu hồi (reset to unverified)
        spec_val_admin.action_reset_unverified()
        self.assertEqual(spec_val_admin.validation_status, "unverified")
        self.assertFalse(spec_val_admin.verified_by_id)

    def test_06_populate_category_specs_helper(self):
        """Kiểm tra nút tải mẫu thông số từ danh mục vào sản phẩm."""
        # Tạo định nghĩa gắn với LC
        spec_lc_1 = self.env["qba.product.spec.definition"].create({
            "name": "Đường kính đinh tán",
            "code": "rivet_diameter",
            "data_type": "float",
            "category_ids": [(6, 0, [self.categ_lc.id])],
        })
        self.categ_lc.tech_spec_definition_ids = [(4, spec_lc_1.id)]

        # Tạo sản phẩm mới trong LC chưa có thông số nào
        new_prod = self.env["product.template"].create({
            "name": "Lá côn thử nghiệm",
            "default_code": "LC-NEW-001",
            "categ_id": self.categ_lc.id,
        })
        self.assertEqual(len(new_prod.spec_value_ids), 0)

        # Gọi hàm populate
        new_prod.action_populate_category_specs()

        # Kiểm tra thông số đã được tạo dưới dạng bản nháp unverified, không tự bịa giá trị
        self.assertTrue(any(v.spec_definition_id.id == spec_lc_1.id for v in new_prod.spec_value_ids))
        val_line = new_prod.spec_value_ids.filtered(lambda v: v.spec_definition_id.id == spec_lc_1.id)
        self.assertEqual(val_line.validation_status, "unverified")
        self.assertEqual(val_line.source, "manual_entry")

    def test_07_spec_definition_deletion(self):
        """Kiểm tra quyền xóa và cơ chế bảo vệ toàn vẹn dữ liệu khi xóa định nghĩa thông số:
        - Người dùng thường cố xóa -> AccessError.
        - Định nghĩa có giá trị verified -> ValidationError, chặn xóa, hướng dẫn active=False.
        - Định nghĩa có giá trị unverified -> ValidationError, chặn xóa ngoài ý muốn.
        - Chỉ khi không còn giá trị liên kết -> Cho phép Quản trị viên AI xóa thành công.
        """
        # 1. Tạo thông số mẫu
        spec_to_del = self.env["qba.product.spec.definition"].create({
            "name": "Thông số chuẩn bị xóa",
            "code": "spec_to_delete_test",
            "data_type": "float",
            "category_ids": [(6, 0, [self.categ_lc.id])],
        })
        spec_id = spec_to_del.id

        # Gán giá trị thông số cho sản phẩm LC ở trạng thái verified
        val_rec = self.env["qba.product.spec.value"].create({
            "product_tmpl_id": self.product_lc.id,
            "spec_definition_id": spec_id,
            "value_float": 150.0,
            "validation_status": "verified",
        })
        val_id = val_rec.id

        # 2. Người dùng thông thường cố xóa -> Phải bị AccessError
        with self.assertRaises(AccessError):
            spec_to_del.with_user(self.user_normal).action_delete_spec_definition()

        with self.assertRaises(AccessError):
            spec_to_del.with_user(self.user_normal).unlink()

        # 3. Quản trị viên AI xóa định nghĩa đang có giá trị verified -> Phải bị CHẶN bởi ValidationError
        with self.assertRaises(ValidationError) as cm_verified:
            spec_to_del.with_user(self.user_ai_admin).action_delete_spec_definition()
        self.assertIn("active = False", str(cm_verified.exception))

        with self.assertRaises(ValidationError):
            spec_to_del.with_user(self.user_ai_admin).unlink()

        # Xác nhận định nghĩa và giá trị verified vẫn được bảo toàn
        self.assertTrue(self.env["qba.product.spec.definition"].search([("id", "=", spec_id)]))
        self.assertTrue(self.env["qba.product.spec.value"].search([("id", "=", val_id)]))

        # 4. Chuyển giá trị sang unverified -> Vẫn phải bị chặn bởi ValidationError để tránh mất dữ liệu ngoài ý muốn
        val_rec.validation_status = "unverified"
        with self.assertRaises(ValidationError):
            spec_to_del.with_user(self.user_ai_admin).action_delete_spec_definition()

        # 5. Khi giá trị liên kết đã được dọn sạch hoàn toàn -> Cho phép Quản trị viên AI xóa vĩnh viễn
        val_rec.unlink()
        res = spec_to_del.with_user(self.user_ai_admin).action_delete_spec_definition()
        self.assertEqual(res.get("type"), "ir.actions.client")
        self.assertEqual(res.get("tag"), "display_notification")

        # Xác nhận bản ghi định nghĩa thông số đã biến mất khỏi DB
        found_def = self.env["qba.product.spec.definition"].search([("id", "=", spec_id)])
        self.assertFalse(found_def, "Định nghĩa thông số phải bị xóa hoàn toàn khỏi cơ sở dữ liệu khi không còn liên kết!")

    def test_08_spec_modal_dialog_actions(self):
        """Kiểm tra các action mở modal cấu hình chi tiết và tạo mới thông số."""
        # 1. Action mở modal tạo mới từ danh mục
        action_create = self.categ_lc.action_create_new_spec()
        self.assertEqual(action_create.get("type"), "ir.actions.act_window")
        self.assertEqual(action_create.get("target"), "new")
        self.assertEqual(action_create.get("res_model"), "qba.product.spec.definition")
        self.assertIn("default_category_ids", action_create.get("context", {}))

        # 2. Action mở modal xem/sửa chi tiết cho thông số đã tồn tại
        spec_test = self.env["qba.product.spec.definition"].create({
            "name": "Thông số chi tiết test",
            "code": "spec_modal_detail_test",
            "data_type": "selection",
            "selection_options": "Tùy chọn 1\nTùy chọn 2",
            "category_ids": [(6, 0, [self.categ_lc.id])],
        })
        action_open = spec_test.action_open_spec_form()
        self.assertEqual(action_open.get("type"), "ir.actions.act_window")
        self.assertEqual(action_open.get("target"), "new")
        self.assertEqual(action_open.get("res_id"), spec_test.id)

    def test_09_lc_product_specs_entry_and_validation(self):
        """Kiểm tra toàn diện nhập thông số cấp sản phẩm, định dạng số thập phân, giá trị trống và bảo vệ phê duyệt."""
        # 1. Tạo các định nghĩa thông số kỹ thuật cho danh mục LC (Lá côn)
        spec_diameter = self.env["qba.product.spec.definition"].create({
            "name": "Đường kính ngoài",
            "code": "lc_outer_diameter",
            "data_type": "float",
            "uom": "mm",
            "is_critical": True,
            "category_ids": [(6, 0, [self.categ_lc.id])],
        })
        spec_teeth = self.env["qba.product.spec.definition"].create({
            "name": "Số răng moay ơ",
            "code": "lc_spline_teeth",
            "data_type": "integer",
            "uom": "răng",
            "is_critical": True,
            "category_ids": [(6, 0, [self.categ_lc.id])],
        })
        spec_hub = self.env["qba.product.spec.definition"].create({
            "name": "Kích thước moay ơ",
            "code": "lc_hub_size",
            "data_type": "float",
            "uom": "mm",
            "category_ids": [(6, 0, [self.categ_lc.id])],
        })
        spec_springs = self.env["qba.product.spec.definition"].create({
            "name": "Số lò xo",
            "code": "lc_spring_count",
            "data_type": "integer",
            "uom": "lò xo",
            "category_ids": [(6, 0, [self.categ_lc.id])],
        })
        spec_optional = self.env["qba.product.spec.definition"].create({
            "name": "Chất liệu bố",
            "code": "lc_facing_material",
            "data_type": "char",
            "category_ids": [(6, 0, [self.categ_lc.id])],
        })

        # 2. Tạo sản phẩm mẫu LC.002
        prod_lc002 = self.env["product.template"].create({
            "name": "Lá Côn Howo 325 (LC.002)",
            "default_code": "TEST-LC.002",
            "categ_id": self.categ_lc.id,
            "list_price": 1250000.0,
        })
        orig_price = prod_lc002.list_price
        orig_code = prod_lc002.default_code

        # 3. Nhập giá trị kỹ thuật cho LC.002:
        # outer diameter 325 mm, spline teeth 10, hub measurements 38 mm, spring count 8
        val_diam = self.env["qba.product.spec.value"].create({
            "product_tmpl_id": prod_lc002.id,
            "spec_definition_id": spec_diameter.id,
            "value_display": "325",
        })
        val_teeth = self.env["qba.product.spec.value"].create({
            "product_tmpl_id": prod_lc002.id,
            "spec_definition_id": spec_teeth.id,
            "value_display": "10",
        })
        val_hub = self.env["qba.product.spec.value"].create({
            "product_tmpl_id": prod_lc002.id,
            "spec_definition_id": spec_hub.id,
            "value_display": "38",
        })
        val_springs = self.env["qba.product.spec.value"].create({
            "product_tmpl_id": prod_lc002.id,
            "spec_definition_id": spec_springs.id,
            "value_display": "8",
        })
        # Thông số không rõ (unknown value): để trống
        val_unknown = self.env["qba.product.spec.value"].create({
            "product_tmpl_id": prod_lc002.id,
            "spec_definition_id": spec_optional.id,
            "value_display": "",
        })

        # 4. Kiểm tra lưu trữ và hiển thị đúng kiểu:
        self.assertEqual(val_diam.value_float, 325.0)
        self.assertEqual(val_diam.value_display, "325")
        self.assertEqual(val_teeth.value_integer, 10)
        self.assertEqual(val_teeth.value_display, "10")
        self.assertEqual(val_springs.value_integer, 8)
        self.assertEqual(val_springs.value_display, "8")
        # Kiểm tra giá trị để trống (unknown) không bị ép thành 0 hoặc False hiển thị
        self.assertEqual(val_unknown.value_display, "")
        self.assertFalse(val_unknown.value_char)

        # 5. Kiểm tra mẫu số thập phân LC.003: hub measurement 38.5 mm
        prod_lc003 = self.env["product.template"].create({
            "name": "Lá Côn Howo 350 (LC.003)",
            "default_code": "TEST-LC.003",
            "categ_id": self.categ_lc.id,
        })
        val_hub_decimal = self.env["qba.product.spec.value"].create({
            "product_tmpl_id": prod_lc003.id,
            "spec_definition_id": spec_hub.id,
            "value_display": "38.5",
        })
        self.assertEqual(val_hub_decimal.value_float, 38.5)
        self.assertEqual(val_hub_decimal.value_display, "38.5")

        # 6. Kiểm tra các trường hiển thị tên thông số, đơn vị, trạng thái mặc định
        self.assertEqual(val_hub_decimal.spec_code, "lc_hub_size")
        self.assertEqual(val_hub_decimal.uom, "mm")
        self.assertEqual(val_hub_decimal.data_type, "float")
        self.assertEqual(val_hub_decimal.validation_status, "unverified")
        self.assertEqual(val_hub_decimal.source, "manual_entry")

        # 7. Kiểm tra ngăn chặn trùng lặp: không thể thêm cùng thông số 2 lần cho 1 sản phẩm
        with mute_logger("odoo.sql_db"), self.assertRaises(Exception), self.cr.savepoint():
            self.env["qba.product.spec.value"].create({
                "product_tmpl_id": prod_lc003.id,
                "spec_definition_id": spec_hub.id,
                "value_display": "39",
            })

        # 8. Kiểm tra bảo mật: User thường KHÔNG thể duyệt thông số chính thức qua direct RPC
        with self.assertRaises(AccessError):
            val_hub_decimal.with_user(self.user_normal).action_verify()

        with self.assertRaises(AccessError):
            val_hub_decimal.with_user(self.user_normal).write({"validation_status": "verified"})

        # Chỉ Quản trị viên AI mới có quyền duyệt
        val_hub_decimal.with_user(self.user_ai_admin).action_verify()
        self.assertEqual(val_hub_decimal.validation_status, "verified")

        # 9. Kiểm tra các trường gốc của sản phẩm không bị thay đổi / xáo trộn
        self.assertEqual(prod_lc002.list_price, orig_price)
        self.assertEqual(prod_lc002.default_code, orig_code)

    def test_10_datatype_continuous_vs_discrete_validation(self):
        """Kiểm tra chi tiết kiểu số thực vs số nguyên:
        1. Float diameter accepts 325.
        2. Float diameter accepts 38.5.
        3. Integer tooth count accepts 10.
        4. Integer tooth count rejects invalid fractional values (10.5, 10,5).
        5. Empty unknown values remain empty.
        6. Invalid text cannot be stored as a valid numeric value.
        """
        spec_diam = self.env["qba.product.spec.definition"].create({
            "name": "Đường kính ngoài kiểm thử",
            "code": "test_diam_float",
            "data_type": "float",
            "uom": "mm",
            "category_ids": [(6, 0, [self.categ_lc.id])],
        })

        spec_teeth = self.env["qba.product.spec.definition"].create({
            "name": "Số răng kiểm thử",
            "code": "test_teeth_int",
            "data_type": "integer",
            "uom": "răng",
            "category_ids": [(6, 0, [self.categ_lc.id])],
        })

        # 1. Float diameter accepts 325
        v_diam_int = self.env["qba.product.spec.value"].create({
            "product_tmpl_id": self.product_lc.id,
            "spec_definition_id": spec_diam.id,
            "value_display": "325",
        })
        self.assertEqual(v_diam_int.value_float, 325.0)
        self.assertEqual(v_diam_int.value_display, "325")

        # 2. Float diameter accepts 38.5
        prod_temp2 = self.env["product.template"].create({
            "name": "Sản phẩm kiểm thử float",
            "categ_id": self.categ_lc.id,
        })
        v_diam_dec = self.env["qba.product.spec.value"].create({
            "product_tmpl_id": prod_temp2.id,
            "spec_definition_id": spec_diam.id,
            "value_display": "38.5",
        })
        self.assertEqual(v_diam_dec.value_float, 38.5)
        self.assertEqual(v_diam_dec.value_display, "38.5")

        # 3. Integer tooth count accepts 10
        v_teeth = self.env["qba.product.spec.value"].create({
            "product_tmpl_id": self.product_lc.id,
            "spec_definition_id": spec_teeth.id,
            "value_display": "10",
        })
        self.assertEqual(v_teeth.value_integer, 10)
        self.assertEqual(v_teeth.value_display, "10")

        # 4. Integer tooth count rejects invalid fractional values
        with self.assertRaises(ValidationError):
            self.env["qba.product.spec.value"].create({
                "product_tmpl_id": prod_temp2.id,
                "spec_definition_id": spec_teeth.id,
                "value_display": "10.5",
            })
        with self.assertRaises(ValidationError):
            self.env["qba.product.spec.value"].create({
                "product_tmpl_id": prod_temp2.id,
                "spec_definition_id": spec_teeth.id,
                "value_display": "10,5",
            })

        # 5. Empty unknown values remain empty
        spec_opt = self.env["qba.product.spec.definition"].create({
            "name": "Thông số chưa rõ",
            "code": "test_opt_unknown",
            "data_type": "float",
            "category_ids": [(6, 0, [self.categ_lc.id])],
        })
        v_empty = self.env["qba.product.spec.value"].create({
            "product_tmpl_id": self.product_lc.id,
            "spec_definition_id": spec_opt.id,
            "value_display": "",
        })
        self.assertEqual(v_empty.value_display, "")
        self.assertFalse(v_empty.value_char)

        # 6. Invalid text cannot be stored as a numeric value
        prod_invalid = self.env["product.template"].create({
            "name": "Sản phẩm kiểm thử giá trị lỗi",
            "categ_id": self.categ_lc.id,
        })
        with self.assertRaises(ValidationError):
            self.env["qba.product.spec.value"].create({
                "product_tmpl_id": prod_invalid.id,
                "spec_definition_id": spec_diam.id,
                "value_display": "phi_325_khong_hop_le",
            })
        with self.assertRaises(ValidationError):
            self.env["qba.product.spec.value"].create({
                "product_tmpl_id": prod_invalid.id,
                "spec_definition_id": spec_teeth.id,
                "value_display": "muoi_rang",
            })

    def test_11_hub_diameter_split_and_migration(self):
        """Kiểm tra tính năng tách và chuẩn hóa thông số Moay ơ C & D:
        7. Dữ liệu gốc 31|38 được bảo toàn nguyên vẹn.
        8. Bản xem trước (preview) phân tích chính xác C=31, D=38 và C=31, D=38.5.
        9. Giá trị đề xuất chuyển đổi ở trạng thái 'unverified'.
        10. Dữ liệu mơ hồ/lỗi được đánh dấu cần kiểm tra thủ công, không tự động chuyển đổi.
        """
        def_old = self.env["qba.product.spec.definition"].with_context(active_test=False).search([("code", "=", "duong_kinh_moay_o")], limit=1)
        if not def_old:
            def_old = self.env["qba.product.spec.definition"].create({
                "name": "đường kính moay ơ",
                "code": "duong_kinh_moay_o",
                "data_type": "char",
                "uom": "mm",
                "category_ids": [(6, 0, [self.categ_lc.id])],
            })
        elif not def_old.active:
            def_old.active = True

        p1 = self.env["product.template"].create({
            "name": "Lá côn 31|38 test",
            "categ_id": self.categ_lc.id,
        })
        v1 = self.env["qba.product.spec.value"].create({
            "product_tmpl_id": p1.id,
            "spec_definition_id": def_old.id,
            "value_display": "31|38",
            "validation_status": "verified",
        })

        p2 = self.env["product.template"].create({
            "name": "Lá côn 31/38.5 test",
            "categ_id": self.categ_lc.id,
        })
        v2 = self.env["qba.product.spec.value"].create({
            "product_tmpl_id": p2.id,
            "spec_definition_id": def_old.id,
            "value_display": "31/38.5",
            "validation_status": "unverified",
        })

        p3 = self.env["product.template"].create({
            "name": "Lá côn mơ hồ test",
            "categ_id": self.categ_lc.id,
        })
        v3 = self.env["qba.product.spec.value"].create({
            "product_tmpl_id": p3.id,
            "spec_definition_id": def_old.id,
            "value_display": "chưa rõ kích thước",
        })

        # 8. Chạy preview_hub_diameter_split trên qba.lc.spec.parser (vị trí chuẩn mới)
        preview = self.env["qba.lc.spec.parser"].preview_hub_diameter_split(category_id=self.categ_lc.id)
        p1_item = next(item for item in preview if item["product_id"] == p1.id)
        p2_item = next(item for item in preview if item["product_id"] == p2.id)
        p3_item = next(item for item in preview if item["product_id"] == p3.id)

        self.assertEqual(p1_item["status"], "ready")
        self.assertEqual(p1_item["c_value"], 31.0)
        self.assertEqual(p1_item["d_value"], 38.0)

        self.assertEqual(p2_item["status"], "ready")
        self.assertEqual(p2_item["c_value"], 31.0)
        self.assertEqual(p2_item["d_value"], 38.5)

        # Kiểm tra proxy tương thích ngược trên qba.product.spec.definition
        preview_compat = self.env["qba.product.spec.definition"].preview_hub_diameter_split(category_id=self.categ_lc.id)
        self.assertEqual(len(preview_compat), len(preview))

        # 10. Giá trị mơ hồ được gắn cờ manual_review_required
        self.assertEqual(p3_item["status"], "manual_review_required")

        # Thực thi chuyển đổi an toàn (Admin AI thực hiện trên qba.lc.spec.parser)
        res = self.env["qba.lc.spec.parser"].with_user(self.user_ai_admin).action_apply_hub_diameter_split()
        self.assertEqual(res.get("type"), "ir.actions.client")

        # 7. Kiểm tra giá trị gốc vẫn được giữ nguyên
        self.assertEqual(v1.value_display, "31|38")
        self.assertEqual(v1.validation_status, "verified")

        # 9. Kiểm tra giá trị tách mới tạo ra ở trạng thái 'unverified'
        def_c = self.env["qba.product.spec.definition"].search([("code", "=", "duong_kinh_moay_o_c")], limit=1)
        def_d = self.env["qba.product.spec.definition"].search([("code", "=", "duong_kinh_moay_o_d")], limit=1)
        self.assertTrue(def_c)
        self.assertTrue(def_d)

        val_c1 = self.env["qba.product.spec.value"].search([("product_tmpl_id", "=", p1.id), ("spec_definition_id", "=", def_c.id)])
        val_d1 = self.env["qba.product.spec.value"].search([("product_tmpl_id", "=", p1.id), ("spec_definition_id", "=", def_d.id)])
        self.assertTrue(val_c1)
        self.assertTrue(val_d1)
        self.assertEqual(val_c1.value_float, 31.0)
        self.assertEqual(val_d1.value_float, 38.0)
        self.assertEqual(val_c1.validation_status, "unverified")
        self.assertEqual(val_d1.validation_status, "unverified")

        # Sản phẩm 3 không bị tự tiện tạo thông số sai
        val_c3 = self.env["qba.product.spec.value"].search([("product_tmpl_id", "=", p3.id), ("spec_definition_id", "=", def_c.id)])
        self.assertFalse(val_c3)

        # Kiểm tra tính năng rollback trên qba.lc.spec.parser
        rollback_cnt = self.env["qba.lc.spec.parser"].with_user(self.user_ai_admin).action_rollback_hub_diameter_split(category_id=self.categ_lc.id)
        self.assertTrue(rollback_cnt >= 2)
        self.assertTrue(v1.exists())
        self.assertEqual(v1.value_display, "31|38")

    def test_12_strict_approval_security_boundaries(self):
        """Kiểm tra ranh giới bảo mật cấp máy chủ:
        11. Nhân viên thông thường không thể gọi action_verify / action_reject.
        12. Quản lý kho (Stock Manager) không có quyền duyệt AI.
        13. Quản lý mua hàng (Purchase Manager) không có quyền duyệt AI.
        14. Quản lý bán hàng (Sales Manager) không có quyền duyệt AI.
        15. Chỉ Admin AI mới có thể duyệt.
        16. Chặn toàn bộ RPC write trái phép vào validation_status, verified_by_id, verified_date.
        """
        spec = self.env["qba.product.spec.definition"].create({
            "name": "Thông số kiểm thử bảo mật",
            "code": "test_sec_spec",
            "data_type": "float",
            "category_ids": [(6, 0, [self.categ_lc.id])],
        })
        val = self.env["qba.product.spec.value"].create({
            "product_tmpl_id": self.product_lc.id,
            "spec_definition_id": spec.id,
            "value_display": "50.0",
            "validation_status": "unverified",
        })

        # 11. Nhân viên thông thường gọi approval methods -> AccessError
        with self.assertRaises(AccessError):
            val.with_user(self.user_normal).action_verify()
        with self.assertRaises(AccessError):
            val.with_user(self.user_normal).action_reject()
        with self.assertRaises(AccessError):
            val.with_user(self.user_normal).action_reset_unverified()

        # 12. Quản lý kho (Stock Manager) gọi approval methods -> AccessError
        with self.assertRaises(AccessError):
            val.with_user(self.user_stock_manager).action_verify()
        with self.assertRaises(AccessError):
            val.with_user(self.user_stock_manager).action_reject()

        # 13. Quản lý mua hàng (Purchase Manager) gọi approval methods -> AccessError
        with self.assertRaises(AccessError):
            val.with_user(self.user_purchase_manager).action_verify()
        with self.assertRaises(AccessError):
            val.with_user(self.user_purchase_manager).action_reject()

        # Quản lý bán hàng (Sales Manager) -> AccessError
        with self.assertRaises(AccessError):
            val.with_user(self.user_sales_manager).action_verify()

        # 15. Chặn trực tiếp write qua RPC đối với trường validation_status
        with self.assertRaises(AccessError):
            val.with_user(self.user_normal).write({"validation_status": "verified"})
        with self.assertRaises(AccessError):
            val.with_user(self.user_stock_manager).write({"validation_status": "verified"})
        with self.assertRaises(AccessError):
            val.with_user(self.user_purchase_manager).write({"validation_status": "conflicted"})
        with self.assertRaises(AccessError):
            val.with_user(self.user_normal).write({"verified_by_id": self.user_ai_admin.id})

        # 14. Quản trị viên AI duyệt hợp lệ -> Thành công
        val.with_user(self.user_ai_admin).action_verify()
        self.assertEqual(val.validation_status, "verified")
        self.assertEqual(val.verified_by_id.id, self.user_ai_admin.id)

        # Sau khi đã duyệt, người dùng thường không thể chỉnh sửa dữ liệu
        with self.assertRaises(AccessError):
            val.with_user(self.user_normal).write({"value_display": "55.0"})

    def test_13_approval_counts_and_status_transitions(self):
        """Kiểm tra bộ đếm số lượng thông số và trạng thái duyệt trên sản phẩm:
        16. Số lượng đếm thay đổi chuẩn xác khi duyệt, từ chối hoặc trả về nháp.
        17. Chỉ giá trị 'verified' mới được tính là đã duyệt, unverified và conflicted không được tính.
        - Deactivate thông số cập nhật lại bộ đếm chính xác.
        """
        spec1 = self.env["qba.product.spec.definition"].create({
            "name": "Thông số đếm 1", "code": "count_spec_1", "data_type": "float",
            "category_ids": [(6, 0, [self.categ_lc.id])],
        })
        spec2 = self.env["qba.product.spec.definition"].create({
            "name": "Thông số đếm 2", "code": "count_spec_2", "data_type": "integer",
            "category_ids": [(6, 0, [self.categ_lc.id])],
        })
        spec3 = self.env["qba.product.spec.definition"].create({
            "name": "Thông số đếm 3", "code": "count_spec_3", "data_type": "char",
            "category_ids": [(6, 0, [self.categ_lc.id])],
        })

        test_prod = self.env["product.template"].create({
            "name": "Sản phẩm kiểm tra bộ đếm",
            "categ_id": self.categ_lc.id,
        })
        v1 = self.env["qba.product.spec.value"].create({
            "product_tmpl_id": test_prod.id, "spec_definition_id": spec1.id, "value_display": "100.0",
        })
        v2 = self.env["qba.product.spec.value"].create({
            "product_tmpl_id": test_prod.id, "spec_definition_id": spec2.id, "value_display": "10",
        })
        v3 = self.env["qba.product.spec.value"].create({
            "product_tmpl_id": test_prod.id, "spec_definition_id": spec3.id, "value_display": "Mẫu A",
        })

        # Ban đầu: 3 thông số, 0 thông số đã duyệt
        self.assertEqual(test_prod.spec_value_count, 3)
        self.assertEqual(test_prod.spec_verified_count, 0)
        self.assertFalse(test_prod.spec_has_conflict)

        # Duyệt v1 -> 1 / 3 đã duyệt
        v1.with_user(self.user_ai_admin).action_verify()
        self.assertEqual(test_prod.spec_verified_count, 1)

        # Từ chối v2 (conflicted) -> Không làm tăng số lượng đã duyệt, kích hoạt spec_has_conflict
        v2.with_user(self.user_ai_admin).action_reject()
        self.assertEqual(test_prod.spec_verified_count, 1)
        self.assertTrue(test_prod.spec_has_conflict)

        # Thu hồi v1 về nháp -> 0 / 3 đã duyệt
        v1.with_user(self.user_ai_admin).action_reset_unverified()
        self.assertEqual(test_prod.spec_verified_count, 0)

        # Deactivate / Archive spec3 -> Bộ đếm tự động giảm xuống 2 thông số
        spec3.active = False
        self.assertEqual(test_prod.spec_value_count, 2)

    def test_14_lc_parser_preview_and_rule_accuracy(self):
        """Kiểm tra độ chính xác của bộ phân tích tên sản phẩm LC và chế độ xem trước (preview-only):
        - Quy tắc nhận diện đúng outer diameter, teeth, hub C/D, lò xo.
        - Chặn nhận diện sai các con số thuộc model xe, mã phụ tùng, động cơ, tải trọng (BJ1041, CA142, 3,5T, WP10...).
        - Khi không có dữ liệu trong tên thì không được tự suy đoán (missing).
        - Bản xem trước (preview) là READ-ONLY tuyệt đối: KHÔNG ghi/sửa dữ liệu qba.product.spec.value.
        """
        parser = self.env["qba.lc.spec.parser"]

        # 1. Trích xuất chính xác các mẫu cú pháp hợp lệ
        res_standard = parser.parse_lc_name("Lá côn phi 325-10R 31/38 8 lò xo Howo")
        self.assertEqual(res_standard.get("duong_kinh_ngoai", {}).get("value"), 325.0)
        self.assertEqual(res_standard.get("rang", {}).get("value"), 10)
        self.assertEqual(res_standard.get("duong_kinh_moay_o_c", {}).get("value"), 31.0)
        self.assertEqual(res_standard.get("duong_kinh_moay_o_d", {}).get("value"), 38.0)
        self.assertEqual(res_standard.get("lo_xo", {}).get("value"), 8)

        # 2. Cú pháp biến thể: Ø, số thập phân, dạng răng viết thường hoặc có chữ răng, ngoặc đơn lò xo
        res_variant = parser.parse_lc_name("Lá côn Ø350-10r 31/38.5 (6 lò xo mâm cao)")
        self.assertEqual(res_variant.get("duong_kinh_ngoai", {}).get("value"), 350.0)
        self.assertEqual(res_variant.get("rang", {}).get("value"), 10)
        self.assertEqual(res_variant.get("duong_kinh_moay_o_c", {}).get("value"), 31.0)
        self.assertEqual(res_variant.get("duong_kinh_moay_o_d", {}).get("value"), 38.5)
        self.assertEqual(res_variant.get("lo_xo", {}).get("value"), 6)

        res_teeth_word = parser.parse_lc_name("Lá côn đk 430 - 14 răng 41/52.5")
        self.assertEqual(res_teeth_word.get("duong_kinh_ngoai", {}).get("value"), 430.0)
        self.assertEqual(res_teeth_word.get("rang", {}).get("value"), 14)
        self.assertEqual(res_teeth_word.get("duong_kinh_moay_o_c", {}).get("value"), 41.0)
        self.assertEqual(res_teeth_word.get("duong_kinh_moay_o_d", {}).get("value"), 52.5)

        # 3. Chặn triệt để nhận diện sai số model xe, mã phụ tùng, động cơ, tải trọng
        res_vehicle = parser.parse_lc_name("Lá côn xe tải BJ1041 CA142 EQ145 tải trọng 3,5T động cơ WP10 mã 700A-900B")
        self.assertNotIn("duong_kinh_ngoai", res_vehicle)
        self.assertNotIn("rang", res_vehicle)
        self.assertNotIn("duong_kinh_moay_o_c", res_vehicle)
        self.assertNotIn("duong_kinh_moay_o_d", res_vehicle)
        self.assertNotIn("lo_xo", res_vehicle)

        # 4. Kiểm tra chế độ xem trước (Preview): KHÔNG làm thay đổi DB sản phẩm
        prod_preview = self.env["product.template"].create({
            "name": "Lá côn phi 350-10R 31/38 6 lò xo xem trước",
            "default_code": "LC-PREVIEW-001",
            "categ_id": self.categ_lc.id,
        })
        self.assertEqual(len(prod_preview.spec_value_ids), 0)

        wizard = self.env["qba.lc.spec.parser.wizard"].with_user(self.user_ai_admin).create({
            "product_ids": [(6, 0, prod_preview.ids)],
            "category_id": self.categ_lc.id,
        })
        wizard.action_parse_preview()

        # Dòng preview đã được sinh ra
        lines = wizard.line_ids.filtered(lambda l: l.product_tmpl_id.id == prod_preview.id)
        self.assertEqual(len(lines), 5)

        # Kiểm tra thông số trên sản phẩm: Vẫn phải bằng 0 (hoàn toàn chưa ghi vào DB)
        self.assertEqual(len(prod_preview.spec_value_ids), 0)

        # Đảm bảo các dòng preview có dữ liệu đề xuất chính xác
        outer_line = lines.filtered(lambda l: l.spec_code == "duong_kinh_ngoai")
        self.assertEqual(outer_line.proposed_value, "350")
        self.assertEqual(outer_line.parsing_status, "confident")
        self.assertEqual(outer_line.proposed_action, "create_draft")

    def test_15_lc_parser_apply_unverified_and_conflict_handling(self):
        """Kiểm tra áp dụng đề xuất parser và xử lý xung đột:
        - Tạo bản nháp ở trạng thái 'unverified', KHÔNG BAO GIỜ tự động duyệt 'verified'.
        - Không ghi đè dữ liệu đã duyệt 'verified'.
        - Phát hiện xung đột (conflict) và chuyển sang kiểm tra thủ công (manual_review).
        - Tính bất biến (Idempotent): Chạy nhiều lần không sinh bản ghi trùng lặp.
        - Nguồn dữ liệu (source) và dấu vết (token/notes) được lưu lại đầy đủ.
        """
        prod_apply = self.env["product.template"].create({
            "name": "Lá côn phi 350-10R 31/38.5 8 lò xo thực thi",
            "default_code": "LC-APPLY-001",
            "categ_id": self.categ_lc.id,
        })

        wizard = self.env["qba.lc.spec.parser.wizard"].with_user(self.user_ai_admin).create({
            "product_ids": [(6, 0, prod_apply.ids)],
            "category_id": self.categ_lc.id,
        })
        wizard.action_parse_preview()
        self.assertEqual(len(wizard.line_ids), 5)

        # 1. Admin áp dụng đề xuất
        wizard.with_user(self.user_ai_admin).action_apply_proposals()

        # Đã tạo 5 thông số trên sản phẩm
        self.assertEqual(len(prod_apply.spec_value_ids), 5)

        # Tất cả đều ở trạng thái 'unverified', KHÔNG có cái nào là 'verified'
        for val in prod_apply.spec_value_ids:
            self.assertEqual(val.validation_status, "unverified")
            self.assertEqual(val.source, "parsed_from_name")
            self.assertTrue(val.notes)

        # Kiểm tra chi tiết giá trị từng thông số
        outer_val = prod_apply.spec_value_ids.filtered(lambda v: v.spec_definition_id.code == "duong_kinh_ngoai")
        self.assertEqual(outer_val.value_float, 350.0)
        teeth_val = prod_apply.spec_value_ids.filtered(lambda v: v.spec_definition_id.code == "rang")
        self.assertEqual(teeth_val.value_integer, 10)
        hub_c_val = prod_apply.spec_value_ids.filtered(lambda v: v.spec_definition_id.code == "duong_kinh_moay_o_c")
        self.assertEqual(hub_c_val.value_float, 31.0)
        hub_d_val = prod_apply.spec_value_ids.filtered(lambda v: v.spec_definition_id.code == "duong_kinh_moay_o_d")
        self.assertEqual(hub_d_val.value_float, 38.5)
        spring_val = prod_apply.spec_value_ids.filtered(lambda v: v.spec_definition_id.code == "lo_xo")
        self.assertEqual(spring_val.value_integer, 8)

        # 2. Idempotent: Áp dụng lại lần 2 không sinh bản ghi trùng lặp
        wizard2 = self.env["qba.lc.spec.parser.wizard"].with_user(self.user_ai_admin).create({
            "product_ids": [(6, 0, prod_apply.ids)],
            "category_id": self.categ_lc.id,
        })
        wizard2.action_parse_preview()
        wizard2.with_user(self.user_ai_admin).action_apply_proposals()
        self.assertEqual(len(prod_apply.spec_value_ids), 5)

        # 3. Xử lý xung đột khi sản phẩm đã có thông số đã duyệt (verified)
        # Giả sử Admin duyệt thông số đường kính ngoài 350.0
        outer_val.with_user(self.user_ai_admin).action_verify()
        self.assertEqual(outer_val.validation_status, "verified")

        # Đổi tên sản phẩm sang phi 325 (xung đột với giá trị 350.0 đã duyệt)
        prod_apply.name = "Lá côn phi 325-10R 31/38.5 8 lò xo thực thi"

        wizard3 = self.env["qba.lc.spec.parser.wizard"].with_user(self.user_ai_admin).create({
            "product_ids": [(6, 0, prod_apply.ids)],
            "category_id": self.categ_lc.id,
        })
        wizard3.action_parse_preview()

        line_outer = wizard3.line_ids.filtered(lambda l: l.spec_code == "duong_kinh_ngoai")
        self.assertEqual(line_outer.parsing_status, "conflict")
        self.assertEqual(line_outer.proposed_action, "manual_review")

        # Khi Admin bấm áp dụng, giá trị đã duyệt 350.0 KHÔNG bị ghi đè!
        wizard3.with_user(self.user_ai_admin).action_apply_proposals()
        outer_val.invalidate_recordset()
        self.assertEqual(outer_val.value_float, 350.0)
        self.assertEqual(outer_val.validation_status, "verified")

    def test_16_lc_parser_security_rpc_boundary(self):
        """Kiểm tra hàng rào bảo mật (Security Boundaries) của LC Parser:
        - Chỉ Quản trị viên AI (qba_ai.group_qba_ai_manager) mới được thực thi áp dụng đề xuất.
        - Người dùng thường, Quản lý kho (Stock Manager), Mua hàng (Purchase Manager) bị chặn AccessError.
        - Mở parser từ Product/Category bị chặn nếu không thuộc nhóm Quản trị viên AI.
        """
        prod_sec = self.env["product.template"].create({
            "name": "Lá côn phi 325-10R 31/38 8 lò xo bảo mật",
            "categ_id": self.categ_lc.id,
        })

        wizard = self.env["qba.lc.spec.parser.wizard"].with_user(self.user_ai_admin).create({
            "product_ids": [(6, 0, prod_sec.ids)],
            "category_id": self.categ_lc.id,
        })
        wizard.action_parse_preview()

        # Người dùng thường gọi action_apply_proposals -> AccessError
        with self.assertRaises(AccessError):
            wizard.with_user(self.user_normal).action_apply_proposals()

        # Quản lý kho gọi action_apply_proposals -> AccessError
        with self.assertRaises(AccessError):
            wizard.with_user(self.user_stock_manager).action_apply_proposals()

        # Quản lý mua hàng gọi action_apply_proposals -> AccessError
        with self.assertRaises(AccessError):
            wizard.with_user(self.user_purchase_manager).action_apply_proposals()

        # Quản lý bán hàng gọi action_apply_proposals -> AccessError
        with self.assertRaises(AccessError):
            wizard.with_user(self.user_sales_manager).action_apply_proposals()

        # Mở wizard từ product.template và product.category đối với user thường -> AccessError
        with self.assertRaises(AccessError):
            prod_sec.with_user(self.user_normal).action_open_lc_parser_wizard()
        with self.assertRaises(AccessError):
            self.categ_lc.with_user(self.user_normal).action_open_lc_parser_wizard()

        # Quản trị viên AI thực hiện -> Thành công không lỗi
        wizard.with_user(self.user_ai_admin).action_apply_proposals()
        self.assertTrue(len(prod_sec.spec_value_ids) > 0)

    def test_17_spec_definition_active_toggle_and_code_uniqueness(self):
        """Kiểm tra xử lý bật/tắt 'Có hiệu lực' (active) và chống trùng mã kỹ thuật:
        - Khi tắt active, thông số vẫn phải truy xuất được qua context active_test=False trên danh mục.
        - Tạo mới thông số trùng mã với thông số đang TẮT hiệu lực phải báo lỗi rõ ràng kèm hướng dẫn.
        - Xóa vĩnh viễn (action_delete_spec_definition) cho phép tái sử dụng mã sạch sẽ.
        """
        # 1. Tạo thông số mới
        spec = self.env["qba.product.spec.definition"].create({
            "name": "Thông số Test Bug Active",
            "code": "test_bug_active",
            "data_type": "char",
            "category_ids": [(6, 0, [self.categ_lc.id])],
            "active": True,
        })
        self.assertTrue(spec.id)

        # 2. Tắt hiệu lực (active = False)
        spec.active = False

        # Kiểm tra: trên category với active_test=False vẫn phải nhìn thấy thông số này
        cat_specs = self.categ_lc.with_context(active_test=False).tech_spec_definition_ids
        self.assertIn(spec.id, cat_specs.ids)

        # 3. Thử tạo mới thông số khác nhưng trùng mã kỹ thuật 'test_bug_active'
        with self.assertRaises(ValidationError) as cm:
            self.env["qba.product.spec.definition"].create({
                "name": "Thông số Trùng Mã",
                "code": "test_bug_active",
                "data_type": "char",
            })
        self.assertIn("TẮT HIỆU LỰC", str(cm.exception))

        # 4. Xóa vĩnh viễn thông số cũ
        spec.action_delete_spec_definition()

        # 5. Sau khi đã xóa hẳn, có thể tạo lại với mã đó thành công
        new_spec = self.env["qba.product.spec.definition"].create({
            "name": "Thông số Tạo Lại Thành Công",
            "code": "test_bug_active",
            "data_type": "char",
        })
        self.assertTrue(new_spec.id)

    def test_18_spec_definition_deletion_protection(self):
        """Phase 3.2 - Task 5.1: Kiểm tra tuyệt đối không xóa định nghĩa có giá trị verified:
        - Định nghĩa có giá trị verified: unlink() hoặc action_delete_spec_definition() ném ValidationError.
        - Hướng dẫn người dùng chuyển sang active=False.
        - Giá trị verified không bị mất.
        """
        spec = self.env["qba.product.spec.definition"].create({
            "name": "Thông số Bảo vệ Verified",
            "code": "spec_protect_verified",
            "data_type": "float",
            "category_ids": [(6, 0, [self.categ_lc.id])],
        })
        val = self.env["qba.product.spec.value"].create({
            "product_tmpl_id": self.product_lc.id,
            "spec_definition_id": spec.id,
            "value_float": 220.0,
            "validation_status": "verified",
        })

        # Quản trị viên AI gọi action_delete_spec_definition -> Bị chặn
        with self.assertRaises(ValidationError) as cm:
            spec.with_user(self.user_ai_admin).action_delete_spec_definition()
        self.assertIn("active = False", str(cm.exception))

        # Quản trị viên AI gọi trực tiếp unlink -> Bị chặn
        with self.assertRaises(ValidationError) as cm2:
            spec.with_user(self.user_ai_admin).unlink()
        self.assertIn("active = False", str(cm2.exception))

        # Xác nhận bản ghi vẫn còn nguyên
        self.assertTrue(spec.exists())
        self.assertTrue(val.exists())
        self.assertEqual(val.validation_status, "verified")

    def test_19_lc_parser_preview_pure_readonly_and_rpc_security(self):
        """Phase 3.2 - Task 5.2 & 5.3:
        - 5.3: Người dùng không có quyền (user thường, stock manager) bị từ chối AccessError khi gọi Preview.
        - 5.2: Preview hoàn toàn chỉ đọc:
          + Không thay đổi active của định nghĩa đang bị tắt (ném ValidationError yêu cầu bật cấu hình).
          + Không tạo/sửa bất kỳ bản ghi persistent nào trên qba.product.spec.definition, qba.product.spec.value hoặc product.template.
        """
        # Đảm bảo 5 định nghĩa LC chuẩn tồn tại
        self.env["qba.lc.spec.parser"]._ensure_lc_spec_definitions(self.categ_lc.id)

        wizard = self.env["qba.lc.spec.parser.wizard"].create({
            "category_id": self.categ_lc.id,
            "product_ids": [(6, 0, [self.product_lc.id])],
        })

        # 1. RPC Security: User thường và Stock Manager gọi action_parse_preview -> AccessError
        with self.assertRaises(AccessError):
            wizard.with_user(self.user_normal).action_parse_preview()
        with self.assertRaises(AccessError):
            wizard.with_user(self.user_stock_manager).action_parse_preview()

        # 2. Preview không tự bật active=True:
        # Tắt một định nghĩa chuẩn (ví dụ: rang)
        spec_rang = self.env["qba.product.spec.definition"].search([("code", "=", "rang")], limit=1)
        self.assertTrue(spec_rang)
        spec_rang.active = False

        # Quản trị viên chạy Preview -> Bị chặn bởi ValidationError vì thiếu cấu hình active, KHÔNG tự bật active
        with self.assertRaises(ValidationError) as cm:
            wizard.with_user(self.user_ai_admin).action_parse_preview()
        self.assertIn("active = False", str(cm.exception))

        # Kiểm tra spec_rang vẫn đang active=False (không hề bị ghi đè thành active=True)
        spec_rang.invalidate_recordset()
        self.assertFalse(spec_rang.active, "Preview không được tự động bật active=True cho định nghĩa đang tắt!")

        # Bật lại để kiểm tra tính chỉ đọc
        spec_rang.active = True

        # Đếm số lượng bản ghi persistent trước khi chạy Preview
        count_defs_before = self.env["qba.product.spec.definition"].search_count([])
        count_vals_before = self.env["qba.product.spec.value"].search_count([])

        # Chạy preview
        wizard.with_user(self.user_ai_admin).action_parse_preview()

        # Đếm lại sau khi chạy Preview
        count_defs_after = self.env["qba.product.spec.definition"].search_count([])
        count_vals_after = self.env["qba.product.spec.value"].search_count([])

        self.assertEqual(count_defs_before, count_defs_after, "Preview tuyệt đối không tạo/xóa định nghĩa persistent!")
        self.assertEqual(count_vals_before, count_vals_after, "Preview tuyệt đối không ghi dữ liệu spec_value persistent!")
        self.assertTrue(len(wizard.line_ids) > 0, "Chỉ tạo các dòng transient xem trước!")

    def test_20_lc_parser_conflict_detection_lc002_and_lc007(self):
        """Phase 3.2 - Task 5.4 & 5.5:
        - 5.4: LC.002 báo xung đột D=38.5 so với đề xuất 38, không tự động chọn (selected=False).
        - 5.5: LC.007 thiếu dữ liệu lịch sử phải chuyển sang manual_review / conflict, selected=False.
        """
        # Đảm bảo 5 định nghĩa LC chuẩn tồn tại
        defs = self.env["qba.lc.spec.parser"]._ensure_lc_spec_definitions(self.categ_lc.id)

        # 1. Tạo sản phẩm mô phỏng LC.002
        prod_lc002 = self.env["product.template"].create({
            "name": "Lá côn Aisin DTX-135 325 10R 31/38 6 lò xo",
            "default_code": "TEST-LC.002",
            "categ_id": self.categ_lc.id,
        })
        # Gán 5 thông số verified cho LC.002, trong đó D = 38.5
        val_d = self.env["qba.product.spec.value"].create({
            "product_tmpl_id": prod_lc002.id,
            "spec_definition_id": defs["duong_kinh_moay_o_d"].id,
            "value_float": 38.5,
            "validation_status": "verified",
        })
        self.env["qba.product.spec.value"].create({
            "product_tmpl_id": prod_lc002.id,
            "spec_definition_id": defs["duong_kinh_moay_o_c"].id,
            "value_float": 31.0,
            "validation_status": "verified",
        })

        wizard_lc002 = self.env["qba.lc.spec.parser.wizard"].create({
            "product_ids": [(6, 0, [prod_lc002.id])],
            "category_id": self.categ_lc.id,
        })
        wizard_lc002.with_user(self.user_ai_admin).action_parse_preview()

        line_d = wizard_lc002.line_ids.filtered(lambda l: l.spec_code == "duong_kinh_moay_o_d")
        self.assertEqual(line_d.parsing_status, "conflict", "LC.002 thông số D=38.5 phải báo xung đột với đề xuất 38!")
        self.assertEqual(line_d.proposed_action, "manual_review")
        self.assertFalse(line_d.selected, "Dòng xung đột LC.002 tuyệt đối không được tự động chọn áp dụng (selected=False)!")

        line_c = wizard_lc002.line_ids.filtered(lambda l: l.spec_code == "duong_kinh_moay_o_c")
        self.assertEqual(line_c.parsing_status, "match")
        self.assertEqual(line_c.proposed_action, "skip")
        self.assertFalse(line_c.selected)

        # 2. Tạo sản phẩm mô phỏng LC.007 (chưa có thông số moay ơ cũ 20mm trong DB do bị mất)
        prod_lc007 = self.env["product.template"].create({
            "name": "Lá côn Aisin DTX-157 300 14R 31/38 4 lò xo",
            "default_code": "LC.007",
            "categ_id": self.categ_lc.id,
        })

        wizard_lc007 = self.env["qba.lc.spec.parser.wizard"].create({
            "product_ids": [(6, 0, [prod_lc007.id])],
            "category_id": self.categ_lc.id,
        })
        wizard_lc007.with_user(self.user_ai_admin).action_parse_preview()

        line_c_007 = wizard_lc007.line_ids.filtered(lambda l: l.spec_code == "duong_kinh_moay_o_c")
        line_d_007 = wizard_lc007.line_ids.filtered(lambda l: l.spec_code == "duong_kinh_moay_o_d")

        self.assertEqual(line_c_007.parsing_status, "conflict")
        self.assertEqual(line_c_007.proposed_action, "manual_review")
        self.assertFalse(line_c_007.selected, "LC.007 thông số C không được tự động chọn khi thiếu lịch sử!")
        self.assertIn("LC.007", line_c_007.notes)

        self.assertEqual(line_d_007.parsing_status, "conflict")
        self.assertEqual(line_d_007.proposed_action, "manual_review")
        self.assertFalse(line_d_007.selected, "LC.007 thông số D không được tự động chọn khi thiếu lịch sử!")

        # 3. Phase 4.0 - Bước 4: Kiểm tra cơ chế Anomaly Detection theo dữ liệu (internal_notes) trên sản phẩm bất kỳ
        prod_anomaly = self.env["product.template"].create({
            "name": "Lá côn Thaco 300 14R 31/38 4 lò xo",
            "default_code": "TEST-ANOMALY-001",
            "categ_id": self.categ_lc.id,
            "internal_notes": "[ANOMALY] Bất thường kích thước moay ơ trong lô sản xuất",
        })
        wizard_anomaly = self.env["qba.lc.spec.parser.wizard"].create({
            "product_ids": [(6, 0, [prod_anomaly.id])],
            "category_id": self.categ_lc.id,
        })
        wizard_anomaly.with_user(self.user_ai_admin).action_parse_preview()
        line_c_anom = wizard_anomaly.line_ids.filtered(lambda l: l.spec_code == "duong_kinh_moay_o_c")
        line_d_anom = wizard_anomaly.line_ids.filtered(lambda l: l.spec_code == "duong_kinh_moay_o_d")

        self.assertEqual(line_c_anom.parsing_status, "conflict")
        self.assertEqual(line_c_anom.proposed_action, "manual_review")
        self.assertFalse(line_c_anom.selected, "Sản phẩm có bất thường dữ liệu không được tự động chọn áp dụng!")
        self.assertIn("Bất thường kích thước moay ơ trong lô sản xuất", line_c_anom.notes)

        self.assertEqual(line_d_anom.parsing_status, "conflict")
        self.assertEqual(line_d_anom.proposed_action, "manual_review")
        self.assertFalse(line_d_anom.selected)
        self.assertIn("Bất thường kích thước moay ơ trong lô sản xuất", line_d_anom.notes)

    def test_21_lc_parser_apply_server_side_defense_and_idempotency(self):
        """Phase 3.2 - Task 5.6, 5.7, 5.8:
        - 5.6: Dòng conflict/manual_review không được Apply kể cả khi client cố tình gửi selected=True.
        - 5.7: Chạy Apply nhiều lần mang tính Idempotent, không tạo dữ liệu trùng.
        - 5.8: Không làm thay đổi tên, SKU, giá niêm yết, danh mục hoặc dữ liệu kế toán/kho của sản phẩm.
        """
        defs = self.env["qba.lc.spec.parser"]._ensure_lc_spec_definitions(self.categ_lc.id)

        # Tạo sản phẩm kiểm thử với các trường nghiệp vụ quan trọng
        prod = self.env["product.template"].create({
            "name": "Lá côn Howo 430 10R 35/42 10 lò xo",
            "default_code": "TEST-BIZ-DATA",
            "list_price": 1250000.0,
            "standard_price": 950000.0,
            "categ_id": self.categ_lc.id,
        })

        # Gán một thông số verified: số răng = 10
        teeth_val = self.env["qba.product.spec.value"].create({
            "product_tmpl_id": prod.id,
            "spec_definition_id": defs["rang"].id,
            "value_integer": 10,
            "validation_status": "verified",
        })

        # Mở wizard preview
        wizard = self.env["qba.lc.spec.parser.wizard"].create({
            "product_ids": [(6, 0, [prod.id])],
            "category_id": self.categ_lc.id,
        })
        wizard.with_user(self.user_ai_admin).action_parse_preview()

        # Giả lập client gian lận: Cố tình đặt selected=True cho dòng răng (match/skip) và tạo 1 dòng conflict
        line_teeth = wizard.line_ids.filtered(lambda l: l.spec_code == "rang")
        line_teeth.write({"selected": True, "proposed_action": "manual_review", "parsing_status": "conflict"})

        # Lưu lại snapshot dữ liệu kinh doanh trước khi Apply
        orig_name = prod.name
        orig_code = prod.default_code
        orig_price = prod.list_price
        orig_cost = prod.standard_price
        orig_categ = prod.categ_id.id

        # 1. Gọi Apply lần 1
        wizard.with_user(self.user_ai_admin).action_apply_proposals()

        # Kiểm tra phòng thủ Server-side: Dòng teeth có conflict/manual_review KHÔNG được áp dụng, giá trị verified không bị đụng tới
        teeth_val.invalidate_recordset()
        self.assertEqual(teeth_val.validation_status, "verified")
        self.assertEqual(teeth_val.value_integer, 10)

        # Đếm số lượng spec_values của sản phẩm sau lần Apply 1
        vals_count_run1 = len(prod.spec_value_ids)
        self.assertTrue(vals_count_run1 > 1, "Các dòng confident khác phải được tạo dưới dạng unverified")

        # 2. Gọi Apply lần 2 (Kiểm tra Idempotency)
        # Giả lập bấm Apply lại trên wizard
        wizard.with_user(self.user_ai_admin).action_apply_proposals()
        prod.invalidate_recordset()
        vals_count_run2 = len(prod.spec_value_ids)
        self.assertEqual(vals_count_run1, vals_count_run2, "Chạy Apply lần 2 tuyệt đối không sinh thêm bản ghi trùng!")

        # 3. Chạy lại Preview từ đầu rồi Apply lần 3 (Kiểm tra Idempotency thực tế)
        wizard2 = self.env["qba.lc.spec.parser.wizard"].create({
            "product_ids": [(6, 0, [prod.id])],
            "category_id": self.categ_lc.id,
        })
        wizard2.with_user(self.user_ai_admin).action_parse_preview()
        # Tất cả các dòng lúc này đã là 'match' / 'skip'
        self.assertTrue(all(l.proposed_action == "skip" for l in wizard2.line_ids))
        self.assertTrue(all(not l.selected for l in wizard2.line_ids))

        # Cố tình ép selected=True trên wizard2 rồi Apply
        wizard2.line_ids.write({"selected": True})
        wizard2.with_user(self.user_ai_admin).action_apply_proposals()
        prod.invalidate_recordset()
        self.assertEqual(len(prod.spec_value_ids), vals_count_run1, "Apply lại không bao giờ làm tăng số lượng spec_value!")

        # 4. Bảo toàn 100% dữ liệu kinh doanh
        self.assertEqual(prod.name, orig_name, "Tên sản phẩm không bị thay đổi")
        self.assertEqual(prod.default_code, orig_code, "Mã sản phẩm (SKU) không bị thay đổi")
        self.assertEqual(prod.list_price, orig_price, "Giá niêm yết không bị thay đổi")
        self.assertEqual(prod.standard_price, orig_cost, "Giá vốn không bị thay đổi")
        self.assertEqual(prod.categ_id.id, orig_categ, "Danh mục sản phẩm không bị thay đổi")

    def test_22_ai_knowledge_security_boundaries(self):
        """Phase 4.0 - Bước 1: Kiểm tra quyền quản lý thư viện kiến thức kỹ thuật (qba.ai.knowledge):
        - Người dùng thường (user_normal) không thể tạo bài kiến thức (AccessError).
        - Quản trị viên AI (user_ai_admin) tạo thành công.
        - Người dùng thường không thể chỉnh sửa bài kiến thức (AccessError).
        - Người dùng thường không thể xóa bài kiến thức (AccessError).
        - Quản trị viên AI có toàn quyền chỉnh sửa và xóa.
        """
        knowledge_model = self.env["qba.ai.knowledge"]

        # 1. User thường tạo bài kiến thức -> Bị từ chối bằng AccessError
        with self.assertRaises(AccessError):
            knowledge_model.with_user(self.user_normal).create({
                "name": "Bài hướng dẫn trái phép",
                "content": "<p>Nội dung trái phép</p>",
                "category": "measurement",
            })

        # 2. Quản trị viên AI tạo bài kiến thức -> Thành công
        k_rec = knowledge_model.with_user(self.user_ai_admin).create({
            "name": "Bài hướng dẫn hợp lệ",
            "content": "<p>Nội dung đo chuẩn kỹ thuật</p>",
            "category": "measurement",
        })
        self.assertTrue(k_rec.id)

        # 3. User thường cố tình chỉnh sửa -> Bị từ chối bằng AccessError
        with self.assertRaises(AccessError):
            k_rec.with_user(self.user_normal).write({
                "name": "Sửa trái phép",
            })

        # 4. Quản trị viên AI chỉnh sửa -> Thành công
        k_rec.with_user(self.user_ai_admin).write({
            "name": "Bài hướng dẫn đã cập nhật",
        })
        self.assertEqual(k_rec.name, "Bài hướng dẫn đã cập nhật")

        # 5. User thường cố tình xóa -> Bị từ chối bằng AccessError
        with self.assertRaises(AccessError):
            k_rec.with_user(self.user_normal).unlink()

        # 6. Quản trị viên AI xóa -> Thành công
        k_rec.with_user(self.user_ai_admin).unlink()
        self.assertFalse(k_rec.exists())

    def test_23_generic_parser_dispatcher(self):
        """Phase 4.0 - Bước 3 & Bước 5: Kiểm tra Generic Parser Dispatcher:
        1. Người dùng không có quyền (user_normal) gọi action_open_spec_parser_wizard bị chặn bởi AccessError.
        2. Quản trị viên AI gọi action_open_spec_parser_wizard trên LC (sản phẩm và danh mục) mở LC wizard.
        3. Backward compatibility: action_open_lc_parser_wizard vẫn hoạt động tương đương.
        4. Quản trị viên AI gọi action_open_spec_parser_wizard trên TBUA (sản phẩm và danh mục) nhận thông báo Chưa hỗ trợ, KHÔNG chạy LC parser.
        """
        # 1. AccessError với user không có quyền
        with self.assertRaises(AccessError):
            self.product_lc.with_user(self.user_normal).action_open_spec_parser_wizard()
        with self.assertRaises(AccessError):
            self.categ_lc.with_user(self.user_normal).action_open_spec_parser_wizard()

        # 2. Dispatcher mở LC wizard cho sản phẩm LC
        action_prod_lc = self.product_lc.with_user(self.user_ai_admin).action_open_spec_parser_wizard()
        self.assertEqual(action_prod_lc.get("type"), "ir.actions.act_window")
        self.assertEqual(action_prod_lc.get("res_model"), "qba.lc.spec.parser.wizard")
        self.assertEqual(action_prod_lc.get("target"), "new")
        self.assertIn(self.product_lc.id, action_prod_lc.get("context", {}).get("default_product_ids", []))

        # Dispatcher mở LC wizard cho danh mục LC
        action_cat_lc = self.categ_lc.with_user(self.user_ai_admin).action_open_spec_parser_wizard()
        self.assertEqual(action_cat_lc.get("type"), "ir.actions.act_window")
        self.assertEqual(action_cat_lc.get("res_model"), "qba.lc.spec.parser.wizard")
        self.assertEqual(action_cat_lc.get("context", {}).get("default_category_id"), self.categ_lc.id)

        # 3. Backward compatibility wrapper vẫn hoạt động
        action_prod_compat = self.product_lc.with_user(self.user_ai_admin).action_open_lc_parser_wizard()
        self.assertEqual(action_prod_compat.get("res_model"), "qba.lc.spec.parser.wizard")
        action_cat_compat = self.categ_lc.with_user(self.user_ai_admin).action_open_lc_parser_wizard()
        self.assertEqual(action_cat_compat.get("res_model"), "qba.lc.spec.parser.wizard")

        # 4. Sản phẩm / Danh mục TBUA nhận thông báo chưa hỗ trợ (ir.actions.client), KHÔNG mở LC wizard
        action_prod_tbua = self.product_tbua.with_user(self.user_ai_admin).action_open_spec_parser_wizard()
        self.assertEqual(action_prod_tbua.get("type"), "ir.actions.client")
        self.assertEqual(action_prod_tbua.get("tag"), "display_notification")
        self.assertEqual(action_prod_tbua.get("params", {}).get("type"), "warning")
        self.assertIn("Chưa hỗ trợ công cụ trích xuất", action_prod_tbua.get("params", {}).get("title", ""))

        action_cat_tbua = self.categ_tbua.with_user(self.user_ai_admin).action_open_spec_parser_wizard()
        self.assertEqual(action_cat_tbua.get("type"), "ir.actions.client")
        self.assertEqual(action_cat_tbua.get("tag"), "display_notification")
        self.assertEqual(action_cat_tbua.get("params", {}).get("type"), "warning")
        self.assertIn("Chưa hỗ trợ công cụ trích xuất", action_cat_tbua.get("params", {}).get("title", ""))




