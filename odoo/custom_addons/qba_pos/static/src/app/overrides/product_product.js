/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ProductProduct } from "@point_of_sale/app/models/product_product";
import { unaccent } from "@web/core/utils/strings";

patch(ProductProduct.prototype, {
    get cleanSearchString() {
        if (!this._cleanSearchString) {
            this._cleanSearchString = unaccent((this.searchString || "").toLowerCase(), false);
        }
        return this._cleanSearchString;
    },
});

