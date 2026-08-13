import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";
import { CivoraBadge } from "@civora_core/components/civora_kit";

const STATUS_META = {
    disponible: { label: "Disponible", variant: "info" },
    loue: { label: "Loué", variant: "success" },
    saisonnier: { label: "Saisonnier", variant: "warning" },
};

/**
 * Onglet Portefeuille pour la fiche Contact 360°.
 * Affiche les biens dont le contact est propriétaire, avec :
 *   - KPIs (Total, Loués, Loyer mensuel cumulé, Taux d'occupation)
 *   - Groupement optionnel (Aucun / Par statut / Par ville)
 *   - Cartes de biens avec statut, locataire actuel, loyer, bouton "Ouvrir"
 */
export class ContactPortfolioTab extends Component {
    static template = "civora_documents.ContactPortfolioTab";
    static components = { CivoraStatCard, CivoraBadge };
    static props = { contactId: { type: [Number, Boolean] } };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.groupOptions = [
            { value: "none", label: "Aucun" },
            { value: "status", label: "Par statut" },
            { value: "city", label: "Par ville" },
        ];
        this.state = useState({
            loading: true,
            groupBy: "none",
            data: null,
            expandedGroups: {},
            backendError: "",
            backendTrace: [],
        });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        try {
            const res = await this.orm.call(
                "res.partner", "get_civora_portfolio",
                [this.props.contactId, this.state.groupBy]
            );
            this.state.data = res;
            if (res && res.error) {
                console.error("[CIVORA-PORTFOLIO] backend error:", res.error);
                console.error("[CIVORA-PORTFOLIO] trace:", res.error_trace);
                this.state.backendError = res.error;
                this.state.backendTrace = res.error_trace || [];
            } else {
                this.state.backendError = "";
                this.state.backendTrace = [];
            }
            const exp = {};
            for (const g of (res.groups || [])) exp[g.id] = true;
            this.state.expandedGroups = exp;
        } catch (e) {
            console.error("[CIVORA-PORTFOLIO] load ERROR", e);
            this.state.data = null;
            this.state.backendError = (e && e.message) || String(e);
        }
        this.state.loading = false;
    }

    async onGroupByChange(ev) {
        this.state.groupBy = ev.target.value;
        await this.load();
    }
    toggleGroup(gid) { this.state.expandedGroups[gid] = !this.state.expandedGroups[gid]; }
    isExpanded(gid) { return this.state.expandedGroups[gid] !== false; }

    // ---- Actions ----
    openProperty(bienId) {
        this.action.doAction({
            type: "ir.actions.client", tag: "civora.property_360",
            params: { propertyId: bienId }, target: "current",
        });
    }
    openTenant(tenantId, ev) {
        if (ev) ev.stopPropagation();
        if (!tenantId) return;
        this.action.doAction({
            type: "ir.actions.client", tag: "civora.contact_360",
            params: { contactId: tenantId }, target: "current",
        });
    }

    // ---- Helpers ----
    statusMeta(s) { return STATUS_META[s] || { label: s || "—", variant: "neutral" }; }
    fmtMoney(n) {
        n = Number(n || 0);
        return n.toLocaleString("fr-FR").replace(/\s/g, " ") + " FCFA";
    }

    // ---- Computed KPIs ----
    get totalBiens() { return this.state.data ? this.state.data.total : 0; }
    get louesCount() {
        return this.state.data ? (this.state.data.by_status.loue || 0) : 0;
    }
    get occupancyRate() {
        const t = this.totalBiens;
        if (!t) return "0%";
        return Math.round(this.louesCount / t * 100) + "%";
    }
    get totalRent() {
        return this.state.data ? this.state.data.total_rent : 0;
    }
}

registry.category("civora_contact_360_tab").add("portfolio", {
    id: "portfolio",
    label: "Portefeuille",
    sequence: 40,
    Component: ContactPortfolioTab,
});
