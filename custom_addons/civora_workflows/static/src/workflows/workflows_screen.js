/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";
import { WorkflowDrawer } from "./workflow_drawer";

class CivoraWorkflowsScreen extends Component {
    static template = "civora_workflows.WorkflowsScreen";
    static components = { CivoraStatCard, WorkflowDrawer };
    static props = { "*": true };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            automations: [],
            kpis: {},
            topAutomation: {},
            iaSuggestions: {},
            drawerOpen: false,
            editId: false,
            searchQuery: "",
            filterStatus: "all",
            filterCategory: "all",
        });
        onWillStart(async () => {
            try {
                await this.load();
            } catch (e) {
                console.error("CivoraWorkflowsScreen load error:", e);
            }
        });
    }

    async load() {
        const [kpis, automations, topAutomation, iaSuggestions] = await Promise.all([
            this.orm.call("civora.workflow.template", "get_automations_kpis", []),
            this.orm.call("civora.workflow.template", "get_automations_list", []),
            this.orm.call("civora.workflow.template", "get_top_automation", []),
            this.orm.call("civora.workflow.template", "get_ia_suggestions", []),
        ]);
        this.state.kpis = kpis;
        this.state.automations = automations;
        this.state.topAutomation = topAutomation;
        this.state.iaSuggestions = iaSuggestions;
    }

    get dynamicSubtitle() {
        const k = this.state.kpis;
        const total = k.total_count || 0;
        const active = k.active_count || 0;
        const exec = this.fmtNum(k.executions_30d);
        return `${total} workflows · ${active} actifs · ${exec} executions cumulees`;
    }

    get filteredAutomations() {
        let list = this.state.automations;
        const q = (this.state.searchQuery || "").toLowerCase().trim();
        if (q) {
            list = list.filter(r =>
                (r.name || "").toLowerCase().includes(q) ||
                (r.trigger_description || "").toLowerCase().includes(q)
            );
        }
        if (this.state.filterStatus !== "all") {
            const wantActive = this.state.filterStatus === "active";
            list = list.filter(r => r.is_active === wantActive);
        }
        if (this.state.filterCategory !== "all") {
            list = list.filter(r => r.category === this.state.filterCategory);
        }
        return list;
    }

    get categories() {
        const cats = new Set();
        for (const r of this.state.automations) {
            if (r.category) cats.add(r.category);
        }
        return [...cats].sort();
    }

    onSearchInput(ev) {
        this.state.searchQuery = ev.target.value;
    }

    onFilterStatus(ev) {
        this.state.filterStatus = ev.target.value;
    }

    onFilterCategory(ev) {
        this.state.filterCategory = ev.target.value;
    }

    fmtNum(n) {
        if (!n) return "0";
        return ("" + n).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
    }

    async toggleActive(id) {
        await this.orm.call("civora.workflow.template", "action_toggle_active", [[id]]);
        await this.load();
    }

    async deleteAutomation(id) {
        await this.orm.unlink("civora.workflow.template", [id]);
        await this.load();
    }

    openDrawer() {
        this.state.editId = false;
        this.state.drawerOpen = true;
    }

    editAutomation(id) {
        this.state.editId = id;
        this.state.drawerOpen = true;
    }

    closeDrawer() {
        this.state.drawerOpen = false;
        this.state.editId = false;
    }

    async onSaved() {
        this.state.drawerOpen = false;
        this.state.editId = false;
        await this.load();
    }
}

registry.category("actions").add("civora.workflows", CivoraWorkflowsScreen);
