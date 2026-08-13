import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";
import { CivoraBadge, CivoraAvatar, CivoraProgress } from "@civora_core/components/civora_kit";
import { ContactDrawer } from "./contact_drawer";
import { ContactsRgpdView } from "./rgpd_view";
import { ContactsImportsView } from "./imports_view";
import { ContactsScoringView } from "./scoring_view";
import { ContactsInteractionsView } from "./interactions_view";

const DOMAIN_BASE = [["civora_is_contact", "=", true]];
const PAGE_SIZE = 50;

// Onglets natifs du module. La `sequence` permet aux modules externes de
// s'insérer à la bonne place sans patcher ce fichier — l'ordre cible suit
// le front de référence (contacts.index.tsx) :
//   Annuaire · Segments · Campagnes · Interactions · Scoring · Imports · RGPD
const BASE_TABS = [
    { id: "directory", label: "Annuaire", sequence: 10 },
    { id: "interactions", label: "Interactions", sequence: 40 },
    { id: "scoring", label: "Scoring IA", sequence: 50 },
    { id: "imports", label: "Imports & API", sequence: 60 },
    { id: "rgpd", label: "RGPD & Consentements", sequence: 70 },
];

// Registre de contribution d'onglets.
// Un module externe s'ajoute ainsi, sans dépendance inverse :
//
//   registry.category("civora_contacts_tab").add("campaigns", {
//       id: "campaigns",
//       label: "Campagnes",
//       sequence: 30,
//       Component: CivoraCampaignsView,
//   });
//
// Le composant reçoit automatiquement la prop `onOpenContact`.
const TAB_REGISTRY = "civora_contacts_tab";

// Statuts CRM pour Kanban + filtres (ordre logique du pipeline commercial)
const STATUS_META = {
    chaud: { label: "Chaud", variant: "danger", icon: "fa-fire" },
    actif: { label: "Actif", variant: "success", icon: "fa-check-circle-o" },
    qualifie: { label: "Qualifié", variant: "info", icon: "fa-star-o" },
    a_risque: { label: "À risque", variant: "warning", icon: "fa-exclamation-triangle" },
    inactif: { label: "Inactif", variant: "neutral", icon: "fa-moon-o" },
};
const KANBAN_COLUMNS = ["chaud", "actif", "qualifie", "a_risque", "inactif"];

const CONSENT_OPTIONS = [
    { value: "any", label: "Tous" },
    { value: "opt_in", label: "Opt-in" },
    { value: "opt_out", label: "Opt-out" },
    { value: "none", label: "Non renseigné" },
];

const SORT_OPTIONS = [
    { value: "civora_ai_score desc, name asc", label: "Score IA (haut → bas)" },
    { value: "civora_ai_score asc, name asc", label: "Score IA (bas → haut)" },
    { value: "name asc", label: "Nom A → Z" },
    { value: "name desc", label: "Nom Z → A" },
    { value: "write_date desc", label: "Dernière modif" },
    { value: "create_date desc", label: "Plus récents" },
    { value: "create_date asc", label: "Plus anciens" },
];

export class CivoraContactsScreen extends Component {
    static template = "civora_contacts.Screen";
    static components = {
        CivoraStatCard, CivoraBadge, CivoraAvatar, CivoraProgress, ContactDrawer,
        ContactsRgpdView, ContactsImportsView,
        ContactsScoringView, ContactsInteractionsView,
    };
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        // Fusion onglets natifs + onglets contribués par des modules externes.
        // Lecture au setup : le registre est déjà peuplé, les assets des
        // modules dépendants étant chargés après celui-ci.
        this.externalTabs = registry.category(TAB_REGISTRY).getAll()
            .filter((t) => t && t.id && t.Component);
        this.tabs = [...BASE_TABS, ...this.externalTabs]
            .slice()
            .sort((a, b) => (a.sequence || 100) - (b.sequence || 100));

        this.kanbanColumns = KANBAN_COLUMNS;
        this.statusMeta = STATUS_META;
        this.consentOptions = CONSENT_OPTIONS;
        this.sortOptions = SORT_OPTIONS;

        this.state = useState({
            loading: true,
            contacts: [],
            stats: { total: 0, chaud: 0, vip: 0, avg: 0 },
            activeTab: "directory",
            viewMode: "table",  // "table" | "kanban"
            search: "",
            // Filtres avancés
            filters: {
                role_id: false,
                source_id: false,
                agent_id: false,
                status: false,
                city: "",
                consent_email: "any",
                consent_sms: "any",
                consent_whatsapp: "any",
                score_min: 0,
                score_max: 100,
            },
            filtersOpen: false,
            sortOrder: SORT_OPTIONS[0].value,
            // Pagination
            offset: 0,
            hasMore: false,
            totalFiltered: 0,
            // Drawer
            drawer: { open: false, mode: "view", contactId: false },
            // Export
            exporting: false,
        });

        // Ref data pour les selects de filtres
        this.roles = [];
        this.sources = [];
        this.agents = [];
        this.cities = [];

        onWillStart(async () => {
            await this.loadRefData();
            await this.load();
        });
    }

    async loadRefData() {
        this.roles = await this.orm.searchRead(
            "civora.contact.role", [], ["name", "code"], { order: "sequence, name" }
        );
        this.sources = await this.orm.searchRead(
            "civora.contact.source", [], ["name"], { order: "sequence, name" }
        );
        this.agents = await this.orm.searchRead(
            "res.users", [["share", "=", false]], ["name"], { order: "name" }
        );
        // Villes distinctes (via read_group)
        try {
            const cityGroups = await this.orm.formattedReadGroup(
                "res.partner", DOMAIN_BASE, ["city"], ["__count"]
            );
            this.cities = cityGroups
                .filter((g) => g.city)
                .map((g) => g.city)
                .sort();
        } catch (e) {
            this.cities = [];
        }
    }

    // --- Construction du domaine à partir des filtres ------------------
    get domain() {
        const dom = [...DOMAIN_BASE];
        const f = this.state.filters;

        if (f.role_id) dom.push(["civora_role_ids", "in", [f.role_id]]);
        if (f.source_id) dom.push(["civora_source_id", "=", f.source_id]);
        if (f.agent_id) dom.push(["civora_agent_id", "=", f.agent_id]);
        if (f.status) dom.push(["civora_status", "=", f.status]);
        if (f.city && f.city.trim()) dom.push(["city", "ilike", f.city.trim()]);
        if (f.consent_email !== "any") dom.push(["civora_consent_email", "=", f.consent_email]);
        if (f.consent_sms !== "any") dom.push(["civora_consent_sms", "=", f.consent_sms]);
        if (f.consent_whatsapp !== "any") dom.push(["civora_consent_whatsapp", "=", f.consent_whatsapp]);
        if (f.score_min > 0) dom.push(["civora_ai_score", ">=", f.score_min]);
        if (f.score_max < 100) dom.push(["civora_ai_score", "<=", f.score_max]);

        const q = (this.state.search || "").trim();
        if (q) {
            dom.push("|", "|", "|", "|",
                ["name", "ilike", q],
                ["email", "ilike", q],
                ["phone", "ilike", q],
                ["city", "ilike", q],
                ["company_name", "ilike", q]);
        }
        return dom;
    }

    // --- Chargement ----------------------------------------------------
    async load(append = false) {
        this.state.loading = !append;
        const domain = this.domain;
        const offset = append ? this.state.offset : 0;

        // Stats globales (sur DOMAIN_BASE, indépendantes de la recherche)
        if (!append) {
            const total = await this.orm.searchCount("res.partner", DOMAIN_BASE);
            const chaud = await this.orm.searchCount(
                "res.partner", [...DOMAIN_BASE, ["civora_status", "=", "chaud"]]
            );
            const vip = await this.orm.searchCount(
                "res.partner", [...DOMAIN_BASE, ["civora_ai_score", ">=", 85]]
            );
            let avg = 0;
            try {
                const groups = await this.orm.formattedReadGroup(
                    "res.partner", DOMAIN_BASE, [], ["civora_ai_score:avg"]
                );
                avg = groups.length ? Math.round(groups[0]["civora_ai_score:avg"] || 0) : 0;
            } catch {
                avg = 0;
            }
            this.state.stats = { total, chaud, vip, avg };
        }

        // Total filtré (pour "X sur Y")
        this.state.totalFiltered = await this.orm.searchCount("res.partner", domain);

        // En mode kanban : charger jusqu'à 500 par colonne (raisonnable pour affichage)
        const limit = this.state.viewMode === "kanban" ? 500 : PAGE_SIZE;

        const records = await this.orm.searchRead(
            "res.partner",
            domain,
            [
                "name", "company_name", "email", "phone", "civora_whatsapp",
                "civora_source_id", "civora_primary_role_id", "civora_role_names",
                "civora_ai_score", "civora_status", "civora_agent_id",
                "civora_next_action", "city", "civora_neighborhood",
            ],
            { limit, offset, order: this.state.sortOrder }
        );

        if (append) {
            this.state.contacts = [...this.state.contacts, ...records];
        } else {
            this.state.contacts = records;
        }
        this.state.offset = (append ? offset : 0) + records.length;
        this.state.hasMore = this.state.viewMode === "table"
            && this.state.contacts.length < this.state.totalFiltered;
        this.state.loading = false;
    }

    async loadMore() {
        await this.load(true);
    }

    // --- View mode -----------------------------------------------------
    async setViewMode(mode) {
        if (this.state.viewMode === mode) return;
        this.state.viewMode = mode;
        this.state.offset = 0;
        await this.load();
    }

    // --- Filtres -------------------------------------------------------
    toggleFilters() {
        this.state.filtersOpen = !this.state.filtersOpen;
    }
    async setFilter(field, ev) {
        let v = ev.target.value;
        if (field === "role_id" || field === "source_id" || field === "agent_id") {
            v = v ? Number(v) : false;
        } else if (field === "score_min" || field === "score_max") {
            v = Number(v) || 0;
        }
        this.state.filters[field] = v;
        this.state.offset = 0;
        await this.load();
    }
    async resetFilters() {
        this.state.filters = {
            role_id: false, source_id: false, agent_id: false, status: false, city: "",
            consent_email: "any", consent_sms: "any", consent_whatsapp: "any",
            score_min: 0, score_max: 100,
        };
        this.state.search = "";
        this.state.offset = 0;
        await this.load();
    }
    get activeFilterCount() {
        const f = this.state.filters;
        let n = 0;
        if (f.role_id) n++;
        if (f.source_id) n++;
        if (f.agent_id) n++;
        if (f.status) n++;
        if (f.city && f.city.trim()) n++;
        if (f.consent_email !== "any") n++;
        if (f.consent_sms !== "any") n++;
        if (f.consent_whatsapp !== "any") n++;
        if (f.score_min > 0) n++;
        if (f.score_max < 100) n++;
        return n;
    }

    // --- Sort ----------------------------------------------------------
    async setSortOrder(ev) {
        this.state.sortOrder = ev.target.value;
        this.state.offset = 0;
        await this.load();
    }
    async sortByColumn(column) {
        // Toggle asc/desc si déjà trié dessus, sinon set desc par défaut
        const cur = this.state.sortOrder;
        let newOrder;
        if (cur.startsWith(column + " asc")) {
            newOrder = column + " desc";
        } else if (cur.startsWith(column + " desc")) {
            newOrder = column + " asc";
        } else {
            newOrder = column + " desc";
        }
        this.state.sortOrder = newOrder;
        this.state.offset = 0;
        await this.load();
    }
    sortIndicator(column) {
        const cur = this.state.sortOrder;
        if (cur.startsWith(column + " asc")) return "fa-caret-up";
        if (cur.startsWith(column + " desc")) return "fa-caret-down";
        return "";
    }

    // --- Search --------------------------------------------------------
    async onSearchInput(ev) {
        this.state.search = ev.target.value;
        this.state.offset = 0;
        await this.load();
    }

    // --- Kanban (drag & drop pour changer de statut) ------------------
    contactsByStatus(status) {
        return this.state.contacts.filter((c) => c.civora_status === status);
    }
    contactsNoStatus() {
        return this.state.contacts.filter((c) => !c.civora_status);
    }
    onDragStart(contactId, ev) {
        ev.dataTransfer.setData("text/plain", String(contactId));
        ev.dataTransfer.effectAllowed = "move";
    }
    onDragOver(ev) {
        ev.preventDefault();
        ev.dataTransfer.dropEffect = "move";
    }
    async onDrop(newStatus, ev) {
        ev.preventDefault();
        const contactId = Number(ev.dataTransfer.getData("text/plain"));
        if (!contactId) return;
        const contact = this.state.contacts.find((c) => c.id === contactId);
        if (!contact || contact.civora_status === newStatus) return;
        try {
            await this.orm.write("res.partner", [contactId], { civora_status: newStatus });
            contact.civora_status = newStatus;
            this.notification.add(`Statut mis à jour : ${STATUS_META[newStatus].label}`, {
                type: "success", sticky: false,
            });
        } catch (e) {
            this.notification.add("Erreur lors du changement de statut.", {
                type: "danger", sticky: false,
            });
        }
    }

    // --- Ouvrir un contact avec siblings pour navigation ◀▶ ----------
    async openContact(c) {
        // Récupère la liste complète des IDs matchant les filtres, dans l'ordre
        // affiché — pour permettre la navigation précédent/suivant depuis la fiche
        // 360° même quand tous les contacts ne sont pas encore chargés.
        let siblingIds = [];
        try {
            siblingIds = await this.orm.call(
                "res.partner", "civora_get_sibling_ids",
                [this.domain, this.state.sortOrder]
            );
        } catch (e) {
            // Fallback : au moins les IDs déjà chargés
            siblingIds = this.state.contacts.map((x) => x.id);
        }
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.contact_360",
            params: {
                contactId: c.id,
                siblingIds: siblingIds,
                origin: {
                    tag: "civora.contacts",
                    params: {},
                    label: "Annuaire",
                },
            },
            target: "current",
        });
    }

    // --- Drawer création -----------------------------------------------
    openCreate() {
        this.state.drawer = { open: true, mode: "create", contactId: false };
    }
    closeDrawer() {
        this.state.drawer = { ...this.state.drawer, open: false };
    }
    async onDrawerSaved() {
        this.closeDrawer();
        await this.load();
    }

    // --- Export CSV ----------------------------------------------------
    async exportCsv() {
        if (this.state.exporting) return;
        this.state.exporting = true;
        try {
            const res = await this.orm.call(
                "res.partner", "civora_export_csv", [this.domain]
            );
            if (!res || !res.content) {
                this.notification.add("Export vide.", { type: "warning" });
                return;
            }
            // Déclencher le téléchargement via <a> temporaire
            const link = document.createElement("a");
            link.href = "data:text/csv;charset=utf-8;base64," + res.content;
            link.download = res.filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            this.notification.add(
                `${res.count} contact(s) exporté(s).`,
                { type: "success", sticky: false }
            );
        } catch (e) {
            this.notification.add("Erreur lors de l'export.", { type: "danger" });
            console.error("[CIVORA-EXPORT] error", e);
        } finally {
            this.state.exporting = false;
        }
    }

    // --- Onglets -------------------------------------------------------
    setTab(id) {
        this.state.activeTab = id;
    }

    /** Onglet contribué actuellement sélectionné, ou null si onglet natif. */
    get activeExternalTab() {
        return this.externalTabs.find((t) => t.id === this.state.activeTab) || null;
    }

    // --- Passerelles depuis les onglets analytiques --------------------

    /**
     * Depuis l'onglet Scoring : clic sur une tranche de score.
     * Bascule sur l'Annuaire en appliquant la plage correspondante, et
     * ouvre le panneau de filtres pour que l'utilisateur voie d'où vient
     * la sélection (pas de filtre invisible).
     */
    async applyScoreRange(min, max, label) {
        this.state.filters.score_min = min;
        this.state.filters.score_max = max;
        this.state.filtersOpen = true;
        this.state.activeTab = "directory";
        this.state.offset = 0;
        await this.load();
        this.notification.add(
            "Annuaire filtré sur la tranche « " + label + " ».",
            { type: "info", sticky: false }
        );
    }

    /**
     * Depuis Scoring / Interactions : ouvrir la fiche 360° d'un contact.
     * Réutilise openContact pour conserver la navigation ◀ X/N ▶ et le
     * retour breadcrumb vers l'écran Contacts.
     */
    async openContactFromAnalytics(contact) {
        await this.openContact(contact);
    }

    // --- Helpers d'affichage ------------------------------------------
    sourceName(c) { return c.civora_source_id ? c.civora_source_id[1] : "—"; }
    company(c) { return c.company_name || "—"; }
    roleLabel(c) {
        if (c.civora_primary_role_id) return c.civora_primary_role_id[1];
        if (c.civora_role_names) return c.civora_role_names.split(",")[0].trim();
        return "—";
    }
    agentName(c) { return c.civora_agent_id ? c.civora_agent_id[1] : "—"; }
    statusLabel(c) {
        return c.civora_status ? (STATUS_META[c.civora_status] || {}).label || c.civora_status : "—";
    }
    statusVariant(c) {
        return c.civora_status ? (STATUS_META[c.civora_status] || {}).variant || "neutral" : "neutral";
    }
    scoreTone(score) {
        if (score >= 80) return "success";
        if (score >= 60) return "warning";
        return "danger";
    }
}

registry.category("actions").add("civora.contacts", CivoraContactsScreen);
