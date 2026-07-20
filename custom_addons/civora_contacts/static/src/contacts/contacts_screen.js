import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";
import { CivoraBadge, CivoraAvatar, CivoraTabs, CivoraProgress } from "@civora_core/components/civora_kit";
import { ContactDrawer } from "./contact_drawer";

const DOMAIN_BASE = [["civora_is_contact", "=", true]];

// Onglets (seul "Annuaire" est actif pour l'instant).
const TABS = [
    { id: "directory", label: "Annuaire" },
    { id: "segments", label: "Segments" },
    { id: "campaigns", label: "Campagnes" },
    { id: "interactions", label: "Interactions" },
    { id: "scoring", label: "Scoring" },
    { id: "imports", label: "Imports" },
    { id: "rgpd", label: "RGPD" },
];

// Pastilles de segment -> filtre par role.
const SEGMENTS = [
    { id: "tous", label: "Tous", roleCode: null },
    { id: "acheteurs", label: "Acheteurs", roleCode: "acheteur" },
    { id: "locataires", label: "Locataires", roleCode: "locataire" },
    { id: "proprietaires", label: "Propriétaires", roleCode: "proprietaire" },
    { id: "investisseurs", label: "Investisseurs", roleCode: "investisseur" },
];

export class CivoraContactsScreen extends Component {
    static template = "civora_contacts.Screen";
    static components = { CivoraStatCard, CivoraBadge, CivoraAvatar, CivoraTabs, CivoraProgress, ContactDrawer };
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.tabs = TABS;
        this.segments = SEGMENTS;

        this.state = useState({
            loading: true,
            contacts: [],
            stats: { total: 0, chaud: 0, vip: 0, avg: 0 },
            activeTab: "directory",
            segment: "tous",
            search: "",
            drawer: { open: false, mode: "view", contactId: false },
        });

        onWillStart(() => this.load());
    }

    // --- Domaine courant (base + segment + recherche) ------------------
    get domain() {
        const dom = [...DOMAIN_BASE];
        const seg = SEGMENTS.find((s) => s.id === this.state.segment);
        if (seg && seg.roleCode) {
            dom.push(["civora_role_ids.code", "=", seg.roleCode]);
        }
        const q = (this.state.search || "").trim();
        if (q) {
            dom.push("|", "|", ["name", "ilike", q], ["city", "ilike", q], ["email", "ilike", q]);
        }
        return dom;
    }

    // --- Chargement des donnees ---------------------------------------
    async load() {
        this.state.loading = true;
        const domain = this.domain;

        // Stats (sur le domaine de base, independamment de la recherche)
        const total = await this.orm.searchCount("res.partner", DOMAIN_BASE);
        const chaud = await this.orm.searchCount("res.partner", [...DOMAIN_BASE, ["civora_status", "=", "chaud"]]);
        const vip = await this.orm.searchCount("res.partner", [...DOMAIN_BASE, ["civora_ai_score", ">=", 85]]);
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

        // Liste (domaine filtre)
        const records = await this.orm.searchRead(
            "res.partner",
            domain,
            [
                "name", "company_name", "email", "civora_source_id",
                "civora_primary_role_id", "civora_role_names", "civora_ai_score",
                "civora_status", "civora_agent_id", "civora_next_action",
            ],
            { limit: 100, order: "civora_ai_score desc, name asc" }
        );
        this.state.contacts = records;
        this.state.loading = false;
    }

    // --- Helpers d'affichage ------------------------------------------
    sourceName(c) {
        return c.civora_source_id ? c.civora_source_id[1] : "—";
    }
    company(c) {
        return c.company_name || "—";
    }
    roleLabel(c) {
        if (c.civora_primary_role_id) {
            return c.civora_primary_role_id[1];
        }
        if (c.civora_role_names) {
            return c.civora_role_names.split(",")[0].trim();
        }
        return "—";
    }
    agentName(c) {
        return c.civora_agent_id ? c.civora_agent_id[1] : "—";
    }
    statusLabel(c) {
        const map = { chaud: "Chaud", actif: "Actif", qualifie: "Qualifié", a_risque: "À risque", inactif: "Inactif" };
        return c.civora_status ? map[c.civora_status] || c.civora_status : "—";
    }
    statusVariant(c) {
        const map = { chaud: "danger", a_risque: "warning", actif: "success", qualifie: "info", inactif: "neutral" };
        return c.civora_status ? map[c.civora_status] || "neutral" : "neutral";
    }
    scoreTone(score) {
        if (score >= 80) return "success";
        if (score >= 60) return "warning";
        return "danger";
    }

    // --- Interactions --------------------------------------------------
    setTab(id) {
        this.state.activeTab = id;
    }
    async setSegment(id) {
        this.state.segment = id;
        await this.load();
    }
    async onSearchInput(ev) {
        this.state.search = ev.target.value;
        await this.load();
    }
    // --- Drawer (fiche 360 / creation / edition) ----------------------
    openCreate() {
        this.state.drawer = { open: true, mode: "create", contactId: false };
    }
    openContact(c) {
        // Ouvre la page 360 dediee (client action) au lieu du drawer de lecture.
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.contact_360",
            params: { contactId: c.id },
            target: "current",
        });
    }
    closeDrawer() {
        this.state.drawer = { ...this.state.drawer, open: false };
    }
    async onDrawerSaved() {
        this.closeDrawer();
        await this.load();
    }
}

registry.category("actions").add("civora.contacts", CivoraContactsScreen);
