import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CivoraDrawer } from "@civora_core/components/civora_drawer";

export const PHASE_STATUSES = [
    { id: "planifiee", label: "Planifiée", variant: "neutral" },
    { id: "en_cours", label: "En cours", variant: "accent" },
    { id: "terminee", label: "Terminée", variant: "success" },
    { id: "en_retard", label: "En retard", variant: "danger" },
];

export const GUARANTEE_TYPES = [
    { id: "gfa", label: "GFA — Garantie financière d'achèvement" },
    { id: "do", label: "DO — Dommages-ouvrage" },
    { id: "rc", label: "RC — Responsabilité civile pro" },
    { id: "biennale", label: "Biennale (2 ans)" },
    { id: "decennale", label: "Décennale (10 ans)" },
    { id: "trc", label: "TRC — Tous risques chantier" },
    { id: "autre", label: "Autre" },
];

export const DOCUMENT_TYPES = [
    { id: "permis", label: "Permis de construire" },
    { id: "plan", label: "Plan" },
    { id: "brochure", label: "Brochure" },
    { id: "notice", label: "Notice descriptive" },
    { id: "garantie", label: "Garantie / assurance" },
    { id: "contrat", label: "Contrat" },
    { id: "autre", label: "Autre" },
];

/** Socle commun aux petites modales d'edition (phase, echeance, garantie...). */
class BaseRecordDialog extends Component {
    static components = { CivoraDrawer };
    static props = {
        programId: Number,
        recordId: { type: [Number, Boolean], optional: true },
        onClose: Function,
        onSaved: Function,
    };

    // A surcharger.
    get model() { return ""; }
    get fields() { return []; }
    get defaults() { return {}; }
    get title() { return ""; }
    get kicker() { return ""; }

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({ saving: false, values: { ...this.defaults } });
        onWillStart(async () => {
            await this.loadExtra();
            if (this.props.recordId) {
                const [rec] = await this.orm.read(this.model, [this.props.recordId], this.fields);
                if (rec) {
                    for (const key of Object.keys(this.state.values)) {
                        if (rec[key] === undefined) continue;
                        const cur = this.state.values[key];
                        if (rec[key] === false) {
                            this.state.values[key] = typeof cur === "number" ? 0
                                : (typeof cur === "boolean" ? false : "");
                        } else if (Array.isArray(rec[key])) {
                            this.state.values[key] = rec[key][0];
                        } else {
                            this.state.values[key] = rec[key];
                        }
                    }
                }
            }
        });
    }

    async loadExtra() {}

    get isEdit() {
        return !!this.props.recordId;
    }

    setField(key, ev) {
        const el = ev.target;
        if (el.type === "checkbox") {
            this.state.values[key] = el.checked;
        } else if (el.type === "number") {
            this.state.values[key] = el.value === "" ? 0 : Number(el.value);
        } else {
            this.state.values[key] = el.value;
        }
    }

    /** A surcharger pour valider avant enregistrement. Retourne un message ou null. */
    validate() { return null; }
    /** A surcharger pour transformer les valeurs avant ecriture. */
    prepare(vals) { return vals; }

    async save() {
        if (this.state.saving) return;
        const err = this.validate();
        if (err) {
            this.notification.add(err, { type: "warning" });
            return;
        }
        this.state.saving = true;
        try {
            const vals = this.prepare({ ...this.state.values });
            vals.program_id = this.props.programId;
            if (this.props.recordId) {
                await this.orm.write(this.model, [this.props.recordId], vals);
            } else {
                await this.orm.create(this.model, [vals]);
            }
            this.notification.add("Enregistré", { type: "success" });
            this.props.onSaved();
        } catch (e) {
            this.notification.add("Enregistrement impossible : " + (e.message || e), { type: "danger" });
            throw e;
        } finally {
            this.state.saving = false;
        }
    }
}

// ---------------------------------------------------------------------
// Phase de chantier
// ---------------------------------------------------------------------
export class PhaseDialog extends BaseRecordDialog {
    static template = "civora_programmes.PhaseDialog";
    get model() { return "civora.program.phase"; }
    get fields() {
        return ["name", "sequence", "date_start", "date_end_planned", "date_end_real",
                "progress", "status", "is_milestone", "notes"];
    }
    get defaults() {
        return {
            name: "", sequence: 1, date_start: "", date_end_planned: "", date_end_real: "",
            progress: 0, status: "planifiee", is_milestone: false, notes: "",
        };
    }
    get title() { return this.isEdit ? "Modifier la phase" : "Nouvelle phase"; }
    get kicker() { return "PLANNING CHANTIER"; }
    get statuses() { return PHASE_STATUSES; }

    validate() {
        return (this.state.values.name || "").trim() ? null : "Le libellé est obligatoire.";
    }
    prepare(vals) {
        vals.date_start = vals.date_start || false;
        vals.date_end_planned = vals.date_end_planned || false;
        vals.date_end_real = vals.date_end_real || false;
        return vals;
    }
}

// ---------------------------------------------------------------------
// Echeance VEFA
// ---------------------------------------------------------------------
export class MilestoneDialog extends BaseRecordDialog {
    static template = "civora_programmes.MilestoneDialog";
    get model() { return "civora.program.milestone"; }
    get fields() { return ["name", "sequence", "cumulative_pct", "phase_id", "notes"]; }
    get defaults() {
        return { name: "", sequence: 1, cumulative_pct: 0, phase_id: 0, notes: "" };
    }
    get title() { return this.isEdit ? "Modifier l'échéance" : "Nouvelle échéance"; }
    get kicker() { return "ÉCHÉANCIER VEFA"; }

    async loadExtra() {
        this.phases = await this.orm.searchRead(
            "civora.program.phase", [["program_id", "=", this.props.programId]],
            ["name"], { order: "sequence, id" }
        );
    }
    validate() {
        if (!(this.state.values.name || "").trim()) return "Le libellé est obligatoire.";
        const pct = Number(this.state.values.cumulative_pct);
        if (pct < 0 || pct > 100) return "Le pourcentage cumulé doit être compris entre 0 et 100.";
        return null;
    }
    prepare(vals) {
        vals.phase_id = vals.phase_id ? Number(vals.phase_id) : false;
        return vals;
    }
}

// ---------------------------------------------------------------------
// Garantie / assurance
// ---------------------------------------------------------------------
export class GuaranteeDialog extends BaseRecordDialog {
    static template = "civora_programmes.GuaranteeDialog";
    get model() { return "civora.program.guarantee"; }
    get fields() {
        return ["guarantee_type", "issuer", "policy_number", "amount", "date_start", "date_end", "notes"];
    }
    get defaults() {
        return {
            guarantee_type: "gfa", issuer: "", policy_number: "",
            amount: 0, date_start: "", date_end: "", notes: "",
        };
    }
    get title() { return this.isEdit ? "Modifier la garantie" : "Nouvelle garantie"; }
    get kicker() { return "GARANTIE / ASSURANCE"; }
    get types() { return GUARANTEE_TYPES; }

    validate() {
        return (this.state.values.issuer || "").trim() ? null : "L'émetteur est obligatoire.";
    }
    prepare(vals) {
        vals.date_start = vals.date_start || false;
        vals.date_end = vals.date_end || false;
        return vals;
    }
}

// ---------------------------------------------------------------------
// Document du dossier
// ---------------------------------------------------------------------
export class DocumentDialog extends BaseRecordDialog {
    static template = "civora_programmes.DocumentDialog";
    get model() { return "civora.program.document"; }
    get fields() { return ["name", "document_type", "url", "notes", "file_name"]; }
    get defaults() {
        return { name: "", document_type: "autre", url: "", notes: "", file_name: "" };
    }
    get title() { return this.isEdit ? "Modifier le document" : "Déposer un document"; }
    get kicker() { return "DOSSIER DOCUMENTAIRE"; }
    get types() { return DOCUMENT_TYPES; }

    setup() {
        super.setup();
        this.state.datas = false;
    }

    validate() {
        return (this.state.values.name || "").trim() ? null : "Le nom du document est obligatoire.";
    }
    prepare(vals) {
        if (this.state.datas) {
            vals.datas = this.state.datas;
        }
        return vals;
    }

    async onFile(ev) {
        const file = ev.target.files && ev.target.files[0];
        if (!file) return;
        this.state.values.file_name = file.name;
        if (!this.state.values.name) {
            this.state.values.name = file.name;
        }
        this.state.datas = await new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(String(reader.result).split(",")[1]);
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }
}
