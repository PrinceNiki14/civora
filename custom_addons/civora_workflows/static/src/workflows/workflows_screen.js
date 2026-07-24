/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";
import { WorkflowDrawer } from "./workflow_drawer";

const STATE_LABELS = {
    brouillon: "Brouillon",
    en_cours: "En cours",
    en_pause: "En pause",
    termine: "Termine",
    annule: "Annule",
};

const CATEGORY_LABELS = {
    vente: "Vente",
    location: "Location",
    gestion: "Gestion",
    administratif: "Admin",
};

const PRIORITY_LABELS = {
    normal: "Normal",
    urgent: "Urgent",
    critique: "Critique",
};

class CivoraWorkflowsScreen extends Component {
    static template = "civora_workflows.WorkflowsScreen";
    static components = { CivoraStatCard, WorkflowDrawer };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            workflows: [],
            kpis: {},
            filter: "all",
            search: "",
            drawerOpen: false,
        });
        onWillStart(() => this.load());
    }

    async load() {
        const [kpis, workflows] = await Promise.all([
            this.orm.call("civora.workflow", "get_workflows_kpis", []),
            this.orm.searchRead("civora.workflow", [], [
                "name", "title", "template_id", "state", "category",
                "priority", "assigned_to", "start_date", "deadline",
                "completed_date", "progress", "step_count", "completed_steps",
            ], { order: "create_date desc", limit: 200 }),
        ]);
        this.state.kpis = kpis;
        this.state.workflows = workflows;
    }

    get filteredWorkflows() {
        let list = this.state.workflows;
        const f = this.state.filter;
        if (f === "en_cours") list = list.filter(r => r.state === "en_cours");
        else if (f === "brouillon") list = list.filter(r => r.state === "brouillon");
        else if (f === "en_pause") list = list.filter(r => r.state === "en_pause");
        else if (f === "termine") list = list.filter(r => r.state === "termine");
        else if (f === "annule") list = list.filter(r => r.state === "annule");
        if (this.state.search) {
            const q = this.state.search.toLowerCase();
            list = list.filter(r =>
                (r.title || "").toLowerCase().includes(q) ||
                (r.name || "").toLowerCase().includes(q) ||
                (r.template_id && r.template_id[1] || "").toLowerCase().includes(q)
            );
        }
        return list;
    }

    setFilter(f) { this.state.filter = f; }
    onSearch(ev) { this.state.search = ev.target.value; }

    stateLabel(s) { return STATE_LABELS[s] || s; }
    stateClass(s) {
        const m = {
            brouillon: "muted",
            en_cours: "info",
            en_pause: "warning",
            termine: "success",
            annule: "danger",
        };
        return m[s] || "";
    }
    categoryLabel(s) { return CATEGORY_LABELS[s] || s; }
    categoryClass(s) {
        const m = { vente: "accent", location: "info", gestion: "primary", administratif: "violet" };
        return m[s] || "";
    }
    priorityLabel(s) { return PRIORITY_LABELS[s] || s; }
    priorityClass(s) {
        const m = { normal: "muted", urgent: "warning", critique: "danger" };
        return m[s] || "";
    }

    progressPercent(w) { return Math.round(w.progress || 0); }
    progressLabel(w) { return (w.completed_steps || 0) + "/" + (w.step_count || 0); }

    openDrawer() { this.state.drawerOpen = true; }
    closeDrawer() { this.state.drawerOpen = false; }
    async onSaved() {
        this.state.drawerOpen = false;
        await this.load();
    }

    openDetail(id) {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.workflow_360",
            params: { workflow_id: id },
        });
    }
}

registry.category("actions").add("civora.workflows", CivoraWorkflowsScreen);
