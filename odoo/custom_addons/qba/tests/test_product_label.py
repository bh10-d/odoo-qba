# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.addons.qba.models.product_label_wizard import ProductLabelService
import base64
from PIL import Image
from io import BytesIO


class TestProductLabelWizard(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.brand = cls.env['qba.brand'].create({'name': 'TEST_BRAND'})
        cls.partner = cls.env['res.partner'].create({'name': 'NCC Test'})
        cls.product = cls.env['product.template'].create({
            'name': 'Bơm hơi xe ben Howo Sinotruk',
            'default_code': 'BOM.TEST.001',
            'brand_id': cls.brand.id,
        })
        cls.supplierinfo = cls.env['product.supplierinfo'].create({
            'partner_id': cls.partner.id,
            'product_tmpl_id': cls.product.id,
            'product_code': 'SUP-9988',
        })

    def test_barcode_generation_pure_pil(self):
        """Test pure PIL Code128 generation without Cairo/renderPM dependency"""
        img = ProductLabelService.generate_barcode_image('BOM.TEST.001', width=480, height=80)
        self.assertIsNotNone(img)
        self.assertEqual(img.size, (480, 80))

        # Test ASCII validation with invalid unicode
        invalid_img = ProductLabelService.generate_barcode_image('Có dấu tiếng Việt')
        self.assertIsNone(invalid_img)

    def test_open_label_wizard_defaults(self):
        """Test open_label_wizard action and default_get in wizard"""
        action = self.product.open_label_wizard()
        ctx = action.get('context', {})
        self.assertEqual(ctx.get('default_product_id'), self.product.id)
        self.assertEqual(ctx.get('default_custom_name'), self.product.name)
        self.assertEqual(ctx.get('default_supplier_code'), 'SUP-9988')
        self.assertEqual(ctx.get('default_supplier_product_code'), self.supplierinfo.id)

        wizard = self.env['qba.product.label.wizard'].with_context(ctx).create({})
        self.assertEqual(wizard.product_id.id, self.product.id)
        self.assertEqual(wizard.default_code, 'BOM.TEST.001')
        self.assertEqual(wizard.custom_name, self.product.name)
        self.assertEqual(wizard.supplier_code, 'SUP-9988')
        self.assertEqual(wizard.supplier_product_code.id, self.supplierinfo.id)
        self.assertTrue(bool(wizard.dinh_luong))

    def test_action_generate_label(self):
        """Test generating label image and attaching to product"""
        action = self.product.open_label_wizard()
        wizard = self.env['qba.product.label.wizard'].with_context(action.get('context')).create({})
        wizard.action_generate_label()

        self.assertTrue(bool(self.product.label_image))
        decoded = base64.b64decode(self.product.label_image)
        img = Image.open(BytesIO(decoded))
        self.assertEqual(img.size, (1000, 700))

    def test_vector_svg_barcode_generation(self):
        """Test pure vector SVG barcode generator"""
        from odoo.addons.qba.models.barcode_svg import generate_barcode_svg_string
        svg = generate_barcode_svg_string('BOM.TEST.001', height_mm=10.0, show_text=True)
        self.assertIsNotNone(svg)
        self.assertIn('<svg', svg)
        self.assertIn('<rect', svg)
        self.assertIn('BOM.TEST.001', svg)

    def test_vector_direct_print_pdf_action(self):
        """Test action_print_pdf generating vector report action and dynamic paperformat"""
        default_fmt = self.env['qba.product.label.format'].search([('is_default', '=', True)], limit=1)
        action = self.product.open_label_wizard()
        wizard = self.env['qba.product.label.wizard'].with_context(action.get('context')).create({
            'format_id': default_fmt.id,
            'qty_to_print': 2,
        })
        print_res = wizard.action_print_pdf()
        self.assertEqual(print_res.get('type'), 'ir.actions.report')
        self.assertEqual(print_res.get('report_name'), 'qba.report_product_label_vector_template')

        # Check paperformat synchronization
        pf = default_fmt.paperformat_id
        self.assertTrue(bool(pf))
        self.assertEqual(pf.page_width, default_fmt.width_mm)
        self.assertEqual(pf.page_height, default_fmt.height_mm)

    def test_action_save_to_product(self):
        """Test action_save_to_product saving label directly to product.template.label_image and returning client reload"""
        action = self.product.open_label_wizard()
        wizard = self.env['qba.product.label.wizard'].with_context(action.get('context')).create({})
        res = wizard.action_save_to_product()
        self.assertEqual(res.get('type'), 'ir.actions.client')
        self.assertEqual(res.get('tag'), 'display_notification')
        self.assertEqual(res.get('params', {}).get('next', {}).get('tag'), 'reload')
        self.assertTrue(bool(self.product.label_image))

    def test_preview_html_live_wysiwyg(self):
        """Test preview_html contains exact millimeter dimensions and WYSIWYG elements"""
        action = self.product.open_label_wizard()
        wizard = self.env['qba.product.label.wizard'].with_context(action.get('context')).create({})
        self.assertTrue(bool(wizard.preview_html))
        self.assertIn(f"{wizard.format_id.width_mm:.1f}mm", wizard.preview_html)
        self.assertIn(f"{wizard.format_id.height_mm:.1f}mm", wizard.preview_html)
        self.assertIn('BOM.TEST.001', wizard.preview_html)

    def test_action_save_format_settings(self):
        """Test saving format layout customizations directly from the wizard"""
        action = self.product.open_label_wizard()
        wizard = self.env['qba.product.label.wizard'].with_context(action.get('context')).create({
            'format_product_name_font_size_pt': 14.0,
            'format_product_name_bold': False,
        })
        wizard.action_save_format_settings()
        self.assertEqual(wizard.format_id.product_name_font_size_pt, 14.0)
        self.assertFalse(wizard.format_id.product_name_bold)


