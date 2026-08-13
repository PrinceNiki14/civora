import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CivoraBadge } from "@civora_core/components/civora_kit";

const ICON_BY_TYPE = {
    "call": "fa-phone",
    "email": "fa-envelope",
    "meeting": "fa-calendar",
    "todo": "fa-check-square-o",
    "upload_document": "fa-file-o",
};

/**
 * Onglet Activites : liste des mail.activity de l'opportunite avec CRUD.
 * Modele natif Odoo (activite = tache prevue par un utilisateur).
 */
export class ActivitiesTab extends Component {
    static template = "civora_pipeline.ActivitiesTab";
    static components = { CivoraBadge };
    static props = { opportunityId: { type: [Number, Boolean] } };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            activities: [],
            types: [],
            users: [],
            editor: null, // { activityId, activity_type_id, summary, note, date_deadline, user_id }
            saving: false,
        });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        if (!this.props.opportunityId) {
            this.state.activities = [];
            this.state.loading = false;
            return;
        }
        // Types d'activite disponibles (limite au model civora.opportunity ou generiques).
        this.state.types = await this.orm.searchRead(
            "mail.activity.type",
            ["|", ["res_model", "=", "civora.opportunity"], ["res_model", "=", false]],
            ["name", "icon"],
            { order: "sequence, id" },
        );
        // Utilisateurs internes (agents).
        this.state.users = await this.orm.searchRead(
            "res.users", [["share", "=", false]], ["name"], { order: "name" },
        );
        // Activites en cours (pas terminees) sur l'opportunite.
        this.state.activities = await this.orm.searchRead(
            "mail.activity",
            [["res_model", "=", "civora.opportunity"], ["res_id", "=", this.props.opportunityId]],
            ["activity_type_id", "summary", "note", "date_deadline", "user_id", "state", "create_date"],
            { order: "date_deadline asc, id desc" },
        );
        this.state.loading = false;
    }

    // --- Rendu ---------------------------------------------------------
    typeIcon(a) {
        // On tente le mapping par nom du type ; sinon icone generique.
        const label = (a.activity_type_id && a.activity_type_id[1] || "").toLowerCase();
        for (const key of Object.keys(ICON_BY_TYPE)) {
            if (label.includes(key.replace("_", " ")) || label.includes(key)) return ICON_BY_TYPE[key];
        }
        if (label.includes("appel") || label.includes("call")) return "fa-phone";
        if (label.includes("mail") || label.includes("email")) return "fa-envelope";
        if (label.includes("visite") || label.includes("reunion") || label.includes("meeting")) return "fa-calendar";
        if (label.includes("document")) return "fa-file-o";
        return "fa-tasks";
    }
    typeName(a) { return a.activity_type_id ? a.activity_type_id[1] : "Activité"; }
    userName(a) { return a.user_id ? a.user_id[1] : "—"; }
    stripHtml(html) {
        if (!html) return "";
        const el = document.createElement("div");
        el.innerHTML = html;
        return (el.textContent || "").trim();
    }
    dueLabel(a) {
        if (!a.date_deadline) return "Sans échéance";
        const d = new Date(a.date_deadline + "T00:00:00");
        const today = new Date(); today.setHours(0, 0, 0, 0);
        const diffDays = Math.round((d.getTime() - today.getTime()) / (24 * 3600 * 1000));
        if (diffDays === 0) return "Aujourd'hui";
        if (diffDays === 1) return "Demain";
        if (diffDays === -1) return "Hier";
        if (diffDays < 0) return `En retard de ${-diffDays} j`;
        if (diffDays < 7) return `Dans ${diffDays} j`;
        return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "short" });
    }
    stateVariant(a) {
        if (a.state === "overdue") return "danger";
        if (a.state === "today") return "warning";
        if (a.state === "planned") return "info";
        return "neutral";
    }
    stateLabel(a) {
        return { overdue: "En retard", today: "Aujourd'hui", planned: "Prévue" }[a.state] || "Prévue";
    }

    // --- Actions -------------------------------------------------------
    openNew() {
        const defaultType = this.state.types.length ? this.state.types[0].id : false;
        const defaultUser = this.state.users[0] ? this.state.users[0].id : false;
        const today = new Date().toISOString().slice(0, 10);
        this.state.editor = {
            activityId: false,
            activity_type_id: defaultType,
            summary: "",
            note: "",
            date_deadline: today,
            user_id: defaultUser,
        };
    }
    openEdit(a) {
        this.state.editor = {
            activityId: a.id,
            activity_type_id: a.activity_type_id ? a.activity_type_id[0] : false,
            summary: a.summary || "",
            note: this.stripHtml(a.note),
            date_deadline: a.date_deadline || "",
            user_id: a.user_id ? a.user_id[0] : false,
        };
    }
    closeEditor() { this.state.editor = null; }
    setField(field, ev) {
        if (!this.state.editor) return;
        this.state.editor[field] = ev.target.value;
    }
    setM2O(field, ev) {
        if (!this.state.editor) return;
        this.state.editor[field] = ev.target.value ? parseInt(ev.target.value) : false;
    }

    async saveEditor() {
        const e = this.state.editor;
        if (!e || !e.activity_type_id) return;
        this.state.saving = true;
        try {
            const vals = {
                activity_type_id: e.activity_type_id,
                summary: e.summary || false,
                note: e.note || false,
                date_deadline: e.date_deadline || false,
                user_id: e.user_id || false,
            };
            if (e.activityId) {
                await this.orm.write("mail.activity", [e.activityId], vals);
            } else {
                vals.res_model = "civora.opportunity";
                vals.res_id = this.props.opportunityId;
                await this.orm.create("mail.activity", [vals]);
            }
            this.state.editor = null;
            await this.load();
        } catch (err) {
            this.notification.add("Enregistrement impossible.", { type: "danger" });
        } finally {
            this.state.saving = false;
        }
    }

    async complete(a) {
        try {
            await this.orm.call(
                "mail.activity", "action_feedback",
                [[a.id]],
                { feedback: a.summary || "Terminée" },
            );
            await this.load();
            this.notification.add("Activité terminée.", { type: "success" });
        } catch (err) {
            this.notification.add("Action impossible.", { type: "danger" });
        }
    }

    async remove(a) {
        try {
            await this.orm.unlink("mail.activity", [a.id]);
            await this.load();
        } catch (err) {
            this.notification.add("Suppression impossible.", { type: "danger" });
        }
    }
}
