/** @odoo-module **/
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const CATEGORY_LABELS = {
    damages:   "Dégradations",
    cleaning:  "Ménage / remise en état",
    arrears:   "Arriérés de loyer",
    utilities: "Charges impayées",
    other:     "Autre",
};

const STATE_META = {
    draft:     { label: "Brouillon",      variant: "neutral" },
    validated: { label: "Validée",        variant: "info"    },
    refunded:  { label: "Restituée",      variant: "success" },
    cancelled: { label: "Annulée",        variant: "danger"  },
};

/**
 * Composant restitution de caution en fin de bail.
 *
 * Props :
 *   - leaseId (Number)
 *   - onClose (Function)
 *   - onSaved (Function)
 */
export class DepositRefund extends Component {
    static template = "civora_locations.DepositRefund";
    static props = {
        leaseId: Number,
        onClose: Function,
        onSaved: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            saving: false,
            exists: false,
            refund: null,
            form: {
                date: new Date().toISOString().slice(0, 10),
                reason: "end_of_contract",
                note: "",
                lines: [],
            },
            cautionReceived: 0,
        });

        onWillStart(async () => {
            await this._load();
        });
    }

    async _load() {
        this.state.loading = true;
        try {
            const data = await this.orm.call(
                "civora.deposit.refund",
                "get_for_lease",
                [this.props.leaseId]
            );
            if (data.exists) {
                this.state.exists = true;
                this.state.refund = data.refund;
                this.state.form = {
                    date: data.refund.date || new Date().toISOString().slice(0, 10),
                    reason: data.refund.reason || "end_of_contract",
                    note: data.refund.note || "",
                    lines: data.refund.lines.map(l => ({
                        label: l.label,
                        category: l.category,
                        amount: l.amount,
                        note: l.note,
                    })),
                };
                this.state.cautionReceived = data.refund.caution_received || 0;
            } else {
                // Précharger le montant caution reçu depuis les KPI
                const kpis = await this.orm.call(
                    "civora.lease",
                    "get_financial_kpis",
                    [[this.props.leaseId]]
                );
                // Somme des paiements type caution
                const payments = await this.orm.searchRead(
                    "civora.lease.payment",
                    [
                        ["lease_id", "=", this.props.leaseId],
                        ["payment_type", "=", "caution"],
                        ["status", "in", ["paid", "partial"]],
                    ],
                    ["amount"]
                );
                this.state.cautionReceived = payments.reduce((s, p) => s + p.amount, 0);
            }
        } catch (_) {
            this.state.exists = false;
        }
        this.state.loading = false;
    }

    // ── Helpers ───────────────────────────────────────────────────────
    fmtAmount(v) {
        const n = Number(v) || 0;
        return n.toLocaleString("fr-FR").replace(/,/g, " ") + " FCFA";
    }

    stateMeta(s) {
        return STATE_META[s] || STATE_META.draft;
    }

    categoryLabel(c) {
        return CATEGORY_LABELS[c] || c;
    }

    get deductionsTotal() {
        return this.state.form.lines.reduce((s, l) => s + (Number(l.amount) || 0), 0);
    }

    get netAmount() {
        return Math.max(0, this.state.cautionReceived - this.deductionsTotal);
    }

    get isEditable() {
        return !this.state.exists || this.state.refund.state === 'draft';
    }

    // ── Actions sur les lignes ────────────────────────────────────────
    addLine() {
        this.state.form.lines.push({
            label: "",
            category: "damages",
            amount: 0,
            note: "",
        });
    }

    removeLine(idx) {
        this.state.form.lines.splice(idx, 1);
    }

    setLineField(idx, field, ev) {
        this.state.form.lines[idx][field] = ev.target.value;
    }

    setLineAmount(idx, ev) {
        this.state.form.lines[idx].amount = Number(ev.target.value) || 0;
    }

    setField(field, ev) {
        this.state.form[field] = ev.target.value;
    }

    // ── Actions serveur ───────────────────────────────────────────────
    async save() {
        if (!this.state.form.date) {
            this.notification.add("La date de restitution est requise.", { type: "warning" });
            return;
        }
        this.state.saving = true;
        try {
            if (this.state.exists) {
                // Update lines
                await this.orm.call(
                    "civora.deposit.refund",
                    "update_lines",
                    [[this.state.refund.id], this.state.form.lines]
                );
                // Update main fields
                await this.orm.write(
                    "civora.deposit.refund",
                    [this.state.refund.id],
                    {
                        date: this.state.form.date,
                        reason: this.state.form.reason,
                        note: this.state.form.note || false,
                    }
                );
            } else {
                await this.orm.call(
                    "civora.deposit.refund",
                    "create_for_lease",
                    [this.props.leaseId, {
                        date: this.state.form.date,
                        reason: this.state.form.reason,
                        note: this.state.form.note || false,
                        lines: this.state.form.lines,
                    }]
                );
            }
            this.notification.add("Restitution enregistrée.", { type: "success" });
            await this._load();
        } catch (e) {
            this.notification.add("Erreur : " + (e.message || e), { type: "danger" });
        }
        this.state.saving = false;
    }

    async validateRefund() {
        if (!this.state.exists) {
            this.notification.add("Enregistrez d'abord la restitution.", { type: "warning" });
            return;
        }
        try {
            await this.orm.call(
                "civora.deposit.refund",
                "action_validate",
                [[this.state.refund.id]]
            );
            this.notification.add("Restitution validée.", { type: "success" });
            await this._load();
        } catch (e) {
            this.notification.add("Erreur : " + (e.message || e), { type: "danger" });
        }
    }

    async markRefunded() {
        try {
            await this.orm.call(
                "civora.deposit.refund",
                "action_mark_refunded",
                [[this.state.refund.id]]
            );
            this.notification.add("Caution restituée.", { type: "success" });
            await this._load();
        } catch (e) {
            this.notification.add("Erreur : " + (e.message || e), { type: "danger" });
        }
    }

    async cancel() {
        try {
            await this.orm.call(
                "civora.deposit.refund",
                "action_cancel",
                [[this.state.refund.id]]
            );
            await this._load();
        } catch (e) {
            this.notification.add("Erreur : " + (e.message || e), { type: "danger" });
        }
    }

    async resetToDraft() {
        try {
            await this.orm.call(
                "civora.deposit.refund",
                "action_reset_to_draft",
                [[this.state.refund.id]]
            );
            await this._load();
        } catch (e) {
            this.notification.add("Erreur : " + (e.message || e), { type: "danger" });
        }
    }
}
