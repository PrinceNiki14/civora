import { Component, onWillStart, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { user } from "@web/core/user";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { CivoraAvatar, CivoraBadge, CivoraProgress, CivoraTabs } from "@civora_core/components/civora_kit";
import { ContactDrawer } from "./contact_drawer";

const STATUS_MAP = {
    chaud: { label: "Chaud", variant: "danger" },
    actif: { label: "Actif", variant: "success" },
    qualifie: { label: "Qualifié", variant: "info" },
    a_risque: { label: "À risque", variant: "warning" },
    inactif: { label: "Inactif", variant: "neutral" },
};
const CONSENT_MAP = { opt_in: "Opt-in", opt_out: "Opt-out", none: "—" };

// Types d'interaction -> libelle + icone (aligne sur civora.interaction / le front).
const KIND_META = {
    appel: { label: "Appel", icon: "fa-phone" },
    email: { label: "Email", icon: "fa-envelope-o" },
    whatsapp: { label: "WhatsApp", icon: "fa-whatsapp" },
    sms: { label: "SMS", icon: "fa-comment-o" },
    rdv: { label: "RDV", icon: "fa-users" },
    visite: { label: "Visite", icon: "fa-building-o" },
    note: { label: "Note", icon: "fa-sticky-note-o" },
    document: { label: "Document", icon: "fa-file-o" },
    role_change: { label: "Changement de rôle", icon: "fa-tag" },
};
const KIND_ORDER = ["appel", "email", "whatsapp", "sms", "rdv", "visite", "note", "document", "role_change"];

// Regroupements pour la barre de filtres (aligne sur le front).
const KIND_GROUPS = [
    { key: "all", label: "Tout", kinds: null },
    { key: "appels", label: "Appels", kinds: ["appel"] },
    { key: "messages", label: "Messages", kinds: ["email", "whatsapp", "sms"] },
    { key: "rdv", label: "Rendez-vous", kinds: ["rdv", "visite"] },
    { key: "notes", label: "Notes", kinds: ["note"] },
    { key: "documents", label: "Documents", kinds: ["document"] },
    { key: "systeme", label: "Système", kinds: ["role_change"] },
];
const PERIODS = [
    { key: "7", label: "7j" },
    { key: "30", label: "30j" },
    { key: "all", label: "Tout" },
];

const FIELDS = [
    "name", "company_name", "email", "phone", "civora_whatsapp",
    "city", "civora_neighborhood", "street",
    "civora_role_ids", "civora_primary_role_id", "civora_role_names",
    "civora_source_id", "civora_agent_id", "civora_status",
    "civora_ai_score", "civora_ai_score_manual", "civora_ai_score_breakdown",
    "civora_ai_score_updated",
    "civora_budget", "civora_next_action", "comment",
    "civora_consent_email", "civora_consent_sms", "civora_consent_whatsapp",
    "civora_interaction_count", "civora_last_interaction_date",
    "create_date", "write_date",
];

/**
 * Page 360° d'un contact (client action civora.contact_360).
 * Ouverte depuis l'annuaire via action.doAction({ params: { contactId } }).
 * c1 : en-tete profil + onglet Apercu + bouton Modifier (reutilise ContactDrawer)
 *      + onglets placeholder. L'onglet Activite (timeline) est branche en c2.
 */
export class CivoraContact360 extends Component {
    static template = "civora_contacts.Contact360";
    static components = { CivoraAvatar, CivoraBadge, CivoraProgress, CivoraTabs, ContactDrawer };
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        // Onglets contribues par d'autres modules (biens, pipeline, GED...).
        this.contribTabs = registry
            .category("civora_contact_360_tab")
            .getAll()
            .slice()
            .sort((a, b) => (a.sequence || 100) - (b.sequence || 100));
        this.dialog = useService("dialog");

        const params = (this.props.action && this.props.action.params) || {};
        this.contactId = Number(params.contactId) || false;
        this.origin = params.origin || null;
        // Navigation prev/next : liste ordonnee d'ids fournie par l'ecran de depart.
        this.siblingIds = Array.isArray(params.siblingIds)
            ? params.siblingIds.map(Number).filter(Boolean)
            : [];
        this.users = [];

        this.state = useState({
            loading: true,
            error: "",
            record: null,
            activeTab: params.tab || "overview",
            edit: { open: false },
            // Activite / interactions
            interactions: [],
            addOpen: false,
            savingI: false,
            errI: "",
            newI: { kind: "appel", title: "", description: "", agent_id: user.userId },
            // Filtres timeline
            filterKind: "all",
            filterPeriod: "all",
            // v10.1.0 — Score IA
            scoreRecomputing: false,
            showBreakdown: false,
        });

        onWillStart(() => this.load());

        // Raccourcis clavier ← → pour naviguer entre siblings
        this._onKeyDown = (ev) => {
            // Ignore si focus sur input/textarea/select ou modale d'édition ouverte
            const tag = (ev.target.tagName || "").toLowerCase();
            if (["input", "textarea", "select"].includes(tag)) return;
            if (this.state.edit && this.state.edit.open) return;
            if (ev.key === "ArrowLeft" && this.hasPrev) {
                ev.preventDefault();
                this.goPrev();
            } else if (ev.key === "ArrowRight" && this.hasNext) {
                ev.preventDefault();
                this.goNext();
            }
        };
        onMounted(() => window.addEventListener("keydown", this._onKeyDown));
        onWillUnmount(() => window.removeEventListener("keydown", this._onKeyDown));
    }

    async load() {
        this.state.loading = true;
        this.state.error = "";
        if (!this.contactId) {
            this.state.error = "Contact introuvable.";
            this.state.loading = false;
            return;
        }
        try {
            const [rec] = await this.orm.read("res.partner", [this.contactId], FIELDS);
            this.state.record = rec || null;
            if (!rec) {
                this.state.error = "Contact introuvable.";
            } else {
                this.users = await this.orm.searchRead(
                    "res.users", [["share", "=", false]], ["name", "civora_function_id"], { order: "name" }
                );
                await this.loadInteractions();
            }
        } catch (e) {
            this.state.error = "Impossible de charger le contact.";
        }
        this.state.loading = false;
    }

    async loadInteractions() {
        this.state.interactions = await this.orm.searchRead(
            "civora.interaction",
            [["contact_id", "=", this.contactId]],
            ["kind", "title", "description", "agent_id", "date"],
            { order: "date desc, id desc" }
        );
    }

    // --- Navigation ----------------------------------------------------
    goBack() {
        if (this.origin && this.origin.tag) {
            this.action.doAction({
                type: "ir.actions.client",
                tag: this.origin.tag,
                params: this.origin.params || {},
                target: "current",
            });
        } else {
            this.action.doAction({
                type: "ir.actions.client",
                tag: "civora.contacts",
                target: "current",
            });
        }
    }
    get backLabel() {
        return this.origin && this.origin.label ? this.origin.label : "Annuaire";
    }

    // --- Navigation prev/next entre contacts (siblings) --------------
    get siblingPosition() {
        if (!this.siblingIds.length) return -1;
        return this.siblingIds.indexOf(this.contactId);
    }
    get siblingCount() {
        return this.siblingIds.length;
    }
    get hasSiblings() {
        return this.siblingIds.length > 1 && this.siblingPosition >= 0;
    }
    get hasPrev() {
        return this.hasSiblings && this.siblingPosition > 0;
    }
    get hasNext() {
        return this.hasSiblings && this.siblingPosition < this.siblingCount - 1;
    }
    get siblingCounterLabel() {
        if (!this.hasSiblings) return "";
        return (this.siblingPosition + 1) + " / " + this.siblingCount;
    }
    goPrev() {
        if (!this.hasPrev) return;
        const prevId = this.siblingIds[this.siblingPosition - 1];
        this._navigateToSibling(prevId);
    }
    goNext() {
        if (!this.hasNext) return;
        const nextId = this.siblingIds[this.siblingPosition + 1];
        this._navigateToSibling(nextId);
    }
    _navigateToSibling(newId) {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.contact_360",
            params: {
                contactId: newId,
                siblingIds: this.siblingIds,
                origin: this.origin,
                tab: this.state.activeTab,  // préserver l'onglet actif
            },
            target: "current",
        });
    }

    // --- Onglets -------------------------------------------------------
    setTab(id) {
        this.state.activeTab = id;
    }
    get tabList() {
        const count = this.state.interactions.length;
        const base = [
            { id: "overview", label: "Aperçu" },
            { id: "activity", label: "Activité", count: count },
        ];
        const contrib = this.contribTabs.map((t) => ({ id: t.id, label: t.label }));
        return [...base, ...contrib];
    }
    get activeContrib() {
        return this.contribTabs.find((t) => t.id === this.state.activeTab) || null;
    }

    // --- Edition (reutilise la modale ContactDrawer) ------------------
    openEdit() {
        this.state.edit = { open: true };
    }
    closeEdit() {
        this.state.edit = { open: false };
    }
    async onEditSaved() {
        this.state.edit = { open: false };
        await this.load();
    }

    // --- Helpers d'affichage ------------------------------------------
    get record() {
        return this.state.record || {};
    }
    m2oName(v) {
        return v ? v[1] : "—";
    }
    orDash(v) {
        return v ? v : "—";
    }
    get statusInfo() {
        return STATUS_MAP[this.record.civora_status] || { label: "—", variant: "neutral" };
    }
    get roleLabel() {
        const r = this.record;
        if (r.civora_primary_role_id) {
            return r.civora_primary_role_id[1];
        }
        if (r.civora_role_names) {
            return r.civora_role_names.split(",")[0].trim();
        }
        return "—";
    }
    scoreTone(score) {
        if (score >= 80) return "success";
        if (score >= 60) return "warning";
        return "danger";
    }
    consentLabel(v) {
        return CONSENT_MAP[v] || "—";
    }
    fmtMoney(v) {
        const n = Number(v || 0);
        return (n ? n.toLocaleString("fr-FR") : "0") + " FCFA";
    }

    // --- Interactions (onglet Activite) -------------------------------
    get currentUserId() {
        return user.userId;
    }
    get periods() {
        return PERIODS;
    }
    get kindOptions() {
        return KIND_ORDER.map((k) => ({ value: k, label: KIND_META[k].label }));
    }
    get kindFilters() {
        const list = this.state.interactions;
        return KIND_GROUPS
            .map((g) => ({
                key: g.key,
                label: g.label,
                count: g.kinds ? list.filter((i) => g.kinds.includes(i.kind)).length : list.length,
            }))
            .filter((g) => g.key === "all" || g.count > 0);
    }
    get filteredInteractions() {
        let list = this.state.interactions;
        const grp = KIND_GROUPS.find((g) => g.key === this.state.filterKind);
        if (grp && grp.kinds) {
            list = list.filter((i) => grp.kinds.includes(i.kind));
        }
        if (this.state.filterPeriod !== "all") {
            const cutoff = Date.now() - Number(this.state.filterPeriod) * 86400000;
            list = list.filter((i) => {
                const t = new Date((i.date || "").replace(" ", "T") + "Z").getTime();
                return t >= cutoff;
            });
        }
        return list;
    }
    setKindFilter(key) {
        this.state.filterKind = key;
    }
    setPeriod(p) {
        this.state.filterPeriod = p;
    }
    kindMeta(k) {
        return KIND_META[k] || KIND_META.note;
    }
    userFn(uid) {
        const u = this.users.find((x) => x.id === uid);
        return u && u.civora_function_id ? u.civora_function_id[1] : "";
    }
    agentOptionLabel(u) {
        const me = u.id === this.currentUserId ? " (moi)" : "";
        const fn = u.civora_function_id ? " · " + u.civora_function_id[1] : "";
        return u.name + me + fn;
    }
    get engagementStats() {
        const list = this.state.interactions;
        const c = (k) => list.filter((i) => i.kind === k).length;
        return {
            appel: c("appel"),
            email: c("email"),
            whatsapp: c("whatsapp"),
            rdv: c("rdv"),
            visite: c("visite"),
            last: list.length ? this.relDate(list[0].date) : "—",
        };
    }
    get preferredChannels() {
        const list = this.state.interactions;
        const chans = [
            { key: "whatsapp", label: "WhatsApp" },
            { key: "appel", label: "Téléphone" },
            { key: "email", label: "Email" },
            { key: "sms", label: "SMS" },
        ];
        const counts = chans.map((ch) => ({
            label: ch.label,
            n: list.filter((i) => i.kind === ch.key).length,
        }));
        const total = counts.reduce((s, x) => s + x.n, 0);
        if (!total) {
            return [];
        }
        return counts
            .filter((x) => x.n > 0)
            .map((x) => ({ label: x.label, pct: Math.round((x.n / total) * 100) }))
            .sort((a, b) => b.pct - a.pct);
    }
    get activitySub() {
        const list = this.state.interactions;
        if (!list.length) {
            return "Aucune interaction pour l'instant";
        }
        const kinds = [];
        for (const i of list) {
            const l = this.kindMeta(i.kind).label.toLowerCase();
            if (!kinds.includes(l)) kinds.push(l);
        }
        const word = list.length > 1 ? " évènements · " : " évènement · ";
        return list.length + word + kinds.slice(0, 4).join(", ");
    }
    fmtDate(v) {
        // v = "YYYY-MM-DD HH:MM:SS" (serveur, UTC). Abidjan etant en UTC+0,
        // aucun decalage a appliquer ici.
        if (!v) return "—";
        const [d, t] = v.split(" ");
        if (!d) return v;
        const [Y, M, D] = d.split("-");
        const hm = (t || "").slice(0, 5);
        return D + "/" + M + "/" + Y + (hm ? " · " + hm : "");
    }
    relDate(v) {
        if (!v) return "";
        const dt = new Date(v.replace(" ", "T") + "Z"); // serveur = UTC
        const min = Math.floor((Date.now() - dt.getTime()) / 60000);
        if (min < 1) return "à l'instant";
        if (min < 60) return "il y a " + min + " min";
        const h = Math.floor(min / 60);
        if (h < 24) return "il y a " + h + " h";
        return "il y a " + Math.floor(h / 24) + " j";
    }

    toggleAdd() {
        this.state.addOpen = !this.state.addOpen;
        if (this.state.addOpen) {
            this.state.errI = "";
            this.state.newI = { kind: "appel", title: "", description: "", agent_id: user.userId };
        }
    }
    setNewField(field, ev) {
        let v = ev.target.value;
        if (field === "agent_id") {
            v = Number(v) || false;
        }
        this.state.newI[field] = v;
    }
    async saveInteraction() {
        const f = this.state.newI;
        if (!f.title || !f.title.trim()) {
            this.state.errI = "Le titre est requis.";
            return;
        }
        this.state.errI = "";
        this.state.savingI = true;
        try {
            await this.orm.create("civora.interaction", [{
                contact_id: this.contactId,
                kind: f.kind,
                title: f.title.trim(),
                description: f.description || false,
                agent_id: Number(f.agent_id) || false,
            }]);
            this.state.savingI = false;
            this.state.addOpen = false;
            this.state.newI = { kind: "appel", title: "", description: "", agent_id: user.userId };
            await this.loadInteractions();
        } catch (e) {
            this.state.savingI = false;
            this.state.errI = "Erreur lors de l'enregistrement.";
            throw e;
        }
    }
    deleteInteraction(rec) {
        this.dialog.add(ConfirmationDialog, {
            title: "Supprimer l'interaction",
            body: "Supprimer « " + rec.title + " » ? Cette action est définitive.",
            confirmLabel: "Supprimer",
            confirmClass: "btn-danger",
            cancelLabel: "Annuler",
            confirm: async () => {
                await this.orm.unlink("civora.interaction", [rec.id]);
                await this.loadInteractions();
            },
            cancel: () => {},
        });
    }

    // ═══════════════════════════════════════════════════════════════════
    // v10.1.0 — Score IA : recalcul + verrou + décomposition
    // ═══════════════════════════════════════════════════════════════════
    get scoreBreakdown() {
        const r = this.state.record;
        if (!r || !r.civora_ai_score_breakdown) return null;
        try {
            return JSON.parse(r.civora_ai_score_breakdown);
        } catch (e) {
            return null;
        }
    }
    get scoreUpdatedLabel() {
        const r = this.state.record;
        if (!r || !r.civora_ai_score_updated) return "";
        return this.formatDateTime(r.civora_ai_score_updated);
    }
    async recomputeScore() {
        if (this.state.scoreRecomputing) return;
        this.state.scoreRecomputing = true;
        try {
            const res = await this.orm.call(
                "res.partner", "civora_recompute_score",
                [], { contact_id: this.contactId }
            );
            if (res && res.success) {
                this.state.record.civora_ai_score = res.score;
                this.state.record.civora_ai_score_breakdown = res.breakdown;
                this.state.record.civora_ai_score_updated = res.updated;
                this.notification.add(`Score recalculé : ${res.score}/100`, {
                    type: "success", sticky: false,
                });
            } else {
                this.notification.add("Impossible de recalculer le score.", {
                    type: "danger",
                });
            }
        } catch (e) {
            console.error("[CIVORA-SCORE] recompute", e);
            this.notification.add("Erreur lors du recalcul.", { type: "danger" });
        } finally {
            this.state.scoreRecomputing = false;
        }
    }
    async toggleScoreLock() {
        const wasLocked = !!this.state.record.civora_ai_score_manual;
        const newLocked = !wasLocked;
        try {
            const res = await this.orm.call(
                "res.partner", "civora_toggle_score_lock",
                [], { contact_id: this.contactId, locked: newLocked }
            );
            if (res && res.success) {
                this.state.record.civora_ai_score_manual = res.locked;
                this.notification.add(
                    res.locked
                        ? "Score verrouillé (ne sera pas recalculé automatiquement)."
                        : "Score déverrouillé (recalcul auto réactivé).",
                    { type: "success", sticky: false }
                );
            }
        } catch (e) {
            console.error("[CIVORA-SCORE] lock", e);
            this.notification.add("Erreur lors du verrouillage.", { type: "danger" });
        }
    }
    toggleScoreBreakdown() {
        this.state.showBreakdown = !this.state.showBreakdown;
    }

    // --- Formatage des dates -------------------------------------------
    formatDate(dtStr) {
        if (!dtStr) return "—";
        const d = new Date(dtStr);
        if (isNaN(d)) return dtStr;
        return d.toLocaleDateString("fr-FR");
    }
    formatDateTime(dtStr) {
        if (!dtStr) return "—";
        const d = new Date(dtStr);
        if (isNaN(d)) return dtStr;
        return d.toLocaleDateString("fr-FR") + " à "
             + String(d.getHours()).padStart(2, "0") + ":"
             + String(d.getMinutes()).padStart(2, "0");
    }
    formatRelativeDate(dtStr) {
        if (!dtStr) return "Jamais";
        const d = new Date(dtStr);
        if (isNaN(d)) return dtStr;
        const now = new Date();
        const diff = Math.floor((now - d) / (1000 * 60 * 60 * 24));
        if (diff === 0) return "Aujourd'hui";
        if (diff === 1) return "Hier";
        if (diff < 7) return `Il y a ${diff} jours`;
        if (diff < 30) return `Il y a ${Math.floor(diff / 7)} semaines`;
        if (diff < 365) return `Il y a ${Math.floor(diff / 30)} mois`;
        return `Il y a ${Math.floor(diff / 365)} an${Math.floor(diff / 365) > 1 ? 's' : ''}`;
    }
}

registry.category("actions").add("civora.contact_360", CivoraContact360);
