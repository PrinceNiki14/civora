import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";
import { CivoraBadge, CivoraAvatar } from "@civora_core/components/civora_kit";

/**
 * Onglet Locataires pour la fiche Contact 360°.
 * Vue consolidée des locataires actuels des biens du propriétaire.
 * Un locataire peut avoir plusieurs biens loués — affiché une seule
 * fois avec la liste de ses biens.
 */
export class ContactTenantsTab extends Component {
    static template = "civora_documents.ContactTenantsTab";
    static components = { CivoraStatCard, CivoraBadge, CivoraAvatar };
    static props = { contactId: { type: [Number, Boolean] } };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            data: null,
            backendError: "",
            backendTrace: [],
        });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        try {
            const res = await this.orm.call(
                "res.partner", "get_civora_tenants",
                [this.props.contactId]
            );
            this.state.data = res;
            if (res && res.error) {
                console.error("[CIVORA-TENANTS] backend error:", res.error);
                console.error("[CIVORA-TENANTS] trace:", res.error_trace);
                this.state.backendError = res.error;
                this.state.backendTrace = res.error_trace || [];
            } else {
                this.state.backendError = "";
                this.state.backendTrace = [];
            }
        } catch (e) {
            console.error("[CIVORA-TENANTS] load ERROR", e);
            this.state.data = null;
            this.state.backendError = (e && e.message) || String(e);
        }
        this.state.loading = false;
    }

    // ---- Actions ----
    openTenant(tenantId) {
        this.action.doAction({
            type: "ir.actions.client", tag: "civora.contact_360",
            params: { contactId: tenantId }, target: "current",
        });
    }
    openProperty(propertyId, ev) {
        if (ev) ev.stopPropagation();
        this.action.doAction({
            type: "ir.actions.client", tag: "civora.property_360",
            params: { propertyId: propertyId }, target: "current",
        });
    }
    openLease(leaseId, ev) {
        if (ev) ev.stopPropagation();
        if (!leaseId) return;
        this.action.doAction({
            type: "ir.actions.client", tag: "civora.lease_360",
            params: { leaseId: leaseId }, target: "current",
        });
    }

    // ---- Helpers ----
    fmtMoney(n) {
        n = Number(n || 0);
        return n.toLocaleString("fr-FR").replace(/\s/g, " ") + " FCFA";
    }
    fmtDate(d) {
        if (!d) return "—";
        const dt = new Date(d);
        if (isNaN(dt)) return d;
        const dd = String(dt.getDate()).padStart(2, "0");
        const mm = String(dt.getMonth() + 1).padStart(2, "0");
        return `${dd}/${mm}/${dt.getFullYear()}`;
    }

    // ---- KPIs ----
    get totalTenants() { return this.state.data ? this.state.data.total : 0; }
    get totalRentAll() {
        if (!this.state.data) return 0;
        return this.state.data.tenants.reduce((s, t) => s + (t.total_rent || 0), 0);
    }
    get totalBiensLoues() {
        if (!this.state.data) return 0;
        return this.state.data.tenants.reduce((s, t) => s + t.biens.length, 0);
    }
}

registry.category("civora_contact_360_tab").add("tenants", {
    id: "tenants",
    label: "Locataires",
    sequence: 50,
    Component: ContactTenantsTab,
});
