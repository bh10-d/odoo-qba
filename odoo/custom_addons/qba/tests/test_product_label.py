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
