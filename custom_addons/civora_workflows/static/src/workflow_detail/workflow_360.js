/** @odoo-module **/
/**
 * Fiche complete d'un workflow.
 *
 * A noter : sur la demo Lovable, « Ouvrir la fiche complete » pointe vers
 * /workflows/<slug> qui re-affiche la liste (la route detail n'existe pas).
 * On ne reproduit pas ce bug : la fiche existe reellement ici, avec le
 * detail du graphe, le journal d'execution complet et les actions.
 */
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";
import { WorkflowBuilderDialog, WorkflowTestDialog } from "../workflows/workflow_drawer";

class CivoraWorkflow360 extends Component {
    static template = "civora_workflows.Workflow360";
    static components = { CivoraStatCard, WorkflowBuilderDialog, WorkflowTestDialog };
    static props = { "*": true };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.workflowId = this.props.action.params?.workflow_id;
        this.state = useState({
            loading: true,
            wf: null,
            history: [],
            tab: "steps",
            builderOpen: false,
            testOpen: false,
            confirmDelete: false,
        });
        onWillStart(() => this.load());
    }

    async load() {
        if (!this.workflowId) {
            this.state.loading = false;
            return;
        }
        const data = await this.orm.call("civora.workflow", "get_detail", [this.workflowId]);
        this.state.wf = data.workflow;
        this.state.history = data.history || [];
        this.state.loading = false;
    }

    get w() { return this.state.wf || {}; }

    setTab(t) { this.state.tab = t; }
    isTab(t) { return `${this.state.tab}` === `${t}`; }

    goBack() {
        this.action.doAction({ type: "ir.actions.client", tag: "civora.workflows", target: "current" });
    }

    resultClass(r) { return { succes: "ok", partiel: "warn", echec: "ko" }[r] || "ok"; }
    resultIcon(r) {
        return { succes: "fa-check-circle", partiel: "fa-exclamation-circle", echec: "fa-times-circle" }[r]
            || "fa-check-circle";
    }

    fmtNum(n) {
        if (!n) return "0";
        return `${n}`.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
    }

    async toggleStatus() {
        try {
            await this.orm.call("civora.workflow", "action_toggle_status", [[this.workflowId]]);
            await this.load();
        } catch (e) {
            this.notification.add(
                (e && e.data && e.data.message) || "Changement de statut impossible.",
                { type: "danger" },
            );
        }
    }

    openBuilder() { this.state.builderOpen = true; }
    closeBuilder() { this.state.builderOpen = false; }
    async onSaved() {
        this.state.builderOpen = false;
        await this.load();
    }

    openTest() { this.state.testOpen = true; }
    closeTest() { this.state.testOpen = false; }
    async onTestDone() { await this.load(); }

    askDelete() { this.state.confirmDelete = true; }
    cancelDelete() { this.state.confirmDelete = false; }
    async doDelete() {
        await this.orm.unlink("civora.workflow", [this.workflowId]);
        this.notification.add("Workflow supprimé.", { type: "success" });
        this.goBack();
    }

    async duplicate() {
        const id = await this.orm.call("civora.workflow", "action_duplicate", [[this.workflowId]]);
        this.notification.add("Copie créée en brouillon.", { type: "success" });
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.workflow_360",
            params: { workflow_id: id },
            target: "current",
        });
    }
}

registry.category("actions").add("civora.workflow_360", CivoraWorkflow360);
