/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { unaccent } from "@web/core/utils/strings";

patch(ProductScreen.prototype, {
    getProductsBySearchWord(searchWord) {
        if (!searchWord || !searchWord.trim()) {
            return this.pos.selectedCategory?.id
                ? this.getProductsByCategory(this.pos.selectedCategory)
                : this.products;
        }

        const words = unaccent(searchWord.trim().toLowerCase(), false);
        const products = this.pos.selectedCategory?.id
            ? this.getProductsByCategory(this.pos.selectedCategory)
            : this.products;

        const matching = [];
        for (const p of products) {
            const cleanStr = p.cleanSearchString || unaccent((p.searchString || "").toLowerCase(), false);
            const idx = cleanStr.indexOf(words);
            if (idx !== -1) {
                matching.push({ product: p, index: idx, name: cleanStr });
            }
        }

        // Sap xep nhanh dua tren vi tri trung khop va ten ma khong phai goi lai unaccent hang van lan
        matching.sort((a, b) => a.index - b.index || a.name.localeCompare(b.name));
        return matching.map((m) => m.product);
    },
});

