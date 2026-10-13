{
    "name": "Phụ tùng ô tô QBA",
    "version": "1.0",
    "author": "FACT",
    "license": "LGPL-3",
    "category": "Inventory",
    "depends": ["base", "product", "stock", "purchase", "sale_management"],
    "data": [
        "security/ir.model.access.csv",
        "views/product_oe_code_views.xml",
        "views/product_web_link_wizard_views.xml",
        "views/product_template_views.xml",
        "views/product_compare_wizard_views.xml",
        "views/brand_views.xml",
        "views/engine_views.xml",
        "views/gearbox_views.xml",
        "views/vehicle_views.xml",
        "views/product_supplierinfo_views.xml",
        "views/product_label_wizard_views.xml",
        "views/product_image_wizard_views.xml",
        "views/product_web_batch_sync_wizard_views.xml",
        "views/product_web_batch_unlink_wizard_views.xml",
        "views/res_config_settings_views.xml"
    ],
    "assets": {
        "web.assets_backend": [
            "qba/static/src/css/product_responsive.css",
            "qba/static/src/js/image_lightbox.js",
        ],
    },
    "installable": True,
    "application": False,
}
