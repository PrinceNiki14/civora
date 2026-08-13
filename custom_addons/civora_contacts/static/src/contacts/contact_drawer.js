import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { CivoraDrawer } from "@civora_core/components/civora_drawer";
import { CivoraAvatar, CivoraBadge, CivoraProgress } from "@civora_core/components/civora_kit";

const STATUSES = [
    { value: "chaud", label: "Chaud" },
    { value: "actif", label: "Actif" },
    { value: "qualifie", label: "Qualifié" },
    { value: "a_risque", label: "À risque" },
    { value: "inactif", label: "Inactif" },
];
const CONSENTS = [
    { value: "opt_in", label: "Opt-in" },
    { value: "opt_out", label: "Opt-out" },
    { value: "none", label: "—" },
];

function emptyForm() {
    return {
        name: "", company_name: "", email: "", phone: "", civora_whatsapp: "",
        city: "", civora_neighborhood: "", street: "",
        civora_role_ids: [], civora_primary_role_id: false,
        civora_source_id: false, civora_agent_id: false,
        civora_status: false, civora_ai_score: 0, civora_budget: 0,
        civora_next_action: "", comment: "",
        civora_consent_email: "none", civora_consent_sms: "none", civora_consent_whatsapp: "none",
        company_id: false,
    };
}

export class ContactDrawer extends Component {
    static template = "civora_contacts.Drawer";
    static components = { CivoraDrawer, CivoraAvatar, CivoraBadge, CivoraProgress };
    static props = {
        mode: String,                               // "view" | "edit" | "create"
        contactId: { type: [Number, Boolean], optional: true },
        onClose: Function,
        onSaved: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.statuses = STATUSES;
        this.consents = CONSENTS;

        this.state = useState({
            mode: this.props.mode,
            loading: true,
            saving: false,
            error: "",
            form: emptyForm(),
            record: null,   // pour la vue 360 (valeurs affichables)
            // Détection de doublons (uniquement en mode création)
            duplicates: [],
            duplicatesChecked: false,
            duplicatesLoading: false,
            forceCreateDespiteDuplicates: false,
        });

        this.roles = [];
        this.sources = [];
        this.segments = [];
        this.users = [];
        // Debounce pour la détection de doublons
        this._duplicateTimer = null;
        // Societes autorisees (source fiable, comme le selecteur de la sidebar).
        this.companies = Object.values(user.allowedCompanies || {})
            .sort((a, b) => (a.sequence || 0) - (b.sequence || 0));

        onWillStart(async () => {
            await this.loadRefData();
            if (this.props.contactId) {
                await this.loadContact(this.props.contactId);
            } else {
                // Nouveau contact : pre-rempli sur la societe active.
                this.state.form.company_id = user.activeCompany ? user.activeCompany.id : false;
            }
            this.state.loading = false;
        });
    }

    async loadRefData() {
        this.roles = await this.orm.searchRead("civora.contact.role", [], ["name", "code", "color"]);
        this.sources = await this.orm.searchRead("civora.contact.source", [], ["name"]);
        this.users = await this.orm.searchRead("res.users", [["share", "=", false]], ["name"]);
    }

    async loadContact(id) {
        const fields = [
            "name", "company_name", "email", "phone", "civora_whatsapp",
            "city", "civora_neighborhood", "street",
            "civora_role_ids", "civora_primary_role_id", "civora_source_id",
            "civora_agent_id", "civora_status", "civora_ai_score", "civora_budget",
            "civora_next_action", "comment", "civora_role_names",
            "civora_consent_email", "civora_consent_sms", "civora_consent_whatsapp",
            "company_id",
        ];
        const [rec] = await this.orm.read("res.partner", [id], fields);
        this.state.record = rec;
        // Alimente le formulaire (m2o -> id, m2m -> liste d'ids)
        const m2o = (v) => (v ? v[0] : false);
        this.state.form = {
            name: rec.name || "", company_name: rec.company_name || "",
            email: rec.email || "", phone: rec.phone || "", civora_whatsapp: rec.civora_whatsapp || "",
            city: rec.city || "", civora_neighborhood: rec.civora_neighborhood || "", street: rec.street || "",
            civora_role_ids: rec.civora_role_ids || [],
            civora_primary_role_id: m2o(rec.civora_primary_role_id),
            civora_source_id: m2o(rec.civora_source_id),
            civora_agent_id: m2o(rec.civora_agent_id),
            civora_status: rec.civora_status || false,
            civora_ai_score: rec.civora_ai_score || 0,
            civora_budget: rec.civora_budget || 0,
            civora_next_action: rec.civora_next_action || "",
            comment: rec.comment || "",
            civora_consent_email: rec.civora_consent_email || "none",
            civora_consent_sms: rec.civora_consent_sms || "none",
            civora_consent_whatsapp: rec.civora_consent_whatsapp || "none",
            company_id: m2o(rec.company_id),
        };
    }

    // --- Setters (binding explicite, robuste) -------------------------
    setField(field, ev) {
        this.state.form[field] = ev.target.value;
        // Déclencher détection de doublons pour les champs sensibles en création
        if (this.state.mode === "create" && ["name", "email", "phone"].includes(field)) {
            this._scheduleDuplicateCheck();
        }
    }
    setNumber(field, ev) {
        this.state.form[field] = ev.target.value === "" ? 0 : Number(ev.target.value);
    }
    setM2O(field, ev) {
        this.state.form[field] = ev.target.value ? parseInt(ev.target.value) : false;
    }

    // --- Détection de doublons -----------------------------------------
    _scheduleDuplicateCheck() {
        if (this._duplicateTimer) clearTimeout(this._duplicateTimer);
        this._duplicateTimer = setTimeout(() => this._checkDuplicates(), 500);
    }
    async _checkDuplicates() {
        const f = this.state.form;
        const nameLen = (f.name || "").trim().length;
        const emailLen = (f.email || "").trim().length;
        const phoneLen = (f.phone || "").trim().length;
        // Requiert au moins 3 caractères sur un des champs pertinents
        if (nameLen < 3 && emailLen < 3 && phoneLen < 4) {
            this.state.duplicates = [];
            this.state.duplicatesChecked = false;
            return;
        }
        this.state.duplicatesLoading = true;
        try {
            const results = await this.orm.call(
                "res.partner", "civora_find_duplicates",
                [], { name: f.name, email: f.email, phone: f.phone }
            );
            this.state.duplicates = results || [];
            this.state.duplicatesChecked = true;
        } catch (e) {
            console.error("[CIVORA-DUP] error", e);
            this.state.duplicates = [];
        } finally {
            this.state.duplicatesLoading = false;
        }
    }
    ignoreDuplicates() {
        this.state.forceCreateDespiteDuplicates = true;
    }
    openExistingContact(contactId) {
        // Ouvrir directement la fiche 360° d'un doublon existant
        this.props.onClose();
        // Attendre la fermeture puis naviguer
        setTimeout(() => {
            window.location.hash = `#action=civora.contact_360&contactId=${contactId}`;
            // Fallback : recharger via action.doAction
            const evt = new CustomEvent("civora-open-contact", { detail: { contactId } });
            window.dispatchEvent(evt);
        }, 100);
    }

    // --- Titre du drawer ----------------------------------------------
    get drawerTitle() {
        if (this.state.mode === "create") return "Nouveau contact";
        if (this.state.mode === "edit") return "Modifier le contact";
        return this.state.record ? this.state.record.name : "Contact";
    }
    get drawerSubtitle() {
        return "Fiche 360° · identité, qualification et consentements";
    }

    // --- Roles ---------------------------------------------------------
    isRoleChecked(id) {
        return this.state.form.civora_role_ids.includes(id);
    }
    toggleRole(id) {
        const arr = this.state.form.civora_role_ids;
        if (arr.includes(id)) {
            this.state.form.civora_role_ids = arr.filter((x) => x !== id);
            if (this.state.form.civora_primary_role_id === id) {
                this.state.form.civora_primary_role_id = false;
            }
        } else {
            this.state.form.civora_role_ids = [...arr, id];
        }
    }
    get selectedRoles() {
        return this.roles.filter((r) => this.state.form.civora_role_ids.includes(r.id));
    }

    // --- Helpers d'affichage (vue 360) --------------------------------
    statusLabel(v) {
        const s = STATUSES.find((x) => x.value === v);
        return s ? s.label : "—";
    }
    statusVariant(v) {
        const map = { chaud: "danger", a_risque: "warning", actif: "success", qualifie: "info", inactif: "neutral" };
        return map[v] || "neutral";
    }
    scoreTone(score) {
        if (score >= 80) return "success";
        if (score >= 60) return "warning";
        return "danger";
    }
    consentLabel(v) {
        const c = CONSENTS.find((x) => x.value === v);
        return c ? c.label : "—";
    }
    roleName(id) {
        const r = this.roles.find((x) => x.id === id);
        return r ? r.name : "";
    }

    // --- Actions -------------------------------------------------------
    switchToEdit() {
        this.state.mode = "edit";
    }

    validate() {
        const f = this.state.form;
        if (!f.name || !f.name.trim()) return "Le nom est requis.";
        const score = Number(f.civora_ai_score) || 0;
        if (score < 0 || score > 100) return "Le score IA doit être entre 0 et 100.";
        if (f.civora_primary_role_id && !f.civora_role_ids.includes(f.civora_primary_role_id)) {
            return "Le rôle principal doit faire partie des rôles sélectionnés.";
        }
        return "";
    }

    buildVals() {
        const f = this.state.form;
        return {
            name: f.name.trim(),
            company_name: f.company_name || false,
            email: f.email || false,
            phone: f.phone || false,
            civora_whatsapp: f.civora_whatsapp || false,
            city: f.city || false,
            civora_neighborhood: f.civora_neighborhood || false,
            street: f.street || false,
            civora_role_ids: [[6, 0, f.civora_role_ids]],
            civora_primary_role_id: f.civora_primary_role_id || false,
            civora_source_id: f.civora_source_id || false,
            civora_agent_id: f.civora_agent_id || false,
            civora_status: f.civora_status || false,
            civora_ai_score: Number(f.civora_ai_score) || 0,
            civora_budget: Number(f.civora_budget) || 0,
            civora_next_action: f.civora_next_action || false,
            comment: f.comment || false,
            civora_consent_email: f.civora_consent_email,
            civora_consent_sms: f.civora_consent_sms,
            civora_consent_whatsapp: f.civora_consent_whatsapp,
            company_id: f.company_id || false,
            civora_is_contact: true,
        };
    }

    async save() {
        const err = this.validate();
        if (err) {
            this.state.error = err;
            return;
        }
        // En création, bloquer si des doublons ont été détectés et pas ignorés
        if (this.state.mode === "create"
                && this.state.duplicates.length > 0
                && !this.state.forceCreateDespiteDuplicates) {
            this.state.error = "Des doublons potentiels ont été détectés. Vérifiez la liste ci-dessus, puis cliquez sur \"Créer quand même\" pour continuer.";
            return;
        }
        this.state.error = "";
        this.state.saving = true;
        try {
            const vals = this.buildVals();
            if (this.state.mode === "create") {
                await this.orm.create("res.partner", [vals]);
            } else {
                await this.orm.write("res.partner", [this.props.contactId], vals);
            }
            this.state.saving = false;
            this.props.onSaved();
        } catch (e) {
            this.state.saving = false;
            this.state.error = "Erreur lors de l'enregistrement.";
            throw e;
        }
    }
}
