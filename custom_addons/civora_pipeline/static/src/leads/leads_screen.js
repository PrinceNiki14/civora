import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";
import { CivoraAvatar, CivoraBadge, CivoraProgress } from "@civora_core/components/civora_kit";
import { LeadDrawer } from "./lead_drawer";

const STATUS_META = {
    nouveau: { label: "Nouveau", variant: "info" },
    a_qualifier: { label: "À qualifier", variant: "warning" },
    qualifie: { label: "Qualifié", variant: "success" },
    rejete: { label: "Rejeté", variant: "danger" },
};
const STATUS_FILTERS = [
    { id: "tous", label: "Toutes" },
    { id: "nouveau", label: "Nouveau" },
    { id: "a_qualifier", label: "À qualifier" },
    { id: "qualifie", label: "Qualifié" },
    { id: "rejete", label: "Rejeté" },
];
const TRANSACTION_LABEL = { vente: "Vente", location: "Location", saisonnier: "Saisonnier" };
const FIELDS = [
    "name", "partner_id", "contact_name", "email", "phone", "source_id",
    "status", "score", "transaction", "budget_min", "budget_max",
    "property_id", "agent_id", "opportunity_id", "create_date",
];

export class CivoraLeadsScreen extends Component {
    static template = "civora_pipeline.Leads";
    static components = { CivoraStatCard, CivoraAvatar, CivoraBadge, CivoraProgress, LeadDrawer };
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.statusFilters = STATUS_FILTERS;
        this.state = useState({
            loading: true,
            filter: "tous",
            selectedId: false,
            drawer: { open: false, leadId: false },
            stats: { new7: 0, toQualify: 0, qualifRate: 0, avgScore: 0 },
            funnel: { total: 0, a_qualifier: 0, qualifie: 0, rejete: 0 },
            sources: [],
            hotCount: 0,
        });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        this.leads = await this.orm.searchRead("civora.lead", [], FIELDS, { order: "score desc, create_date desc" });

        const now = Date.now();
        const weekAgo = now - 7 * 24 * 3600 * 1000;
        let new7 = 0, toQualify = 0, qualifie = 0, rejete = 0, aQualifier = 0, scoreTot = 0, hot = 0;
        const srcMap = {};
        for (const l of this.leads) {
            if (l.create_date && new Date(l.create_date.replace(" ", "T")).getTime() >= weekAgo) new7++;
            if (l.status === "a_qualifier") { toQualify++; aQualifier++; }
            if (l.status === "qualifie") qualifie++;
            if (l.status === "rejete") rejete++;
            scoreTot += l.score || 0;
            if ((l.score || 0) >= 85) hot++;
            const src = l.source_id ? l.source_id[1] : "Direct";
            srcMap[src] = (srcMap[src] || 0) + 1;
        }
        const total = this.leads.length;
        this.state.stats = {
            new7,
            toQualify,
            qualifRate: total ? Math.round((qualifie / total) * 100) : 0,
            avgScore: total ? Math.round(scoreTot / total) : 0,
        };
        this.state.funnel = { total, a_qualifier: aQualifier, qualifie, rejete };
        this.state.hotCount = hot;
        this.state.sources = Object.entries(srcMap)
            .map(([label, n]) => ({ label, n, pct: total ? Math.round((n / total) * 100) : 0 }))
            .sort((a, b) => b.n - a.n);

        if (!this.state.selectedId || !this.leads.find((l) => l.id === this.state.selectedId)) {
            const first = this.filteredLeads[0];
            this.state.selectedId = first ? first.id : false;
        }
        this.state.loading = false;
    }

    // --- Filtres / selection ------------------------------------------
    get filteredLeads() {
        if (this.state.filter === "tous") return this.leads;
        return this.leads.filter((l) => l.status === this.state.filter);
    }
    setFilter(id) {
        this.state.filter = id;
        const list = this.filteredLeads;
        if (!list.find((l) => l.id === this.state.selectedId)) {
            this.state.selectedId = list.length ? list[0].id : false;
        }
    }
    selectLead(l) {
        this.state.selectedId = l.id;
    }
    get selected() {
        return this.leads.find((l) => l.id === this.state.selectedId) || null;
    }

    // --- Actions -------------------------------------------------------
    async qualify(l) {
        await this.orm.call("civora.lead", "action_qualify", [[l.id]]);
        await this.load();
    }
    async reject(l) {
        await this.orm.call("civora.lead", "action_reject", [[l.id]]);
        await this.load();
    }
    openCreate() {
        this.state.drawer = { open: true, leadId: false };
    }
    async importVisits() {
        const n = await this.orm.call("civora.lead", "create_from_visit_requests", []);
        if (n > 0) {
            this.notification.add(`${n} demande(s) de visite importée(s) en piste.`, { type: "success" });
            await this.load();
        } else {
            this.notification.add("Aucune nouvelle demande de visite à importer.", { type: "info" });
        }
    }
    openEdit(l) {
        this.state.drawer = { open: true, leadId: l.id };
    }
    async closeDrawer(saved) {
        this.state.drawer = { open: false, leadId: false };
        if (saved) await this.load();
    }
    goPipeline() {
        this.action.doAction({ type: "ir.actions.client", tag: "civora.pipeline", target: "current" });
    }

    // --- Helpers -------------------------------------------------------
    statusMeta(l) {
        return STATUS_META[l.status] || { label: l.status || "—", variant: "neutral" };
    }
    sourceLabel(l) {
        return l.source_id ? l.source_id[1] : "Direct";
    }
    transactionLabel(l) {
        return TRANSACTION_LABEL[l.transaction] || "—";
    }
    agentLabel(l) {
        return l.agent_id ? l.agent_id[1] : "—";
    }
    contactLine(l) {
        const parts = [];
        if (l.transaction) parts.push(TRANSACTION_LABEL[l.transaction]);
        if (l.property_id) parts.push(l.property_id[1]);
        parts.push(this.budgetLabel(l));
        return parts.filter(Boolean).join(" · ");
    }
    fmtMoney(n) {
        n = Number(n || 0);
        if (n >= 1e9) return (n / 1e9).toFixed(1).replace(".", ",") + " Md";
        if (n >= 1e6) return (n / 1e6).toFixed(n % 1e6 ? 1 : 0).replace(".", ",") + " M";
        if (n >= 1e3) return Math.round(n / 1e3) + " k";
        return "" + n;
    }
    budgetLabel(l) {
        const mn = l.budget_min || 0;
        const mx = l.budget_max || 0;
        if (mn && mx) return this.fmtMoney(mn) + " – " + this.fmtMoney(mx) + " FCFA";
        if (mx) return "≤ " + this.fmtMoney(mx) + " FCFA";
        if (mn) return "≥ " + this.fmtMoney(mn) + " FCFA";
        return "Budget n.c.";
    }
    scoreTone(score) {
        return score >= 80 ? "success" : score >= 60 ? "warning" : "danger";
    }
    recommendation(score) {
        if (score >= 85) return "Piste très chaude — conversion immédiate recommandée.";
        if (score >= 60) return "Piste à qualifier — appel sortant sous 24h recommandé.";
        return "Piste faible — à cultiver via campagne de nurturing.";
    }
}

registry.category("actions").add("civora.leads", CivoraLeadsScreen);
