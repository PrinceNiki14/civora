import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";
import { CivoraBadge } from "@civora_core/components/civora_kit";
import { OpportunityDrawer } from "./opportunity_drawer";

const TRANSACTION_LABEL = { vente: "Vente", location: "Loc.", saisonnier: "Saison." };
const OPP_FIELDS = [
    "name", "partner_id", "property_id", "transaction", "stage_id",
    "expected_amount", "probability", "score", "agent_id", "create_date", "is_won", "is_lost",
];

export class CivoraPipelineScreen extends Component {
    static template = "civora_pipeline.Pipeline";
    static components = { CivoraStatCard, CivoraBadge, OpportunityDrawer };
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.draggedId = null;
        this.state = useState({
            loading: true,
            view: "kanban",
            search: "",
            drawerOpen: false,
            columns: [],
            list: [],
            stats: { count: 0, hot: 0, ventes: 0, locations: 0, transfo: 0, won: 0, avgScore: 0, avgDays: 0 },
        });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        this.stages = await this.orm.searchRead(
            "civora.pipeline.stage", [], ["name", "code", "sequence", "is_won", "is_lost", "fold"],
            { order: "sequence, id" }
        );
        this.opps = await this.orm.searchRead(
            "civora.opportunity", [], OPP_FIELDS, { order: "stage_sequence, priority desc, id desc" }
        );
        this.computeStats();
        this.rebuild();
        this.state.loading = false;
    }

    computeStats() {
        let ventes = 0, locations = 0, won = 0, hot = 0, scoreTot = 0, daysTot = 0, active = 0;
        for (const o of this.opps) {
            if ((o.score || 0) >= 80) hot++;
            scoreTot += o.score || 0;
            daysTot += this.daysOld(o);
            if (o.is_won) { won++; }
            if (o.is_lost) continue;
            active++;
            if (o.transaction === "vente") ventes += o.expected_amount || 0;
            else if (o.transaction === "location" || o.transaction === "saisonnier") locations += o.expected_amount || 0;
        }
        const total = this.opps.length;
        this.state.stats = {
            count: active,
            hot,
            ventes,
            locations,
            transfo: total ? Math.round((won / total) * 100) : 0,
            won,
            avgScore: total ? Math.round(scoreTot / total) : 0,
            avgDays: total ? Math.round(daysTot / total) : 0,
        };
    }

    rebuild() {
        const q = (this.state.search || "").trim().toLowerCase();
        const match = (o) => {
            if (!q) return true;
            const hay = [o.name, o.partner_id && o.partner_id[1], o.property_id && o.property_id[1]]
                .filter(Boolean).join(" ").toLowerCase();
            return hay.includes(q);
        };
        const opps = this.opps.filter(match);

        const byStage = {};
        for (const s of this.stages) byStage[s.id] = [];
        for (const o of opps) {
            const sid = o.stage_id ? o.stage_id[0] : false;
            if (sid && byStage[sid]) byStage[sid].push(o);
        }
        this.state.columns = this.stages.map((s) => {
            const cards = byStage[s.id] || [];
            return { stage: s, cards, total: cards.reduce((a, c) => a + (c.expected_amount || 0), 0) };
        });
        this.state.list = opps;
    }

    // --- Toolbar -------------------------------------------------------
    setView(v) {
        this.state.view = v;
    }
    onSearchInput(ev) {
        this.state.search = ev.target.value;
        this.rebuild();
    }
    openCreate() {
        this.state.drawerOpen = true;
    }
    async closeDrawer(saved) {
        this.state.drawerOpen = false;
        if (saved) await this.load();
    }
    goLeads() {
        this.action.doAction({ type: "ir.actions.client", tag: "civora.leads", target: "current" });
    }

    // --- Drag & drop ---------------------------------------------------
    onDragStart(opp) {
        this.draggedId = opp.id;
    }
    onDragOver(ev) {
        ev.preventDefault();
    }
    async onDrop(col) {
        const id = this.draggedId;
        this.draggedId = null;
        if (!id) return;
        const current = this.opps.find((x) => x.id === id);
        if (!current || (current.stage_id && current.stage_id[0] === col.stage.id)) return;
        await this.orm.write("civora.opportunity", [id], { stage_id: col.stage.id });
        await this.load();
    }

    openOpp(opp) {
        this.action.doAction({
            type: "ir.actions.client", tag: "civora.opportunity_360",
            params: { opportunityId: opp.id, origin: { tag: "civora.pipeline", label: "Pipeline" } },
            target: "current",
        });
    }

    // --- Helpers -------------------------------------------------------
    colClass(col) {
        let c = "civora-pl-col";
        if (col.stage.is_won) c += " is-won";
        if (col.stage.is_lost) c += " is-lost";
        return c;
    }
    stageLabel(o) {
        return o.stage_id ? o.stage_id[1] : "—";
    }
    partnerLabel(o) {
        return o.partner_id ? o.partner_id[1] : o.name;
    }
    propertyLabel(o) {
        return o.property_id ? o.property_id[1] : "—";
    }
    agentLabel(o) {
        return o.agent_id ? o.agent_id[1] : "—";
    }
    txLabel(o) {
        return TRANSACTION_LABEL[o.transaction] || "";
    }
    isRental(o) {
        return o.transaction === "location" || o.transaction === "saisonnier";
    }
    scoreTone(score) {
        return score >= 80 ? "success" : score >= 60 ? "warning" : "danger";
    }
    fmtMoney(n) {
        n = Number(n || 0);
        if (n >= 1e9) return (n / 1e9).toFixed(1).replace(".", ",") + " Md";
        if (n >= 1e6) return (n / 1e6).toFixed(n % 1e6 ? 1 : 0).replace(".", ",") + " M";
        if (n >= 1e3) return Math.round(n / 1e3) + " k";
        return "" + n;
    }
    kpiMoney(n) {
        return this.fmtMoney(n) + " FCFA";
    }
    amountLabel(o) {
        return this.fmtMoney(o.expected_amount) + (this.isRental(o) ? "/m" : "") + " FCFA";
    }
    daysOld(o) {
        if (!o.create_date) return 0;
        const d = new Date(o.create_date.replace(" ", "T")).getTime();
        return Math.max(0, Math.floor((Date.now() - d) / (24 * 3600 * 1000)));
    }
}

registry.category("actions").add("civora.pipeline", CivoraPipelineScreen);
