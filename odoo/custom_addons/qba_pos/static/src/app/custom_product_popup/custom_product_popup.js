/** @odoo-module */

import { Component, onMounted, useRef, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { _t } from "@web/core/l10n/translation";

export class CustomProductPopup extends Component {
    static template = "qba_pos.CustomProductPopup";
    static components = { Dialog };
    static props = {
        title: { type: String, optional: true },
        initialName: { type: String, optional: true },
        initialQty: { type: Number, optional: true },
        initialPrice: { type: Number, optional: true },
        initialNotes: { type: String, optional: true },
        getPayload: Function,
        close: Function,
    };
    static defaultProps = {
        title: _t("Nhap Hang Chua Co Ma"),
        initialName: "",
        initialQty: 1,
        initialPrice: 0,
        initialNotes: "",
    };

    setup() {
        this.pos = usePos();
        this.nameInputRef = useRef("nameInput");
        this.state = useState({
            name: this.props.initialName || "",
            qty: this.props.initialQty || 1,
            price: this.props.initialPrice || 0,
            notes: this.props.initialNotes || "",
            showSuggestions: false,
            suggestions: [],
            selectedIndex: -1,
        });

        onMounted(() => {
            if (this.nameInputRef.el) {
                this.nameInputRef.el.focus();
                this.nameInputRef.el.select();
            }
        });
    }

    get allHistory() {
        if (this.pos.models && this.pos.models["pos.custom.product.history"]) {
            return this.pos.models["pos.custom.product.history"].getAll() || [];
        }
        return [];
    }

    onNameInput(ev) {
        const query = this.state.name.trim().toLowerCase();
        if (query.length >= 1) {
            const matches = this.allHistory.filter((item) => {
                const nameMatch = (item.name || "").toLowerCase().includes(query);
                const codeMatch = (item.code || "").toLowerCase().includes(query);
                return nameMatch || codeMatch;
            });
            // Sap xep uu tien so lan su dung cao nhat
            matches.sort((a, b) => (b.use_count || 0) - (a.use_count || 0));
            this.state.suggestions = matches.slice(0, 8);
            this.state.showSuggestions = this.state.suggestions.length > 0;
            this.state.selectedIndex = -1;
        } else {
            this.state.suggestions = [];
            this.state.showSuggestions = false;
        }
    }

    selectSuggestion(item) {
        this.state.name = item.name;
        if (item.last_price > 0 && (!this.state.price || this.state.price === 0)) {
            this.state.price = item.last_price;
        }
        if (item.notes && !this.state.notes) {
            this.state.notes = item.notes;
        }
        this.state.showSuggestions = false;
        this.state.suggestions = [];
    }

    onNameKeydown(ev) {
        if (this.state.showSuggestions && this.state.suggestions.length > 0) {
            if (ev.key === "ArrowDown") {
                ev.preventDefault();
                this.state.selectedIndex = Math.min(
                    this.state.selectedIndex + 1,
                    this.state.suggestions.length - 1
                );
                return;
            } else if (ev.key === "ArrowUp") {
                ev.preventDefault();
                this.state.selectedIndex = Math.max(this.state.selectedIndex - 1, 0);
                return;
            } else if (ev.key === "Enter" && this.state.selectedIndex >= 0) {
                ev.preventDefault();
                const item = this.state.suggestions[this.state.selectedIndex];
                if (item) {
                    this.selectSuggestion(item);
                }
                return;
            } else if (ev.key === "Escape") {
                this.state.showSuggestions = false;
                return;
            }
        }

        if (ev.key === "Enter") {
            ev.preventDefault();
            if (this.state.name.trim()) {
                this.confirm();
            }
        }
    }

    formatPrice(val) {
        return new Intl.NumberFormat("vi-VN").format(val || 0) + " d";
    }

    confirm() {
        if (!this.state.name.trim()) {
            return;
        }
        this.props.getPayload({
            name: this.state.name.trim(),
            qty: parseFloat(this.state.qty) || 1,
            price: parseFloat(this.state.price) || 0,
            notes: (this.state.notes || "").trim(),
        });
        this.props.close();
    }

    close() {
        this.props.close();
    }
}

