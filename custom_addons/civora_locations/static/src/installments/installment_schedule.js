/** @odoo-module **/
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

// ─────────────────────────────────────────────────────────────────────────────
// Métadonnées d'affichage par état d'échéance
// ─────────────────────────────────────────────────────────────────────────────
const STATE_META = {
    covered_by_advance: { label: "Couvert par avance", icon: "check-circle",     variant: "info"    },
    paid:               { label: "Payé",               icon: "check-circle",     variant: "success" },
    partial:            { label: "Partiel",            icon: "adjust",           variant: "warning" },
    pending:            { label: "En attente",         icon: "clock-o",          variant: "neutral" },
    overdue:            { label: "En retard",          icon: "exclamation-triangle", variant: "danger" },
};

/**
 * Composant échéancier d'un bail.
 *
 * Props :
 *   - leaseId (Number) : ID du bail
 *   - compact (Boolean, default true) : mode compact = mois en cours + prochain
 *
 * Affiche 2 échéances en mode compact + un bouton "Voir tout l'échéancier"
 * qui ouvre un drawer plein écran avec toutes les échéances.
 */
export class InstallmentSchedule extends Component {
    static template = "civora_locations.InstallmentSchedule";
    static props = {
        leaseId: Number,
        compact: { type: Boolean, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            compactItems: [],       // 2 échéances : mois en cours + prochain
            allItems: [],           // toutes les échéances (chargées à l'ouverture du drawer)
            drawerOpen: false,
            drawerLoading: false,
            regenerating: false,
            hasSchedule: false,
        });

        onWillStart(async () => {
            await this._loadCompact();
        });
    }

    // ── Chargement ────────────────────────────────────────────────────
    async _loadCompact() {
        this.state.loading = true;
        try {
            const items = await this.orm.call(
                "civora.lease",
                "get_installments_data",
                [[this.props.leaseId], "compact"]
            );
            this.state.compactItems = items || [];
            this.state.hasSchedule = (items || []).length > 0;
        } catch (e) {
            this.state.compactItems = [];
            this.state.hasSchedule = false;
        }
        this.state.loading = false;
    }

    async _loadAll() {
        this.state.drawerLoading = true;
        try {
            const items = await this.orm.call(
                "civora.lease",
                "get_installments_data",
                [[this.props.leaseId], "all"]
            );
            this.state.allItems = items || [];
        } catch (e) {
            this.state.allItems = [];
        }
        this.state.drawerLoading = false;
    }

    // ── Actions ───────────────────────────────────────────────────────
    async openAllDrawer() {
        this.state.drawerOpen = true;
        await this._loadAll();
    }

    closeDrawer() {
        this.state.drawerOpen = false;
    }

    async regenerateSchedule() {
        this.state.regenerating = true;
        try {
            await this.orm.call(
                "civora.lease",
                "action_regenerate_installments",
                [[this.props.leaseId]]
            );
            await this._loadCompact();
            if (this.state.drawerOpen) await this._loadAll();
            this.notification.add("Échéancier régénéré.", { type: "success" });
        } catch (e) {
            this.notification.add("Erreur : " + (e.message || e), { type: "danger" });
        }
        this.state.regenerating = false;
    }

    // ── Helpers ───────────────────────────────────────────────────────
    stateMeta(stateKey) {
        return STATE_META[stateKey] || STATE_META.pending;
    }

    fmtAmount(v) {
        const n = Number(v) || 0;
        return n.toLocaleString("fr-FR").replace(/,/g, " ") + " FCFA";
    }

    fmtDate(iso) {
        if (!iso) return "";
        const d = new Date(iso + "T00:00:00");
        const dd = String(d.getDate()).padStart(2, "0");
        const mm = String(d.getMonth() + 1).padStart(2, "0");
        return `${dd}/${mm}/${d.getFullYear()}`;
    }

    overdueLabel(days) {
        if (!days || days <= 0) return "";
        if (days === 1) return "1 jour de retard";
        return `${days} jours de retard`;
    }

    get compactCount() {
        return this.state.compactItems.length;
    }

    get allCount() {
        return this.state.allItems.length;
    }

    get overdueTotal() {
        return this.state.allItems.filter(i => i.state === 'overdue').length;
    }

    get paidTotal() {
        return this.state.allItems.filter(i =>
            i.state === 'paid' || i.state === 'covered_by_advance'
        ).length;
    }
}
