/** @odoo-module **/
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Composant : Résumé financier consolidé du bail
 *
 * Props :
 *   - leaseId (Number) : ID du bail
 *
 * Affiche 4 KPI + un bloc "prochaine échéance" + un bloc "versements initiaux".
 */
export class FinanceOverview extends Component {
    static template = "civora_locations.FinanceOverview";
    static props = {
        leaseId: Number,
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            loading: true,
            kpis: null,
        });

        onWillStart(async () => {
            await this._load();
        });
    }

    async _load() {
        this.state.loading = true;
        try {
            const kpis = await this.orm.call(
                "civora.lease",
                "get_financial_kpis",
                [[this.props.leaseId]]
            );
            this.state.kpis = kpis;
        } catch (_) {
            this.state.kpis = null;
        }
        this.state.loading = false;
    }

    // ── Formatage ─────────────────────────────────────────────────────
    fmtAmount(v) {
        const n = Number(v) || 0;
        const cur = (this.state.kpis && this.state.kpis.currency) || "FCFA";
        return n.toLocaleString("fr-FR").replace(/,/g, " ") + " " + cur;
    }

    fmtDate(iso) {
        if (!iso) return "";
        const d = new Date(iso + "T00:00:00");
        return `${String(d.getDate()).padStart(2,"0")}/${String(d.getMonth()+1).padStart(2,"0")}/${d.getFullYear()}`;
    }

    // ── Getters ────────────────────────────────────────────────────────
    get hasInitialPending() {
        const k = this.state.kpis;
        return k && k.initial_payment_pending > 0.01;
    }

    get initialPaymentComplete() {
        const k = this.state.kpis;
        return k && k.initial_payment_expected > 0
               && k.initial_payment_pending <= 0.01;
    }

    get hasOverdue() {
        const k = this.state.kpis;
        return k && k.overdue_count > 0;
    }
}
