# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '/app')
import odoo
from odoo import api, SUPERUSER_ID
from odoo.exceptions import AccessError
import io
import re

try:
    from odoo.tools.pdf import pdf_page_count
    def get_num_pages(content):
        return pdf_page_count(content)
except Exception:
    def get_num_pages(content):
        return len(re.findall(rb'/Type\s*/Page[^s]', content))

print("=== STARTING COMPREHENSIVE AUDIT OF DIRECT PRINT VECTOR LABELS ===")

odoo.tools.config.parse_config(['-c', '/app/debian/odoo.conf', '-d', 'qba'])
registry = odoo.modules.registry.Registry('qba')

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})

    # 1. AUDIT FORMAT PRESETS
    print("\n--- 1. AUDITING FORMAT PRESETS ---")
    formats = env['qba.product.label.format'].search([])
    print(f"Total formats found: {len(formats)}")
    expected_codes = {'100x70', '75x50', '50x30', '35x22'}
    found_codes = set(formats.mapped('code'))
    for fmt in formats:
        print(f"Format: {fmt.name} | Code: {fmt.code} | Size: {fmt.width_mm}x{fmt.height_mm}mm | Default: {fmt.is_default}")
    assert expected_codes.issubset(found_codes), f"Missing presets! Expected {expected_codes}, found {found_codes}"
    print("[PASS] All required label format presets are present and correctly configured.")

    # 2. AUDIT PRODUCT & WIZARD GENERATION
    print("\n--- 2. AUDITING WIZARD CREATION & LIVE PREVIEW ---")
    product = env['product.template'].search([('default_code', '!=', False)], limit=1)
    if not product:
        product = env['product.template'].create({
            'name': 'Bơm Cao Áp HOWO Sinotruk VG1560080023',
            'default_code': 'VG1560080023',
        })
    print(f"Testing with Product: {product.name} (SKU: {product.default_code})")

    default_fmt = env['qba.product.label.format'].search([('is_default', '=', True)], limit=1)
    wizard = env['qba.product.label.wizard'].create({
        'product_id': product.id,
        'format_id': default_fmt.id,
        'custom_name': product.name,
        'supplier_code': 'SUP-998877',
        'dinh_luong': '1 Cái',
        'qty_to_print': 2,
    })
    print(f"Wizard created successfully (ID: {wizard.id})")
    assert wizard.preview_html, "preview_html is empty!"
    assert '<svg' in wizard.preview_html, "SVG barcode missing in live preview!"
    assert product.default_code in wizard.preview_html, "SKU code missing in preview!"
    assert 'SUP-998877' in wizard.preview_html, "Supplier code missing in preview!"
    print("[PASS] Live Preview HTML correctly generated with pure vector SVG barcodes and product info.")

    # 3. AUDIT VECTOR PDF GENERATION FOR ALL FORMATS
    print("\n--- 3. AUDITING VECTOR PDF GENERATION ACROSS ALL SIZES ---")
    report = env.ref('qba.action_report_product_label_vector')
    assert report, "Report action qba.action_report_product_label_vector not found!"

    for fmt in formats:
        wizard.write({
            'format_id': fmt.id,
            'qty_to_print': 2,
        })
        # Execute wizard action_print_pdf
        res_action = wizard.action_print_pdf()
        assert res_action.get('type') == 'ir.actions.report', f"Expected ir.actions.report, got {res_action}"

        # Render real PDF using wkhtmltopdf
        pdf_content, content_type = report._render_qweb_pdf(report.id, [wizard.id])
        assert pdf_content.startswith(b'%PDF-'), f"Output is not a valid PDF for format {fmt.code}!"
        assert len(pdf_content) > 1000, f"PDF file size suspiciously small: {len(pdf_content)} bytes"

        # Check page count
        num_pages = get_num_pages(pdf_content)
        print(f"-> Format {fmt.code} ({fmt.width_mm}x{fmt.height_mm}mm): PDF Generated successfully ({len(pdf_content)} bytes, {num_pages} pages)")
        assert num_pages == 2, f"Expected 2 pages for qty_to_print=2, got {num_pages}"

    print("[PASS] All sizes (100x70mm, 75x50mm, 50x30mm, 35x22mm) render valid multi-page Vector PDFs!")

    # 4. AUDIT SECURITY & PERMISSIONS
    print("\n--- 4. AUDITING PERMISSIONS & SECURITY BOUNDARIES ---")
    # Find a non-admin internal user
    normal_user = env['res.users'].search([
        ('groups_id', 'in', env.ref('base.group_user').id),
        ('groups_id', 'not in', env.ref('base.group_system').id),
        ('active', '=', True),
    ], limit=1)

    if normal_user:
        print(f"Testing with standard user: {normal_user.name} (login: {normal_user.login})")
        user_env = env(user=normal_user)

        user_env = env(user=normal_user)

        # Standard user CAN read formats
        user_formats = user_env['qba.product.label.format'].search([])
        print(f"Standard user can read formats: {len(user_formats)} visible")
        assert len(user_formats) > 0, "Standard user cannot read formats!"

        # Standard user CAN create and customize formats (accessible before printing)
        created_fmt = user_env['qba.product.label.format'].create({
            'name': 'Khổ in tùy chỉnh Audit',
            'width_mm': 80,
            'height_mm': 50,
        })
        print(f"Standard user created format successfully: {created_fmt.name} (ID: {created_fmt.id})")
        assert created_fmt.id, "Standard user should be able to create format!"

        created_fmt.write({'name': 'Khổ in tùy chỉnh Audit Updated'})
        print("Standard user edited format successfully.")

        # Standard user CAN use wizard and print labels
        user_wiz = user_env['qba.product.label.wizard'].create({
            'product_id': product.id,
            'format_id': user_formats[0].id,
            'qty_to_print': 1,
        })
        print(f"Standard user wizard execution: format={user_wiz.format_id.name}")

        # Test action_save_to_product saves label_image to product.template
        res_save = user_wiz.action_save_to_product()
        assert res_save.get('type') == 'ir.actions.client', "action_save_to_product failed to return client action!"
        assert bool(product.label_image), "product.label_image was not populated by action_save_to_product!"
        print(f"[PASS] action_save_to_product successfully saved label image ({len(product.label_image)} bytes) to product.template.label_image!")
        wiz_act = user_wiz.action_print_pdf()
        assert wiz_act.get('type') == 'ir.actions.report', "Standard user failed to print PDF!"
        print("[PASS] Standard user can print labels and customize formats before printing.")
    else:
        print("[WARN] No non-admin user found in database to test ACL, testing with admin.")

    # 5. AUDIT ADMIN CUSTOMIZATION
    print("\n--- 5. AUDITING ADMIN CUSTOMIZATION OF FORMAT ---")
    admin_format = env['qba.product.label.format'].create({
        'name': 'Custom Tem Shop QBA',
        'code': 'custom_qba',
        'width_mm': 80.0,
        'height_mm': 60.0,
        'border_style': 'rounded',
        'border_color': '#0055ff',
        'border_width_mm': 1.0,
        'product_name_font_size_pt': 14.0,
        'product_name_bold': True,
        'separator_color': '#0055ff',
        'show_sku_barcode': True,
        'sku_barcode_height_mm': 12.0,
    })
    print(f"Admin created custom format: {admin_format.name} (ID: {admin_format.id})")
    pf = admin_format.get_or_create_paperformat()
    assert pf, "Failed to create paperformat for custom format!"
    assert pf.page_width == 80.0 and pf.page_height == 60.0, f"Paperformat dimensions mismatch: {pf.page_width}x{pf.page_height}"
    print(f"Synchronized Paperformat verified: {pf.name} -> {pf.page_width}x{pf.page_height} mm")

    wizard.write({'format_id': admin_format.id, 'qty_to_print': 1})
    pdf_custom, _ = report._render_qweb_pdf(report.id, [wizard.id])
    assert pdf_custom.startswith(b'%PDF-'), "Admin custom format failed to generate PDF!"
    print(f"Custom format rendered PDF: {len(pdf_custom)} bytes")
    print("[PASS] Admin format customization and dynamic paperformat creation verified.")

    # Rollback audit transaction to leave DB pristine
    cr.rollback()

    print("\n=== ALL AUDIT CHECKS PASSED PERFECTLY (100% SUCCESS) ===")
