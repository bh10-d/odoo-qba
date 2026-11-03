# -*- coding: utf-8 -*-
{
    "name": "QBA POS - Bán Hàng & Chăm Sóc Khách Hàng",
    "summary": "Tối ưu hóa điểm bán hàng POS, bán hàng chưa có trong kho, in bill bán lẻ và tự động gửi tin nhắn bảo hành qua Zalo",
    "description": """
        Module mở rộng tính năng Điểm Bán Hàng (POS) cho Phụ Tùng Ô Tô QBA:
        - Thiết lập cấu hình máy POS bán lẻ & mẫu bill bán hàng chuyên nghiệp.
        - Kích hoạt bán hàng POS hàng loạt cho toàn bộ danh mục sản phẩm.
        - Bán hàng chưa có mã trong kho: Nhập tên hàng bằng tay, gợi ý thông minh từ lịch sử (autocomplete), ghi nhớ tên sản phẩm chưa tạo, hỗ trợ công nợ và lưu vết chính xác trên hóa đơn.
        - Tự động gửi tin nhắn bảo hành qua Zalo OA / ZNS cho khách hàng ngay sau khi thanh toán đơn POS.
    """,
    "version": "1.0",
    "category": "Point of Sale",
    "author": "FACT",
    "license": "LGPL-3",
    "depends": [
        "base",
        "product",
        "stock",
        "point_of_sale",
        "qba",
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/pos_default_data.xml",
        "views/product_views.xml",
        "views/pos_config_views.xml",
        "views/pos_order_views.xml",
        "views/pos_custom_product_history_views.xml",
        "views/pos_zalo_message_views.xml",
        "views/res_config_settings_views.xml",
        "views/menu_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "qba_pos/static/src/scss/pos_custom.scss",
            "qba_pos/static/src/app/custom_product_button/custom_product_button.js",
            "qba_pos/static/src/app/custom_product_button/custom_product_button.xml",
            "qba_pos/static/src/app/custom_product_popup/custom_product_popup.js",
            "qba_pos/static/src/app/custom_product_popup/custom_product_popup.xml",
            "qba_pos/static/src/app/overrides/**/*",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
    "post_init_hook": "post_init_hook",
}

