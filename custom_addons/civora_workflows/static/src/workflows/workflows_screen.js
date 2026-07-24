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
