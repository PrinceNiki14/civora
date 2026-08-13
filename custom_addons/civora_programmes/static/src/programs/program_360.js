import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";
import { CivoraInsight } from "@civora_core/components/civora_insight";
import { CivoraTabs } from "@civora_core/components/civora_kit";
import { ProgramDialog } from "./program_dialog";
import { LotDialog, LOT_TYPES, LOT_STATUSES } from "./lot_dialog";
import { LotDrawer } from "./lot_drawer";
import {
    PhaseDialog, MilestoneDialog, GuaranteeDialog, DocumentDialog,
    PHASE_STATUSES, GUARANTEE_TYPES, DOCUMENT_TYPES,
} from "./record_dialogs";
import { PROGRAM_STATUS_META, PROGRAM_TYPE_META, fmtMoneyShort, fmtMonth } from "./programs_screen";

const PROGRAM_FIELDS = [
    "name", "ref", "program_type", "status", "developer", "city", "district", "street",
    "architect", "contractor", "description", "building_count", "total_lots",
    "sold_lots", "reserved_lots", "total_value", "signed_revenue", "start_date",
    "delivery_date", "works_progress", "building_permit", "notary_office", "gfa_reference",
    "amenity_ids", "lot_count", "lot_available", "lot_optioned", "lot_reserved",
    "lot_sold", "lot_blocked", "stock_value", "sold_value", "optioned_value",
    "commercial_progress", "absorption_rate", "realization_rate", "phase_progress",
    "commission_rate", "reservation_fee", "marketing_budget", "negotiator_share",
    "closing_bonus", "internal_notes",
];

const LOT_FIELDS = [
    "name", "building", "floor", "floor_label", "lot_type", "status", "price",
    "surface", "rooms", "bathrooms", "parking", "orientation", "buyer_id", "buyer_name",
];

const TABS = [
    { id: "overview", label: "Vue d'ensemble" },
    { id: "lots", label: "Plan & Lots" },
    { id: "phases", label: "Planning chantier" },
    { id: "reservations", label: "Réservations" },
    { id: "calls", label: "Appels de fonds" },
    { id: "finance", label: "Finances & garanties" },
    { id: "marketing", label: "Commercialisation" },
    { id: "documents", label: "Documents" },
    { id: "team", label: "Équipe" },
];

const LOT_STATUS_FILTERS = [
    { id: "tous", label: "Tous" },
    ...LOT_STATUSES.map((s) => ({ id: s.id, label: s.label })),
];

export class CivoraProgram360 extends Component {
    static template = "civora_programmes.Program360";
    static components = {
        CivoraStatCard, CivoraInsight, CivoraTabs,
        ProgramDialog, LotDialog, LotDrawer,
        PhaseDialog, MilestoneDialog, GuaranteeDialog, DocumentDialog,
    };
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.lotStatusFilters = LOT_STATUS_FILTERS;
        this.phaseStatuses = PHASE_STATUSES;

        this.programId = this.props.action.params?.programId
            || this.props.action.context?.program_id
            || false;

        this.state = useState({
            loading: true,
            program: null,
            amenities: [],
            lots: [],
            phases: [],
            milestones: [],
            calls: [],
            guarantees: [],
            documents: [],
            stakeholders: [],
            tab: "overview",
            lotView: "grille",
            lotStatus: "tous",
            lotSearch: "",
            generating: false,
            commission: {},
            savingCommission: false,
            programDialog: false,
            lotDialog: { open: false, lotId: false },
            lotDrawer: { open: false, lotId: false },
            phaseDialog: { open: false, recordId: false },
            milestoneDialog: { open: false, recordId: false },
            guaranteeDialog: { open: false, recordId: false },
            documentDialog: { open: false, recordId: false },
        });

        onWillStart(() => this.load());
    }

    // ------------------------------------------------------------------
    // Chargement
    // ------------------------------------------------------------------
    async load() {
        this.state.loading = true;
        if (!this.programId) {
            this.state.loading = false;
            return;
        }
        const [prog] = await this.orm.read("civora.program", [this.programId], PROGRAM_FIELDS);
        this.state.program = prog || null;
        if (!prog) {
            this.state.loading = false;
            return;
        }
        this.state.commission = {
            commission_rate: prog.commission_rate || 0,
            reservation_fee: prog.reservation_fee || 0,
            marketing_budget: prog.marketing_budget || 0,
            negotiator_share: prog.negotiator_share || 0,
            closing_bonus: prog.closing_bonus || 0,
            internal_notes: prog.internal_notes || "",
        };

        const dom = [["program_id", "=", this.programId]];
        const [amenities, lots, phases, milestones, calls, guarantees, documents, stakeholders] =
            await Promise.all([
                prog.amenity_ids?.length
                    ? this.orm.read("civora.program.amenity", prog.amenity_ids, ["name"])
                    : [],
                this.orm.searchRead("civora.program.lot", dom, LOT_FIELDS,
                    { order: "building, floor, name" }),
                this.orm.searchRead("civora.program.phase", dom,
                    ["name", "sequence", "date_start", "date_end_planned", "date_end_real",
                     "progress", "status", "is_milestone", "notes"], { order: "sequence, id" }),
                this.orm.searchRead("civora.program.milestone", dom,
                    ["name", "sequence", "cumulative_pct", "step_pct", "phase_id", "issued", "notes"],
                    { order: "sequence, cumulative_pct" }),
                this.orm.searchRead("civora.program.call", dom,
                    ["milestone_id", "lot_id", "partner_id", "amount", "amount_paid",
                     "date_issue", "date_due", "status"], { order: "date_issue desc, id desc" }),
                this.orm.searchRead("civora.program.guarantee", dom,
                    ["guarantee_type", "issuer", "policy_number", "amount",
                     "date_start", "date_end", "is_expiring"], { order: "date_end, id" }),
                this.orm.searchRead("civora.program.document", dom,
                    ["name", "document_type", "file_name", "url", "create_date"],
                    { order: "create_date desc, id desc" }),
                this.orm.searchRead("civora.program.stakeholder", dom,
                    ["role", "name", "phone", "email"], { order: "sequence, id" }),
            ]);

        this.state.amenities = amenities;
        this.state.lots = lots;
        this.state.phases = phases;
        this.state.milestones = milestones;
        this.state.calls = calls;
        this.state.guarantees = guarantees;
        this.state.documents = documents;
        this.state.stakeholders = stakeholders;
        this.state.loading = false;
    }

    // ------------------------------------------------------------------
    // Getters generaux
    // ------------------------------------------------------------------
    get p() {
        return this.state.program || {};
    }
    get tabs() {
        return TABS.map((t) => {
            if (t.id === "lots") return { ...t, count: this.state.lots.length };
            if (t.id === "phases" && this.state.phases.length) {
                return { ...t, count: this.state.phases.length };
            }
            if (t.id === "documents" && this.state.documents.length) {
                return { ...t, count: this.state.documents.length };
            }
            return t;
        });
    }
    get statusMeta() {
        return PROGRAM_STATUS_META[this.p.status]
            || { label: "—", variant: "neutral", gradient: "sky" };
    }
    get typeLabel() {
        return (PROGRAM_TYPE_META[this.p.program_type] || {}).label || "—";
    }
    get headerSub() {
        return [this.p.ref, this.p.district, "Livraison " + fmtMonth(this.p.delivery_date)]
            .filter(Boolean).join(" · ");
    }
    get locLabel() {
        return [this.p.district, this.p.city].filter(Boolean).join(" · ") || "—";
    }
    /**
     * Un programme declare un nombre total de lots (ex. 48 logements au
     * permis) mais la grille de lots peut n'etre saisie que partiellement.
     * On ne masque pas l'ecart : on l'affiche, sinon l'ecran de liste et la
     * fiche donnent deux verites differentes sans que personne ne sache
     * laquelle est bonne.
     */
    /**
     * Complete la grille jusqu'au total declare au permis.
     * Cote serveur, les lots existants ne sont jamais modifies.
     */
    async generateMissingLots() {
        if (this.state.generating) return;
        this.state.generating = true;
        try {
            const res = await this.orm.call(
                "civora.program", "action_generate_missing_lots", [[this.programId]]);
            await this.load();
            this.notification.add(
                `${res.created} lot(s) générés — grille à ${res.total}/${res.target}.`,
                { type: "success" });
        } catch (e) {
            this.notification.add(
                (e && e.data && e.data.message) || "Génération impossible.",
                { type: "warning" });
        } finally {
            this.state.generating = false;
        }
    }

    get lotGapNotice() {
        const declared = this.p.total_lots || 0;
        const captured = this.p.lot_count || 0;
        if (!declared || declared === captured) return "";
        const missing = declared - captured;
        if (missing > 0) {
            return `${captured} lot(s) saisis sur ${declared} déclarés — ${missing} restent à créer dans « Plan & Lots ».`;
        }
        return `${captured} lot(s) saisis pour ${declared} déclarés — le total déclaré est à corriger.`;
    }

    get totalLots() {
        return this.p.total_lots || this.p.lot_count || 0;
    }
    get placedLots() {
        // Un lot est "commercialise" des qu'il est sorti du stock disponible :
        // vendu, reserve ou sous option.
        return (this.p.lot_sold || 0) + (this.p.lot_reserved || 0) + (this.p.lot_optioned || 0);
    }
    get insight() {
        const optioned = this.p.lot_optioned || 0;
        if (optioned) {
            return {
                title: "CIVORA AI · Options à transformer",
                body: `${optioned} option(s) en cours — relancez les prospects avant expiration `
                    + `pour sécuriser la conversion en réservation.`,
            };
        }
        const available = this.p.lot_available || 0;
        if (available) {
            return {
                title: "CIVORA AI · Stock à activer",
                body: `${available} lot(s) disponible(s) au stock — poussez-les sur la marketplace `
                    + `et le réseau d'agents pour accélérer l'absorption.`,
            };
        }
        return {
            title: "CIVORA AI · Stock épuisé",
            body: "Tous les lots enregistrés sont placés. Ajoutez du stock ou passez au programme suivant.",
        };
    }

    setTab(id) {
        this.state.tab = id;
    }

    // ------------------------------------------------------------------
    // Colonne laterale de la vue d'ensemble
    // ------------------------------------------------------------------
    /** Repartition du stock : une ligne + une barre par statut commercial. */
    get advancementRows() {
        const total = this.p.lot_count || 0;
        const pct = (n) => (total ? Math.round((n / total) * 100) : 0);
        return [
            { key: "vendu", label: "Vendus", count: this.p.lot_sold || 0, tone: "accent" },
            { key: "reserve", label: "Réservés", count: this.p.lot_reserved || 0, tone: "success" },
            { key: "optionne", label: "Optionnés", count: this.p.lot_optioned || 0, tone: "warning" },
            { key: "disponible", label: "Disponibles", count: this.p.lot_available || 0, tone: "accent" },
            { key: "bloque", label: "Bloqués", count: this.p.lot_blocked || 0, tone: "danger" },
        ].map((r) => ({ ...r, width: pct(r.count) }));
    }

    /** Icone d'un acteur, choisie d'apres son role. */
    stakeholderIcon(s) {
        const role = (s.role || "").toLowerCase();
        if (role.includes("ouvrage") || role.includes("promoteur")) return "fa-users";
        if (role.includes("architecte")) return "fa-pencil-square-o";
        if (role.includes("étude") || role.includes("etude") || role.includes("bet")) return "fa-comments-o";
        if (role.includes("entreprise") || role.includes("btp")) return "fa-industry";
        if (role.includes("contrôle") || role.includes("controle")) return "fa-check-square-o";
        if (role.includes("notaire")) return "fa-gavel";
        if (role.includes("chantier")) return "fa-wrench";
        if (role.includes("commercial")) return "fa-handshake-o";
        return "fa-user-o";
    }

    /** Premier acteur disposant d'un telephone / email, pour les boutons. */
    get primaryContact() {
        const withPhone = this.state.stakeholders.find((s) => s.phone);
        const withMail = this.state.stakeholders.find((s) => s.email);
        return { phone: withPhone ? withPhone.phone : "", email: withMail ? withMail.email : "" };
    }

    /**
     * Liens rapides. Les deux premiers et le dernier ouvrent les modules
     * CIVORA correspondants ; la tresorerie et le dossier documentaire
     * renvoient vers les onglets du programme courant, qui portent la donnee
     * reelle (les modules Comptabilite et GED globale ne sont pas encore
     * livres, un lien mort serait pire qu'un raccourci utile).
     */
    get quickLinks() {
        return [
            { id: "pipeline", icon: "fa-users", label: "Pipeline commercial", action: "civora.pipeline" },
            { id: "ventes", icon: "fa-file-text-o", label: "Ventes signées", action: "civora.ventes" },
            { id: "tresorerie", icon: "fa-credit-card", label: "Trésorerie & appels", tab: "calls" },
            { id: "documents", icon: "fa-folder-open-o", label: "Dossier documentaire", tab: "documents" },
            { id: "acquereurs", icon: "fa-user-plus", label: "Acquéreurs", action: "civora.buyers" },
        ];
    }

    onQuickLink(link) {
        if (link.tab) {
            this.setTab(link.tab);
            return;
        }
        this.openClientAction(link.action);
    }

    openClientAction(tag) {
        this.action.doAction({ type: "ir.actions.client", tag, target: "current" });
    }

    // --- Formatteurs ---------------------------------------------------
    money(n) {
        return fmtMoneyShort(n) + " FCFA";
    }
    moneyFull(n) {
        return new Intl.NumberFormat("fr-FR").format(Math.round(Number(n || 0))) + " FCFA";
    }
    monthLabel(d) {
        if (!d) return "—";
        const dt = new Date(d);
        if (isNaN(dt)) return "—";
        return dt.toLocaleDateString("fr-FR", { month: "long", year: "numeric" });
    }
    dateLabel(d) {
        if (!d) return "—";
        return String(d).slice(0, 10).split("-").reverse().join("/");
    }
    fmtMonth(d) {
        return fmtMonth(d);
    }

    // ------------------------------------------------------------------
    // Onglet Plan & Lots
    // ------------------------------------------------------------------
    get lotStatusCounts() {
        const counts = { tous: this.state.lots.length };
        for (const s of LOT_STATUSES) {
            counts[s.id] = this.state.lots.filter((l) => l.status === s.id).length;
        }
        return counts;
    }
    get filteredLots() {
        const q = (this.state.lotSearch || "").trim().toLowerCase();
        return this.state.lots.filter((l) => {
            if (this.state.lotStatus !== "tous" && l.status !== this.state.lotStatus) return false;
            if (!q) return true;
            const hay = [l.name, this.lotTypeLabel(l), this.buyerLabel(l), l.building]
                .filter(Boolean).join(" ").toLowerCase();
            return hay.includes(q);
        });
    }
    /** Regroupe les lots par batiment puis par niveau, pour le plan de masse. */
    get buildings() {
        const map = {};
        for (const l of this.filteredLots) {
            const b = l.building || "—";
            (map[b] = map[b] || []).push(l);
        }
        return Object.keys(map).sort().map((code) => {
            const lots = map[code];
            const maxFloor = lots.reduce((m, l) => Math.max(m, l.floor || 0), 0);
            const minFloor = lots.reduce((m, l) => Math.min(m, l.floor || 0), maxFloor);
            const levels = [];
            for (let f = maxFloor; f >= minFloor; f--) {
                levels.push({
                    floor: f,
                    label: f ? "R+" + f : "RDC",
                    lots: lots.filter((l) => (l.floor || 0) === f)
                        .sort((a, b) => (a.name || "").localeCompare(b.name || "")),
                });
            }
            return { code, count: lots.length, maxFloor, levels };
        });
    }
    lotTypeLabel(l) {
        return (LOT_TYPES.find((t) => t.id === l.lot_type) || {}).label || "—";
    }
    lotStatusMeta(l) {
        return LOT_STATUSES.find((s) => s.id === l.status) || { label: "—", variant: "neutral" };
    }
    lotTileClass(l) {
        return "civora-prg-tile civora-prg-tile--" + (l.status || "disponible");
    }
    buyerLabel(l) {
        if (l.buyer_id) return l.buyer_id[1];
        return l.buyer_name || "";
    }
    orientationShort(l) {
        const map = {
            nord: "Nord", ne: "N-E", est: "Est", se: "S-E",
            sud: "Sud", so: "S-O", ouest: "Ouest", no: "N-O",
        };
        return map[l.orientation] || "—";
    }

    setLotView(v) {
        this.state.lotView = v;
    }
    setLotStatus(id) {
        this.state.lotStatus = id;
    }
    onLotSearch(ev) {
        this.state.lotSearch = ev.target.value;
    }

    openLotCreate() {
        this.state.lotDialog = { open: true, lotId: false };
    }
    openLotEdit(lotId) {
        this.state.lotDrawer = { open: false, lotId: false };
        this.state.lotDialog = { open: true, lotId };
    }
    closeLotDialog() {
        this.state.lotDialog = { open: false, lotId: false };
    }
    async onLotSaved() {
        this.closeLotDialog();
        await this.load();
    }
    openLot(l) {
        this.state.lotDrawer = { open: true, lotId: l.id };
    }
    closeLotDrawer() {
        this.state.lotDrawer = { open: false, lotId: false };
    }
    async onLotChanged() {
        await this.load();
    }
    async deleteLot(l) {
        await this.orm.unlink("civora.program.lot", [l.id]);
        this.notification.add(`Lot ${l.name} supprimé`, { type: "success" });
        await this.load();
    }

    // ------------------------------------------------------------------
    // Onglet Planning chantier
    // ------------------------------------------------------------------
    phaseStatusMeta(ph) {
        return PHASE_STATUSES.find((s) => s.id === ph.status) || { label: "—", variant: "neutral" };
    }
    openPhaseCreate() {
        this.state.phaseDialog = { open: true, recordId: false };
    }
    openPhaseEdit(ph) {
        this.state.phaseDialog = { open: true, recordId: ph.id };
    }
    closePhaseDialog() {
        this.state.phaseDialog = { open: false, recordId: false };
    }
    async onPhaseSaved() {
        this.closePhaseDialog();
        await this.load();
    }
    async deletePhase(ph) {
        await this.orm.unlink("civora.program.phase", [ph.id]);
        await this.load();
    }

    // ------------------------------------------------------------------
    // Onglet Réservations
    // ------------------------------------------------------------------
    get reservationRows() {
        return this.state.lots.filter((l) =>
            ["optionne", "reserve", "vendu"].includes(l.status)
        );
    }

    // ------------------------------------------------------------------
    // Onglet Appels de fonds
    // ------------------------------------------------------------------
    get callStats() {
        const eligible = this.state.lots.filter((l) => l.status === "vendu").length;
        const called = this.state.calls.reduce((s, c) => s + (c.amount || 0), 0);
        const cashed = this.state.calls.reduce((s, c) => s + (c.amount_paid || 0), 0);
        return {
            eligible,
            total: this.state.lots.length,
            called,
            cashed,
            remaining: Math.max(0, called - cashed),
            cashedPct: called ? Math.round((cashed / called) * 100) : 0,
        };
    }
    milestonePhaseLabel(m) {
        return m.phase_id ? m.phase_id[1] : "—";
    }
    callLotLabel(c) {
        return c.lot_id ? c.lot_id[1] : "—";
    }
    callPartnerLabel(c) {
        if (c.partner_id) return c.partner_id[1];
        // Repli sur le libelle libre porte par le lot tant qu'aucun contact
        // CIVORA n'est rattache a la vente.
        const lot = c.lot_id && this.state.lots.find((l) => l.id === c.lot_id[0]);
        return (lot && lot.buyer_name) || "—";
    }
    callStatusMeta(c) {
        const map = {
            emis: { label: "Émis", variant: "info" },
            encaisse: { label: "Encaissé", variant: "success" },
            retard: { label: "En retard", variant: "danger" },
            annule: { label: "Annulé", variant: "neutral" },
        };
        return map[c.status] || { label: "—", variant: "neutral" };
    }

    async seedStandardSchedule() {
        if (this.state.milestones.length) {
            this.notification.add("La grille d'échéancier existe déjà.", { type: "warning" });
            return;
        }
        await this.orm.call("civora.program", "action_seed_standard_schedule", [[this.programId]]);
        this.notification.add("Grille VEFA standard initialisée", { type: "success" });
        await this.load();
    }
    openMilestoneCreate() {
        this.state.milestoneDialog = { open: true, recordId: false };
    }
    openMilestoneEdit(m) {
        this.state.milestoneDialog = { open: true, recordId: m.id };
    }
    closeMilestoneDialog() {
        this.state.milestoneDialog = { open: false, recordId: false };
    }
    async onMilestoneSaved() {
        this.closeMilestoneDialog();
        await this.load();
    }
    async deleteMilestone(m) {
        await this.orm.unlink("civora.program.milestone", [m.id]);
        await this.load();
    }
    async issueMilestone(m) {
        const created = await this.orm.call(
            "civora.program.milestone", "action_issue_calls", [[m.id]]
        );
        if (created) {
            this.notification.add(`${created} appel(s) de fonds émis`, { type: "success" });
        } else {
            this.notification.add(
                "Aucun appel à émettre : aucun lot vendu sans appel pour ce jalon.",
                { type: "warning" }
            );
        }
        await this.load();
    }
    async markCallPaid(c) {
        await this.orm.call("civora.program.call", "action_mark_paid", [[c.id]]);
        await this.load();
    }
    exportCalls() {
        const head = ["Jalon", "Lot", "Acquéreur", "Montant appelé", "Encaissé", "Émission", "Statut"];
        const rows = this.state.calls.map((c) => [
            c.milestone_id ? c.milestone_id[1] : "",
            this.callLotLabel(c), this.callPartnerLabel(c),
            c.amount || 0, c.amount_paid || 0,
            this.dateLabel(c.date_issue), this.callStatusMeta(c).label,
        ]);
        const esc = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
        const csv = [head, ...rows].map((r) => r.map(esc).join(";")).join("\n");
        const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `appels-de-fonds-${this.p.ref || "programme"}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    }

    // ------------------------------------------------------------------
    // Onglet Finances & garanties
    // ------------------------------------------------------------------
    guaranteeTypeLabel(g) {
        return (GUARANTEE_TYPES.find((t) => t.id === g.guarantee_type) || {}).label || "—";
    }
    get expiringCount() {
        return this.state.guarantees.filter((g) => g.is_expiring).length;
    }
    openGuaranteeCreate() {
        this.state.guaranteeDialog = { open: true, recordId: false };
    }
    openGuaranteeEdit(g) {
        this.state.guaranteeDialog = { open: true, recordId: g.id };
    }
    closeGuaranteeDialog() {
        this.state.guaranteeDialog = { open: false, recordId: false };
    }
    async onGuaranteeSaved() {
        this.closeGuaranteeDialog();
        await this.load();
    }
    async deleteGuarantee(g) {
        await this.orm.unlink("civora.program.guarantee", [g.id]);
        await this.load();
    }

    setCommission(key, ev) {
        const el = ev.target;
        this.state.commission[key] = el.type === "number"
            ? (el.value === "" ? 0 : Number(el.value))
            : el.value;
    }
    async saveCommission() {
        if (this.state.savingCommission) return;
        this.state.savingCommission = true;
        try {
            await this.orm.write("civora.program", [this.programId], { ...this.state.commission });
            this.notification.add("Paramètres de commission enregistrés", { type: "success" });
            await this.load();
        } finally {
            this.state.savingCommission = false;
        }
    }

    // ------------------------------------------------------------------
    // Onglet Documents
    // ------------------------------------------------------------------
    documentTypeLabel(d) {
        return (DOCUMENT_TYPES.find((t) => t.id === d.document_type) || {}).label || "—";
    }
    documentUrl(d) {
        return d.url || `/web/content/civora.program.document/${d.id}/datas?download=true`;
    }
    openDocumentCreate() {
        this.state.documentDialog = { open: true, recordId: false };
    }
    closeDocumentDialog() {
        this.state.documentDialog = { open: false, recordId: false };
    }
    async onDocumentSaved() {
        this.closeDocumentDialog();
        await this.load();
    }
    async deleteDocument(d) {
        await this.orm.unlink("civora.program.document", [d.id]);
        await this.load();
    }

    // ------------------------------------------------------------------
    // En-tete : actions
    // ------------------------------------------------------------------
    openEdit() {
        this.state.programDialog = true;
    }
    closeProgramDialog() {
        this.state.programDialog = false;
    }
    async onProgramSaved() {
        this.closeProgramDialog();
        await this.load();
    }
    openPipeline() {
        this.openClientAction("civora.pipeline");
    }
    backToList() {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.programs",
            target: "current",
        });
    }
    async share() {
        const url = `${window.location.origin}${window.location.pathname}#action=civora.program_360&program_id=${this.programId}`;
        try {
            await navigator.clipboard.writeText(url);
            this.notification.add("Lien de la fiche copié", { type: "success" });
        } catch {
            this.notification.add(url, { type: "info", sticky: true });
        }
    }
    brochure() {
        window.print();
    }
}

registry.category("actions").add("civora.program_360", CivoraProgram360);
