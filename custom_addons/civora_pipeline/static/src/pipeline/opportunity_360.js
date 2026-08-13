import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";
import { CivoraAvatar, CivoraBadge } from "@civora_core/components/civora_kit";
import { OpportunityDrawer } from "./opportunity_drawer";
import { HistoryTab } from "./history_tab";
import { ActivitiesTab } from "./activities_tab";

const TRANSACTION_LABEL = { vente: "Vente", location: "Location", saisonnier: "Saisonnier" };
const FIELDS = [
    "name", "partner_id", "property_id", "transaction", "stage_id", "expected_amount",
    "probability", "score", "agent_id", "date_close", "description", "lead_id",
    "is_won", "is_lost", "create_date", "date_stage_updated", "date_won", "date_lost",
];

export class CivoraOpportunity360 extends Component {
    static template = "civora_pipeline.Opportunity360";
    static components = { CivoraStatCard, CivoraAvatar, CivoraBadge, OpportunityDrawer, HistoryTab, ActivitiesTab };
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        const params = (this.props.action && this.props.action.params) || {};
        this.opportunityId = Number(params.opportunityId) || false;
        this.origin = params.origin || null;
        this.contribTabs = registry
            .category("civora_opportunity_360_tab")
            .getAll()
            .slice()
            .sort((a, b) => (a.sequence || 100) - (b.sequence || 100));
        this.state = useState({
            loading: true,
            error: "",
            opp: null,
            stages: [],
            drawerOpen: false,
            activeTab: "details",
        });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        if (!this.opportunityId) {
            this.state.error = "Opportunité introuvable.";
            this.state.loading = false;
            return;
        }
        try {
            this.state.stages = await this.orm.searchRead(
                "civora.pipeline.stage", [], ["name", "code", "sequence", "is_won", "is_lost"],
                { order: "sequence, id" }
            );
            const [rec] = await this.orm.read("civora.opportunity", [this.opportunityId], FIELDS);
            if (!rec) {
                this.state.error = "Opportunité introuvable.";
            } else {
                this.state.opp = rec;
            }
        } catch (e) {
            this.state.error = "Impossible de charger l'opportunité.";
        }
        this.state.loading = false;
    }

    get opp() {
        return this.state.opp || {};
    }
    get currentStageId() {
        return this.opp.stage_id ? this.opp.stage_id[0] : false;
    }
    get currentStageSeq() {
        const s = this.state.stages.find((x) => x.id === this.currentStageId);
        return s ? s.sequence : 0;
    }
    get progressStages() {
        // etapes non-perdue pour le stepper
        return this.state.stages.filter((s) => !s.is_lost);
    }
    stageState(s) {
        if (s.id === this.currentStageId) return "current";
        if (s.sequence < this.currentStageSeq) return "done";
        return "todo";
    }
    get stageInfo() {
        const s = this.state.stages.find((x) => x.id === this.currentStageId);
        if (!s) return { label: "—", variant: "neutral" };
        if (s.is_won) return { label: s.name, variant: "success" };
        if (s.is_lost) return { label: s.name, variant: "danger" };
        return { label: s.name, variant: "info" };
    }

    // --- Navigation / actions -----------------------------------------
    goBack() {
        if (this.origin && this.origin.tag) {
            this.action.doAction({
                type: "ir.actions.client", tag: this.origin.tag,
                params: this.origin.params || {}, target: "current",
            });
        } else {
            this.action.doAction({ type: "ir.actions.client", tag: "civora.pipeline", target: "current" });
        }
    }
    get backLabel() {
        return this.origin && this.origin.label ? this.origin.label : "Pipeline";
    }
    async setStage(s) {
        await this.orm.write("civora.opportunity", [this.opportunityId], { stage_id: s.id });
        await this.load();
    }
    async advanceStage() {
        const ordered = this.state.stages.filter((s) => !s.is_lost);
        const idx = ordered.findIndex((s) => s.id === this.currentStageId);
        if (idx >= 0 && idx < ordered.length - 1) {
            await this.setStage(ordered[idx + 1]);
        }
    }
    async markLost() {
        const lost = this.state.stages.find((s) => s.is_lost);
        if (lost) await this.setStage(lost);
    }
    openEdit() {
        this.state.drawerOpen = true;
    }
    async closeDrawer(saved) {
        this.state.drawerOpen = false;
        if (saved) await this.load();
    }
    openContact() {
        if (!this.opp.partner_id) return;
        this.action.doAction({
            type: "ir.actions.client", tag: "civora.contact_360",
            params: {
                contactId: this.opp.partner_id[0],
                origin: { tag: "civora.opportunity_360", params: { opportunityId: this.opportunityId }, label: "Opportunité" },
            },
            target: "current",
        });
    }
    openProperty() {
        if (!this.opp.property_id) return;
        this.action.doAction({
            type: "ir.actions.client", tag: "civora.property_360",
            params: {
                propertyId: this.opp.property_id[0],
                origin: { tag: "civora.opportunity_360", params: { opportunityId: this.opportunityId }, label: "Opportunité" },
            },
            target: "current",
        });
    }

    // --- Helpers -------------------------------------------------------
    partnerLabel() {
        return this.opp.partner_id ? this.opp.partner_id[1] : "Sans contact";
    }
    propertyLabel() {
        return this.opp.property_id ? this.opp.property_id[1] : "—";
    }
    agentLabel() {
        return this.opp.agent_id ? this.opp.agent_id[1] : "—";
    }
    txLabel() {
        return TRANSACTION_LABEL[this.opp.transaction] || "—";
    }
    orDash(v) {
        return v || "—";
    }
    isRental() {
        return this.opp.transaction === "location" || this.opp.transaction === "saisonnier";
    }
    fmtMoney(n) {
        n = Number(n || 0);
        if (n >= 1e9) return (n / 1e9).toFixed(1).replace(".", ",") + " Md";
        if (n >= 1e6) return (n / 1e6).toFixed(n % 1e6 ? 1 : 0).replace(".", ",") + " M";
        if (n >= 1e3) return Math.round(n / 1e3) + " k";
        return "" + n;
    }
    amountLabel() {
        return this.fmtMoney(this.opp.expected_amount) + (this.isRental() ? " /mois" : "") + " FCFA";
    }
    daysOld() {
        if (!this.opp.create_date) return 0;
        const start = new Date(this.opp.create_date.replace(" ", "T")).getTime();
        // Pour une opportunite close, on borne la duree a la date de gain/perte.
        let end = Date.now();
        const closeDate = this.opp.date_won || this.opp.date_lost;
        if (closeDate) {
            end = new Date(closeDate.replace(" ", "T")).getTime();
        }
        return Math.max(0, Math.floor((end - start) / (24 * 3600 * 1000)));
    }
    get daysLabel() {
        // Suffixe explicite pour les opportunites closes.
        return this.daysOld() + " j" + (this.isClosed ? " (clôt.)" : "");
    }
    get isClosed() {
        return this.opp.is_won || this.opp.is_lost;
    }
    get tabList() {
        return [
            { id: "details", label: "Détails" },
            { id: "history", label: "Historique" },
            { id: "activities", label: "Activités" },
            ...this.contribTabs.map((t) => ({ id: t.id, label: t.label })),
        ];
    }
    get activeContrib() {
        return this.contribTabs.find((t) => t.id === this.state.activeTab) || null;
    }
    setTab(id) {
        this.state.activeTab = id;
    }
}

registry.category("actions").add("civora.opportunity_360", CivoraOpportunity360);
