/** @odoo-module **/
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Assistant "Enregistrer un versement initial"
 *
 * Props :
 *   - leaseId (Number)
 *   - onClose (Function)
 *   - onSaved (Function) : appelée après création réussie
 *
 * Workflow :
 *   1. Charge les KPI financiers pour connaître les montants attendus
 *      (advance/caution/agency).
 *   2. Le gestionnaire saisit la date, la méthode, une référence commune.
 *   3. Deux modes de ventilation :
 *      - Auto : les 3 montants sont pré-remplis depuis les attentes
 *      - Manuel : le gestionnaire ajuste chaque ligne
 *   4. À la validation, 3 (ou moins) paiements sont créés en batch avec la
 *      même référence, permettant une traçabilité groupée.
 */
export class InitialPaymentWizard extends Component {
    static template = "civora_locations.InitialPaymentWizard";
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
            kpis: null,
            form: {
                date: new Date().toISOString().slice(0, 10),
                method: "virement",
                reference: "",
                note: "",
                advance_amount: 0,
                caution_amount: 0,
                agency_amount: 0,
            },
            manualMode: false,
        });

        onWillStart(async () => {
            await this._loadKpis();
        });
    }

    async _loadKpis() {
        this.state.loading = true;
        try {
            const kpis = await this.orm.call(
                "civora.lease",
                "get_financial_kpis",
                [[this.props.leaseId]]
            );
            this.state.kpis = kpis;
            // Pré-remplir avec ce qui reste à recevoir sur chaque type
            const lease = await this.orm.read(
                "civora.lease",
                [this.props.leaseId],
                ["advance_amount", "caution_amount", "agency_amount"]
            );
            const l = lease[0] || {};
            // Ce qui a déjà été reçu par type — on ne le prend pas en compte
            // dans cette v1 : on suppose que l'assistant sert à saisir la
            // totalité en une fois. Si des paiements partiels ont déjà été
            // saisis, le gestionnaire ajustera manuellement.
            this.state.form.advance_amount = l.advance_amount || 0;
            this.state.form.caution_amount = l.caution_amount || 0;
            this.state.form.agency_amount  = l.agency_amount  || 0;
        } catch (_) {
            this.state.kpis = null;
        }
        this.state.loading = false;
    }

    // ── Getters ──────────────────────────────────────────────────────
    get total() {
        return (Number(this.state.form.advance_amount) || 0)
             + (Number(this.state.form.caution_amount) || 0)
             + (Number(this.state.form.agency_amount)  || 0);
    }

    get expectedTotal() {
        const k = this.state.kpis;
        return k ? (k.initial_payment_expected || 0) : 0;
    }

    get remainingExpected() {
        const k = this.state.kpis;
        return k ? Math.max(0, (k.initial_payment_expected || 0) - (k.initial_payment_received || 0)) : 0;
    }

    get isValid() {
        return this.state.form.date
            && this.state.form.method
            && this.total > 0.01;
    }

    fmtAmount(v) {
        const n = Number(v) || 0;
        return n.toLocaleString("fr-FR").replace(/,/g, " ") + " FCFA";
    }

    // ── Actions ──────────────────────────────────────────────────────
    setField(field, ev) {
        this.state.form[field] = ev.target.value;
    }

    setAmount(field, ev) {
        this.state.form[field] = Number(ev.target.value) || 0;
    }

    toggleManualMode() {
        this.state.manualMode = !this.state.manualMode;
    }

    resetToExpected() {
        const lease = this.state.kpis;
        // Réinitialise depuis les valeurs par défaut chargées à l'ouverture
        // (on relit les champs du bail)
        this._loadKpis();
    }

    async save() {
        if (!this.isValid) {
            this.notification.add(
                "Vérifiez la date, la méthode et au moins un montant.",
                { type: "warning" }
            );
            return;
        }
        this.state.saving = true;
        try {
            const paymentsToCreate = [];
            const common = {
                lease_id: this.props.leaseId,
                date: this.state.form.date,
                method: this.state.form.method,
                status: "paid",
                source: "manual",
                reference: this.state.form.reference || false,
                note: this.state.form.note || false,
            };
            const a = Number(this.state.form.advance_amount) || 0;
            const c = Number(this.state.form.caution_amount) || 0;
            const g = Number(this.state.form.agency_amount)  || 0;
            if (a > 0.01) paymentsToCreate.push({ ...common, payment_type: "advance", amount: a });
            if (c > 0.01) paymentsToCreate.push({ ...common, payment_type: "caution", amount: c });
            if (g > 0.01) paymentsToCreate.push({ ...common, payment_type: "agency",  amount: g });
            if (!paymentsToCreate.length) {
                this.notification.add("Aucun montant à enregistrer.", { type: "warning" });
                this.state.saving = false;
                return;
            }
            await this.orm.create("civora.lease.payment", paymentsToCreate);
            this.notification.add(
                paymentsToCreate.length + " paiement(s) enregistré(s) — total "
                + this.fmtAmount(this.total),
                { type: "success" }
            );
            this.props.onSaved();
        } catch (e) {
            this.notification.add(
                "Erreur lors de l'enregistrement : " + (e.message || e),
                { type: "danger" }
            );
        }
        this.state.saving = false;
    }
}
