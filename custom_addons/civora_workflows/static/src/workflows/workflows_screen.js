/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";
import {
    WorkflowBuilderDialog,
    WorkflowTemplatesDialog,
    WorkflowViewDialog,
    WorkflowTestDialog,
    WF_CATEGORIES,
} from "./workflow_drawer";

class CivoraWorkflowsScreen extends Component {
    static template = "civora_workflows.WorkflowsScreen";
    static components = {
        CivoraStatCard,
        WorkflowBuilderDialog,
        WorkflowTemplatesDialog,
        WorkflowViewDialog,
        WorkflowTestDialog,
    };
    static props = { "*": true };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.categories = WF_CATEGORIES;
        this.state = useState({
            loading: true,
            loadError: "",
            kpis: {},
            workflows: [],
            templates: [],
            insight: {},
            top: {},
            search: "",
            filterStatus: "all",
            filterCategory: "all",
            builderOpen: false,
            builderId: false,
            builderPreset: null,
            templatesOpen: false,
            viewId: false,
            testId: false,
            testTitle: "",
            confirmDeleteId: false,
            builderFocusId: false,
        });
        onWillStart(() => this.load());
    }

    async load() {
        try {
            const data = await this.orm.call("civora.workflow", "get_screen_data", []);
            this.state.kpis = data.kpis || {};
            this.state.workflows = data.workflows || [];
            this.state.templates = data.templates || [];
            this.state.insight = data.insight || {};
            this.state.top = data.top || {};
            this.state.loadError = "";
        } catch (e) {
            this.state.loadError =
                "Impossible de charger les workflows. Vérifiez que le module est à jour.";
            console.error("civora.workflows load error", e);
        }
        this.state.loading = false;
    }

    /* ---------------------------------------------------------------- */
    get subtitle() {
        const k = this.state.kpis;
        const total = k.total_count || 0;
        const active = k.active_count || 0;
        const runs = this.fmtNum(k.runs);
        const plural = total > 1 ? "s" : "";
        return `${total} workflow${plural} · ${active} actif${active > 1 ? "s" : ""} · ${runs} exécutions cumulées`;
    }

    fmtNum(n) {
        if (!n) return "0";
        return `${n}`.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
    }

    get filtered() {
        let list = this.state.workflows;
        const q = (this.state.search || "").toLowerCase().trim();
        if (q) {
            list = list.filter(
                (w) =>
                    (w.title || "").toLowerCase().includes(q) ||
                    (w.trigger_description || "").toLowerCase().includes(q) ||
                    (w.description || "").toLowerCase().includes(q),
            );
        }
        if (this.state.filterStatus !== "all") {
            list = list.filter((w) => w.status === this.state.filterStatus);
        }
        if (this.state.filterCategory !== "all") {
            list = list.filter((w) => w.category === this.state.filterCategory);
        }
        return list;
    }

    get previewWorkflow() {
        // L'apercu du builder illustre le workflow le plus execute :
        // c'est celui que l'agence a le plus interet a comprendre.
        const focus = this.state.builderFocusId;
        if (focus) {
            const w = this.state.workflows.find((x) => x.id === focus);
            if (w) return w;
        }
        if (this.state.top && this.state.top.id) {
            const w = this.state.workflows.find((x) => x.id === this.state.top.id);
            if (w) return w;
        }
        return this.state.workflows[0] || null;
    }

    get viewWorkflow() {
        return this.state.workflows.find((w) => w.id === this.state.viewId) || null;
    }

    get deleteWorkflow() {
        return this.state.workflows.find((w) => w.id === this.state.confirmDeleteId) || null;
    }

    isStatusFilter(v) { return `${this.state.filterStatus}` === `${v}`; }
    isCategoryFilter(v) { return `${this.state.filterCategory}` === `${v}`; }

    onSearch(ev) { this.state.search = ev.target.value; }
    onStatus(ev) { this.state.filterStatus = ev.target.value; }
    onCategory(ev) { this.state.filterCategory = ev.target.value; }

    /* ---------------------------------------------------------------- */
    openBuilder(id) {
        this.state.builderId = id || false;
        this.state.builderPreset = null;
        this.state.builderOpen = true;
    }

    closeBuilder() {
        this.state.builderOpen = false;
        this.state.builderId = false;
        this.state.builderPreset = null;
    }

    async onBuilderSaved(id) {
        this.closeBuilder();
        this.state.builderFocusId = id;
        await this.load();
    }

    openTemplates() { this.state.templatesOpen = true; }
    closeTemplates() { this.state.templatesOpen = false; }

    async useTemplate(tpl) {
        try {
            const id = await this.orm.call("civora.workflow", "create_from_template", [tpl.id, true]);
            this.state.templatesOpen = false;
            this.state.builderFocusId = id;
            this.notification.add(`Workflow « ${tpl.name} » déployé et activé.`, { type: "success" });
            await this.load();
        } catch (e) {
            this.notification.add(
                (e && e.data && e.data.message) || "Déploiement impossible.",
                { type: "danger" },
            );
        }
    }

    customizeTemplate(tpl) {
        this.state.templatesOpen = false;
        this.state.builderId = false;
        this.state.builderPreset = tpl;
        this.state.builderOpen = true;
    }

    openView(id) { this.state.viewId = id; }
    closeView() { this.state.viewId = false; }

    openTest(w) {
        this.state.testId = w.id;
        this.state.testTitle = w.title;
    }

    closeTest() {
        this.state.testId = false;
        this.state.testTitle = "";
    }

    async onTestDone() { await this.load(); }

    async toggleStatus(w) {
        try {
            await this.orm.call("civora.workflow", "action_toggle_status", [[w.id]]);
            await this.load();
        } catch (e) {
            this.notification.add(
                (e && e.data && e.data.message) || "Changement de statut impossible.",
                { type: "danger" },
            );
        }
    }

    askDelete(w) { this.state.confirmDeleteId = w.id; }
    cancelDelete() { this.state.confirmDeleteId = false; }

    async confirmDelete() {
        const id = this.state.confirmDeleteId;
        this.state.confirmDeleteId = false;
        await this.orm.unlink("civora.workflow", [id]);
        this.notification.add("Workflow supprimé.", { type: "success" });
        await this.load();
    }

    openFull(id) {
        this.state.viewId = false;
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.workflow_360",
            params: { workflow_id: id },
            target: "current",
        });
    }

    examineTop() {
        if (this.state.top && this.state.top.id) {
            this.openView(this.state.top.id);
        }
    }

    openSuggestions() {
        this.state.templatesOpen = true;
    }

    statusClass(status) {
        return `civora-wf-badge civora-wf-badge-${status}`;
    }

    toggleIcon(w) {
        return w.status === "actif" ? "fa-pause" : "fa-play";
    }

    toggleTitle(w) {
        return w.status === "actif" ? "Mettre en pause" : "Activer";
    }
}

registry.category("actions").add("civora.workflows", CivoraWorkflowsScreen);
