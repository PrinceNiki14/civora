/** @odoo-module **/
/**
 * Modales du module Workflows.
 *
 * NOTE D'ARCHITECTURE : les quatre modales (builder, bibliotheque de
 * templates, apercu, test) vivent volontairement dans ce fichier deja
 * declare au manifeste. Le serveur Odoo garde le manifeste en memoire :
 * ajouter un nouveau fichier d'asset a chaud casse tout le backend tant
 * qu'il n'a pas redemarre. On enrichit donc les fichiers existants.
 */
import { Component, useState, onWillStart, onWillUnmount, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CivoraDrawer } from "@civora_core/components/civora_drawer";

export const STEP_KINDS = [
    { value: "declencheur", label: "Déclencheur", icon: "fa-bolt" },
    { value: "delai", label: "Délai", icon: "fa-clock-o" },
    { value: "condition", label: "Condition", icon: "fa-code-fork" },
    { value: "action", label: "Action", icon: "fa-cog" },
    { value: "action_ia", label: "Action IA", icon: "fa-magic" },
    { value: "notification", label: "Notification", icon: "fa-bell-o" },
];

export const WF_CATEGORIES = [
    { value: "locatif", label: "Locatif" },
    { value: "ventes_crm", label: "Ventes & CRM" },
    { value: "saisonnier", label: "Saisonnier" },
    { value: "comptabilite", label: "Comptabilité" },
    { value: "maintenance", label: "Maintenance" },
    { value: "reporting", label: "Reporting" },
];

export const WF_STATUSES = [
    { value: "actif", label: "Actif" },
    { value: "pause", label: "Pause" },
    { value: "brouillon", label: "Brouillon" },
];

export const TRIGGER_TYPES = [
    { value: "event", label: "Événement métier" },
    { value: "schedule", label: "Planification récurrente" },
    { value: "condition", label: "Condition / score IA" },
    { value: "manual", label: "Déclenchement manuel" },
];

let localSeq = 0;
function nextKey() {
    localSeq += 1;
    return "s" + localSeq;
}

/* ==================================================================== */
/*  BUILDER : creation / edition d'un workflow                          */
/* ==================================================================== */
export class WorkflowBuilderDialog extends Component {
    static template = "civora_workflows.WorkflowBuilderDialog";
    static components = { CivoraDrawer };
    static props = {
        workflowId: { optional: true },
        preset: { type: Object, optional: true },
        onSaved: Function,
        onClose: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.kinds = STEP_KINDS;
        this.categories = WF_CATEGORIES;
        this.statuses = WF_STATUSES;
        this.triggerTypes = TRIGGER_TYPES;
        this.state = useState({
            loading: true,
            saving: false,
            error: "",
            values: {
                title: "",
                trigger_description: "",
                category: "locatif",
                trigger_type: "event",
                status: "brouillon",
                description: "",
                time_saved_hours: 0,
            },
            steps: [],
        });
        onWillStart(() => this.load());
    }

    async load() {
        if (this.props.workflowId) {
            const [rec] = await this.orm.read("civora.workflow", [this.props.workflowId], [
                "title", "trigger_description", "category", "trigger_type",
                "status", "description", "time_saved_hours",
            ]);
            if (rec) {
                this.state.values = {
                    title: rec.title || "",
                    trigger_description: rec.trigger_description || "",
                    category: rec.category || "locatif",
                    trigger_type: rec.trigger_type || "event",
                    status: rec.status || "brouillon",
                    description: rec.description || "",
                    time_saved_hours: rec.time_saved_hours || 0,
                };
            }
            const steps = await this.orm.searchRead(
                "civora.workflow.step",
                [["workflow_id", "=", this.props.workflowId]],
                ["kind", "name", "detail", "sequence"],
                { order: "sequence, id" },
            );
            this.state.steps = steps.map((s) => ({
                key: nextKey(), kind: s.kind, name: s.name || "", detail: s.detail || "",
            }));
        } else if (this.props.preset) {
            const p = this.props.preset;
            this.state.values = {
                title: p.name || "",
                trigger_description: p.trigger_description || "",
                category: p.category || "locatif",
                trigger_type: p.trigger_type || "event",
                status: "brouillon",
                description: p.description || "",
                time_saved_hours: p.time_saved_hours || 0,
            };
            this.state.steps = (p.steps || []).map((s) => ({
                key: nextKey(), kind: s.kind, name: s.name || "", detail: s.detail || "",
            }));
        }
        if (!this.state.steps.length) {
            this.state.steps = [
                { key: nextKey(), kind: "declencheur", name: "", detail: "" },
            ];
        }
        this.state.loading = false;
    }

    get isEdit() {
        return !!this.props.workflowId;
    }

    get dialogTitle() {
        return this.isEdit ? "Modifier le workflow" : "Nouveau workflow";
    }

    get saveLabel() {
        return this.isEdit ? "Enregistrer" : "Créer le workflow";
    }

    /* ---- helpers de template (Number/String indisponibles en OWL) ---- */
    isCategory(v) { return `${this.state.values.category}` === `${v}`; }
    isStatus(v) { return `${this.state.values.status}` === `${v}`; }
    isTrigger(v) { return `${this.state.values.trigger_type}` === `${v}`; }
    isKind(step, v) { return `${step.kind}` === `${v}`; }
    stepIndex(step) { return this.state.steps.indexOf(step) + 1; }

    update(field, ev) {
        const v = ev.target.value;
        this.state.values[field] = field === "time_saved_hours" ? (parseInt(v, 10) || 0) : v;
    }

    updateStep(step, field, ev) {
        step[field] = ev.target.value;
    }

    addStep() {
        this.state.steps.push({ key: nextKey(), kind: "action", name: "", detail: "" });
    }

    removeStep(step) {
        const i = this.state.steps.indexOf(step);
        if (i >= 0) this.state.steps.splice(i, 1);
    }

    moveStep(step, delta) {
        const i = this.state.steps.indexOf(step);
        const j = i + delta;
        if (i < 0 || j < 0 || j >= this.state.steps.length) return;
        const arr = this.state.steps;
        [arr[i], arr[j]] = [arr[j], arr[i]];
    }

    get hasTrigger() {
        return this.state.steps.some((s) => s.kind === "declencheur" && (s.name || "").trim());
    }

    async save() {
        this.state.error = "";
        const v = this.state.values;
        if (!(v.title || "").trim()) {
            this.state.error = "Le nom du workflow est obligatoire.";
            return;
        }
        const steps = this.state.steps.filter((s) => (s.name || "").trim());
        if (!steps.length) {
            this.state.error = "Ajoutez au moins une étape nommée.";
            return;
        }
        if (v.status === "actif" && !this.hasTrigger) {
            this.state.error =
                "Un workflow actif doit comporter une étape « Déclencheur » nommée : " +
                "sans déclencheur il ne se lancerait jamais.";
            return;
        }
        this.state.saving = true;
        try {
            const id = await this.orm.call("civora.workflow", "save_workflow", [
                this.props.workflowId || false,
                { ...v },
                steps.map((s) => ({ kind: s.kind, name: s.name, detail: s.detail })),
            ]);
            this.notification.add(
                this.isEdit ? "Workflow mis à jour." : `Workflow « ${v.title} » créé.`,
                { type: "success" },
            );
            this.props.onSaved(id);
        } catch (e) {
            this.state.error = (e && e.data && e.data.message) || "Enregistrement impossible.";
            this.state.saving = false;
            throw e;
        }
    }
}

/* ==================================================================== */
/*  BIBLIOTHEQUE DE TEMPLATES                                           */
/* ==================================================================== */
export class WorkflowTemplatesDialog extends Component {
    static template = "civora_workflows.WorkflowTemplatesDialog";
    static components = { CivoraDrawer };
    static props = {
        templates: { type: Array },
        highlightIds: { type: Array, optional: true },
        onUse: Function,
        onCustomize: Function,
        onClose: Function,
    };

    setup() {
        this.state = useState({ category: "all" });
    }

    get categories() {
        return [{ value: "all", label: "Tous" }, ...WF_CATEGORIES];
    }

    isActiveCat(v) { return `${this.state.category}` === `${v}`; }

    setCategory(v) { this.state.category = v; }

    get filtered() {
        const list = this.props.templates || [];
        if (this.state.category === "all") return list;
        return list.filter((t) => t.category === this.state.category);
    }

    isSuggested(tpl) {
        return (this.props.highlightIds || []).includes(tpl.id);
    }
}

/* ==================================================================== */
/*  APERCU D'UN WORKFLOW                                                */
/* ==================================================================== */
export class WorkflowViewDialog extends Component {
    static template = "civora_workflows.WorkflowViewDialog";
    static components = { CivoraDrawer };
    static props = {
        workflow: { type: Object },
        onOpenFull: Function,
        onClose: Function,
    };

    get w() { return this.props.workflow; }

    resultClass(r) {
        return { succes: "ok", partiel: "warn", echec: "ko" }[r] || "ok";
    }

    resultIcon(r) {
        return { succes: "fa-check-circle", partiel: "fa-exclamation-circle", echec: "fa-times-circle" }[r]
            || "fa-check-circle";
    }
}

/* ==================================================================== */
/*  TEST PAS A PAS                                                      */
/* ==================================================================== */
export class WorkflowTestDialog extends Component {
    static template = "civora_workflows.WorkflowTestDialog";
    static components = { CivoraDrawer };
    static props = {
        workflowId: { type: Number },
        title: { type: String },
        onDone: Function,
        onClose: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.timers = [];
        // Garde-fou : OWL peut rejouer onWillStart si le rendu initial est
        // annule puis relance (fiber cancel). Sans ce verrou, une seule
        // ouverture de la modale journaliserait deux executions.
        this.started = false;
        this.state = useState({
            steps: [],
            done: 0,
            finished: false,
            error: "",
        });
        onWillStart(() => this.run());
        onWillUnmount(() => this.timers.forEach((t) => clearTimeout(t)));
    }

    async run() {
        if (this.started) return;
        this.started = true;
        let res;
        try {
            res = await this.orm.call("civora.workflow", "action_run_test", [[this.props.workflowId]]);
        } catch (e) {
            this.state.error = (e && e.data && e.data.message) || "Simulation impossible.";
            return;
        }
        this.state.steps = res.steps || [];
        // Rejoue la sequence pour l'utilisateur (l'execution est deja
        // journalisee cote serveur : l'animation ne fait qu'illustrer).
        this.state.steps.forEach((_s, i) => {
            this.timers.push(setTimeout(() => {
                this.state.done = i + 1;
                if (i + 1 === this.state.steps.length) {
                    this.state.finished = true;
                    this.notification.add(`Test réussi — « ${this.props.title} »`, { type: "success" });
                    this.props.onDone();
                }
            }, 450 * (i + 1)));
        });
    }

    isDone(idx) { return idx < this.state.done; }
    isCurrent(idx) { return idx === this.state.done; }

    stepStatus(idx) {
        if (idx < this.state.done) return "Étape exécutée avec succès";
        if (idx === this.state.done) return "En cours…";
        return "En attente";
    }
}
