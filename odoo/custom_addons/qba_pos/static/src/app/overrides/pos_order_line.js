/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";

patch(PosOrderline.prototype, {
    setup(vals) {
        super.setup(...arguments);
        if (vals && vals.is_custom_manual_line !== undefined) {
            this.is_custom_manual_line = vals.is_custom_manual_line;
        }
        if (vals && vals.full_product_name) {
            this.full_product_name = vals.full_product_name;
        }
    },
    set_full_product_name() {
        if (this.is_custom_manual_line && this.full_product_name) {
            return;
        }
        super.set_full_product_name(...arguments);
    },
    get_full_product_name() {
        return this.full_product_name || super.get_full_product_name();
    },
});

