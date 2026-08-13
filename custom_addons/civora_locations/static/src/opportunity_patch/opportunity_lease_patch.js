import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { CivoraBadge } from "@civora_core/components/civora_kit";
import { LeaseDrawer } from "@civora_locations/leases/lease_drawer";

/**
 * Onglet contribué à la fiche Opportunité 360° via le registry
 * `civora_opportunity_360_tab`. Permet à l'agent :
 * - de voir les baux déjà générés depuis cette opportunité
 * - de créer un nouveau bail préfillé depuis les données de l'opportunité
 *   (uniquement si transaction = 'location')
 */
class OpportunityLeaseTab extends Component {
    static template = "civora_locations.OpportunityLeaseTab";
    static components = { CivoraBadge, LeaseDrawer };
    static props = {
        opportunityId: { type: [Number, Boolean] },
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            error: "",
            opportunity: null,
            leases: [],
            drawer: { open: false, opportunityId: false },
        });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        this.state.error = "";
        try {
            const [opp] = await this.orm.read(
                "civora.opportunity", [this.props.opportunityId],
                ["name", "transaction", "is_won", "is_lost", "property_id", "partner_id",
                 "agent_id", "expected_amount", "stage_id"]
            );
            if (!opp) {
                this.state.error = "Opportunité introuvable.";
                this.state.loading = false;
                return;
            }
            this.state.opportunity = opp;
            this.state.leases = await this.orm.searchRead(
                "civora.lease",
                [["opportunity_id", "=", this.props.opportunityId]],
                ["name", "tenant_id", "property_id", "rent", "state", "status",
                 "date_start", "date_end"],
                { order: "date_start desc" }
            );
        } catch (e) {
            this.state.error = "Impossible de charger les données.";
        }
        this.state.loading = false;
    }

    // ---- Helpers ----
    get isLocation() {
        return this.state.opportunity && this.state.opportunity.transaction === "location";
    }
    get isWon() {
        return this.state.opportunity && this.state.opportunity.is_won;
    }
    get canCreateLease() {
        return this.isLocation && !this.state.loading;
    }
    get shouldPromptCreate() {
        // Message vert : opportunité gagnée + location + pas de bail encore
        return this.isLocation && this.isWon && this.state.leases.length === 0;
    }
    get shouldWarnNotLocation() {
        return this.state.opportunity && !this.isLocation;
    }
    fmtMoney(n) {
        n = Number(n || 0);
        if (n >= 1e6) return (n / 1e6).toFixed(n % 1e6 ? 1 : 0).replace(".", ",") + " M FCFA";
        if (n >= 1e3) return Math.round(n / 1e3) + " k FCFA";
        return n + " FCFA";
    }
    fmtDate(d) {
        if (!d) return "—";
        const [y, m, day] = String(d).split("-");
        return day && m && y ? `${day}/${m}/${y}` : d;
    }
    statusBadge(status) {
        const meta = {
            actif: { label: "Actif", variant: "success" },
            retard: { label: "Retard", variant: "danger" },
            expire_bientot: { label: "Expire bientôt", variant: "warning" },
            resilie: { label: "Résilié", variant: "neutral" },
        };
        return meta[status] || { label: "—", variant: "neutral" };
    }

    // ---- Actions ----
    openCreateLease() {
        this.state.drawer = {
            open: true,
            opportunityId: this.props.opportunityId,
        };
    }
    closeDrawer() {
        this.state.drawer = { open: false, opportunityId: false };
    }
    async onDrawerSaved() {
        this.closeDrawer();
        await this.load();
    }
    openLease(leaseId) {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.lease_360",
            params: { leaseId },
            target: "current",
        });
    }
}

// Contribution au registry des onglets opportunité 360°
registry.category("civora_opportunity_360_tab").add("civora_locations.lease", {
    id: "lease",
    label: "Bail",
    sequence: 60,
    Component: OpportunityLeaseTab,
});

export { OpportunityLeaseTab };
