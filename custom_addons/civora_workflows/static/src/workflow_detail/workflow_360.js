/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";

const STATE_LABELS = {
    brouillon: "Brouillon",
    en_cours: "En cours",
    en_pause: "En pause",
    termine: "Termine",
    annule: "Annule",
};

const STEP_LABELS = {
    a_faire: "A faire",
    en_cours: "En cours",
    termine: "Termine",
    bloque: "Bloque",
    annule: "Annule",
};

const ROLE_LABELS = {
    agent: "Agent",
    manager: "Manager",
    admin: "Admin",
    notaire: "Notaire",
    externe: "Externe",
};

const CATEGORY_LABELS = {
    vente: "Vente",
    location: "Location",
    gestion: "Gestion",
    administratif: "Administratif",
};

const PRIORITY_LABELS = {
    normal: "Normal",
    urgent: "Urgent",
    critique: "Critique",
};

class CivoraWorkflow360 extends Component {
    static template = "civora_workflows.Workflow360";
    static components = { CivoraStatCard };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.workflowId = this.props.action.params?.workflow_id;
        this.state = useState({
            workflow: null,
            steps: [],
            activeTab: "steps",
        });
        onWillStart(() => this.load());
    }

    async load() {
        if (!this.workflowId) return;
        const [wf] = await this.orm.read("civora.workflow", [this.workflowId], [
            "name", "title", "template_id", "state", "category", "priority",
            "assigned_to", "start_date", "deadline", "completed_date",
            "progress", "step_count", "completed_steps", "reference", "notes",
        ]);
        const steps = await this.orm.searchRead("civora.workflow.step", [
            ["workflow_id", "=", this.workflowId],
        ], [
            "name", "description", "sequence", "state", "assigned_to",
            "responsible_role", "deadline", "completed_date", "is_required", "notes",
        ], { order: "sequence, id" });
        this.state.workflow = wf;
        this.state.steps = steps;
    }

    goBack() {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.workflows",
        });
    }

    setTab(t) { this.state.activeTab = t; }

    stateLabel(s) { return STATE_LABELS[s] || s; }
    stateClass(s) {
        const m = { brouillon: "muted", en_cours: "info", en_pause: "warning", termine: "success", annule: "danger" };
        return m[s] || "";
    }
    stepLabel(s) { return STEP_LABELS[s] || s; }
    stepClass(s) {
        const m = { a_faire: "muted", en_cours: "info", termine: "success", bloque: "danger", annule: "muted" };
        return m[s] || "";
    }
    stepIcon(s) {
        const m = { a_faire: "fa-circle-o", en_cours: "fa-spinner fa-pulse", termine: "fa-check-circle", bloque: "fa-ban", annule: "fa-times-circle" };
        return m[s] || "fa-circle-o";
    }
    roleLabel(s) { return ROLE_LABELS[s] || s; }
    categoryLabel(s) { return CATEGORY_LABELS[s] || s; }
    priorityLabel(s) { return PRIORITY_LABELS[s] || s; }
    priorityClass(s) {
        const m = { normal: "muted", urgent: "warning", critique: "danger" };
        return m[s] || "";
    }

    progressPercent() {
        return Math.round(this.state.workflow?.progress || 0);
    }

    async doAction(method) {
        await this.orm.call("civora.workflow", method, [[this.workflowId]]);
        await this.load();
    }

    async stepAction(stepId, method) {
        await this.orm.call("civora.workflow.step", method, [[stepId]]);
        await this.load();
    }
}

registry.category("actions").add("civora.workflow_360", CivoraWorkflow360);
