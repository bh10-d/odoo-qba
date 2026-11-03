/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { CustomProductPopup } from "@qba_pos/app/custom_product_popup/custom_product_popup";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    async addLineToOrder(vals, order, opts = {}, configure = true) {
        let product = vals.product_id;
        if (typeof product === "number" && this.data && this.data.models["product.product"]) {
            product = this.data.models["product.product"].get(product);
        }
        const isCustomProduct = product && (
            product.default_code === "SP_CHUA_CO_MA" ||
            (this.config.custom_manual_product_id && product.id === this.config.custom_manual_product_id.id)
        );

        if (isCustomProduct && !vals.custom_product_configured) {
            return await this.openCustomProductDialog(order, vals, opts, configure);
        }
        return await super.addLineToOrder(...arguments);
    },

    async openCustomProductDialog(order = null, vals = {}, opts = {}, configure = true) {
        let manualProduct = vals.product_id;
        if (typeof manualProduct === "number" && this.models && this.models["product.product"]) {
            manualProduct = this.models["product.product"].get(manualProduct);
        }
        if (!manualProduct && this.models && this.models["product.product"]) {
            manualProduct = this.models["product.product"].find(
                (p) => p.default_code === "SP_CHUA_CO_MA"
            );
        }
        if (!manualProduct && this.config.custom_manual_product_id && this.models && this.models["product.product"]) {
            manualProduct = this.models["product.product"].get(this.config.custom_manual_product_id.id);
        }

        if (!manualProduct) {
            this.dialog.add(AlertDialog, {
                title: _t("Chua Tim Thay San Pham"),
                body: _t("He thong chua tim thay ma san pham 'SP_CHUA_CO_MA' de ban hang nhap tay. Vui long kiem tra lai cau hinh!"),
            });
            return false;
        }

        const payload = await makeAwaitable(this.dialog, CustomProductPopup, {
            title: _t("Nhap Hang Chua Co Ma [Nhap Tay]"),
            initialName: vals.full_product_name || "",
            initialQty: vals.qty || 1,
            initialPrice: vals.price_unit || 0,
            initialNotes: vals.customer_note || "",
        });

        if (!payload || !payload.name) {
            return false;
        }

        const targetOrder = order || this.get_order() || this.add_new_order();
        const line = await super.addLineToOrder({
            ...vals,
            product_id: manualProduct,
            qty: payload.qty,
            price_unit: payload.price,
            price_type: "manual",
            full_product_name: payload.name,
            customer_note: payload.notes,
            custom_product_configured: true,
            is_custom_manual_line: true,
        }, targetOrder, opts, false);

        if (line) {
            line.full_product_name = payload.name;
            line.is_custom_manual_line = true;
            if (payload.notes) {
                line.set_customer_note(payload.notes);
            }
        }

        // Luu vao cache pos.custom.product.history tren frontend
        if (this.models && this.models["pos.custom.product.history"]) {
            const cleanName = payload.name.trim();
            const existing = this.models["pos.custom.product.history"].find(
                (h) => (h.name || "").toLowerCase() === cleanName.toLowerCase()
            );
            if (existing) {
                existing.use_count = (existing.use_count || 1) + 1;
                existing.last_price = payload.price;
            } else {
                this.models["pos.custom.product.history"].create({
                    id: -Math.floor(Math.random() * 100000),
                    name: cleanName,
                    last_price: payload.price,
                    use_count: 1,
                    notes: payload.notes,
                });
            }
        }
        return line;
    },
});

