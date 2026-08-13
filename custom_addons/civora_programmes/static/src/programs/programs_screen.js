import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";
import { CivoraInsight } from "@civora_core/components/civora_insight";
import { ProgramDialog } from "./program_dialog";

// Metadonnees d'affichage par statut de programme.
export const PROGRAM_STATUS_META = {
    etude: { label: "Étude", variant: "info", gradient: "sky" },
    commercialisation: { label: "Commercialisation", variant: "accent", gradient: "indigo" },
    travaux: { label: "Travaux", variant: "success", gradient: "emerald" },
    livre: { label: "Livré", variant: "warning", gradient: "amber" },
};

export const PROGRAM_TYPE_META = {
    neuf: { label: "Neuf" },
    vefa: { label: "VEFA" },
    lotissement: { label: "Lotissement" },
};

const STATUS_FILTERS = [
    { id: "tous", label: "Tous" },
    { id: "etude", label: "Étude" },
    { id: "commercialisation", label: "Commercialisation" },
    { id: "travaux", label: "Travaux" },
    { id: "livre", label: "Livré" },
];

const TYPE_FILTERS = [
    { id: "tous", label: "Tous" },
    { id: "neuf", label: "Neuf" },
    { id: "vefa", label: "VEFA" },
    { id: "lotissement", label: "Lotissement" },
];

const FIELDS = [
    "name", "ref", "slug", "program_type", "status", "developer", "city", "district",
    "total_lots", "sold_lots", "reserved_lots", "total_value", "signed_revenue",
    "delivery_date", "works_progress", "commercial_progress", "absorption_rate",
    "lot_count", "lot_available", "lot_sold", "lot_reserved", "lot_optioned",
    "stock_value", "sold_value",
];

/** Formate un montant en notation courte francophone (Md / M / k). */
export function fmtMoneyShort(n) {
    n = Number(n || 0);
    if (n >= 1e9) return (n / 1e9).toFixed(2) + " Md";
    if (n >= 1e6) {
        // Une decimale seulement quand le montant n'est pas un compte rond,
        // pour rester lisible sur les cartes ("58 M" plutot que "58.0 M").
        const m = n / 1e6;
        return (Math.abs(m - Math.round(m)) < 0.05 ? Math.round(m) : m.toFixed(1)) + " M";
    }
    if (n >= 1e3) return Math.round(n / 1e3) + " k";
    return "" + Math.round(n);
}

/** "2026-09" a partir d'une date Odoo ; "—" si absente. */
export function fmtMonth(d) {
    if (!d) return "—";
    return String(d).slice(0, 7);
}

export class CivoraProgramsScreen extends Component {
    static template = "civora_programmes.Programs";
    static components = { CivoraStatCard, CivoraInsight, ProgramDialog };
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.statusFilters = STATUS_FILTERS;
        this.typeFilters = TYPE_FILTERS;

        this.state = useState({
            loading: true,
            programs: [],
            stats: {
                count: 0, totalLots: 0, available: 0, sold: 0, reserved: 0,
                signed: 0, potential: 0, absorption: 0, commercialisation: 0,
            },
            view: "grid",
            search: "",
            statusFilter: "tous",
            typeFilter: "tous",
            dialog: { open: false, programId: false },
        });

        onWillStart(() => this.load());
    }

    // --- Domaine / chargement -----------------------------------------
    get domain() {
        const dom = [];
        if (this.state.statusFilter !== "tous") {
            dom.push(["status", "=", this.state.statusFilter]);
        }
        if (this.state.typeFilter !== "tous") {
            dom.push(["program_type", "=", this.state.typeFilter]);
        }
        const q = (this.state.search || "").trim();
        if (q) {
            dom.push("|", "|", "|",
                ["name", "ilike", q], ["city", "ilike", q],
                ["developer", "ilike", q], ["ref", "ilike", q]);
        }
        return dom;
    }

    async load() {
        this.state.loading = true;
        const rows = await this.orm.searchRead(
            "civora.program", this.domain, FIELDS, { limit: 200, order: "ref" }
        );
        this.state.programs = rows;

        // Les KPI d'en-tete portent sur l'ensemble du portefeuille, pas sur le
        // resultat filtre : ils doivent rester stables quand on navigue.
        const all = await this.orm.searchRead("civora.program", [], FIELDS, { limit: 500 });
        const totalLots = all.reduce((s, p) => s + (p.total_lots || p.lot_count || 0), 0);
        const sold = all.reduce((s, p) => s + (p.sold_lots || p.lot_sold || 0), 0);
        const reserved = all.reduce((s, p) => s + (p.reserved_lots || p.lot_reserved || 0), 0);
        const signed = all.reduce((s, p) => s + (p.signed_revenue || p.sold_value || 0), 0);
        const potential = all.reduce((s, p) => s + (p.total_value || p.stock_value || 0), 0);
        this.state.stats = {
            count: all.length,
            totalLots,
            available: Math.max(0, totalLots - sold - reserved),
            sold,
            reserved,
            signed,
            potential,
            absorption: totalLots ? Math.round((sold / totalLots) * 100) : 0,
            commercialisation: all.filter((p) => p.status === "commercialisation").length,
        };
        this.state.loading = false;
    }

    // --- Getters d'affichage ------------------------------------------
    get headerSub() {
        const s = this.state.stats;
        return `${s.count} programme${s.count > 1 ? "s" : ""} · ${s.totalLots} lots · ${s.absorption}% d'absorption`;
    }
    get insightBody() {
        // L'insight pointe le programme dont la commercialisation est la plus
        // en retard par rapport a l'avancement du chantier.
        const candidates = this.state.programs.filter((p) => p.status !== "livre");
        if (!candidates.length) {
            return "Aucun écart de cadence détecté sur le portefeuille en cours.";
        }
        const worst = candidates.reduce((a, b) =>
            (a.commercial_progress || 0) <= (b.commercial_progress || 0) ? a : b
        );
        const gap = Math.max(0, 100 - (worst.commercial_progress || 0));
        return `${worst.name} : la cadence commerciale est inférieure de ${gap}% au plan. `
            + `Proposez un boost marketplace et une remise de pré-livraison pour relancer l'absorption.`;
    }

    statusMeta(p) {
        return PROGRAM_STATUS_META[p.status] || { label: "—", variant: "neutral", gradient: "sky" };
    }
    typeLabel(p) {
        return (PROGRAM_TYPE_META[p.program_type] || {}).label || "—";
    }
    coverClass(p) {
        return "civora-prg-cover civora-prg-cover--" + this.statusMeta(p).gradient;
    }
    locLabel(p) {
        return [p.district, p.city].filter(Boolean).join(" · ") || "—";
    }
    soldOf(p) {
        return p.sold_lots || p.lot_sold || 0;
    }
    reservedOf(p) {
        return p.reserved_lots || p.lot_reserved || 0;
    }
    availableOf(p) {
        const total = p.total_lots || p.lot_count || 0;
        return Math.max(0, total - this.soldOf(p) - this.reservedOf(p));
    }
    placedOf(p) {
        return this.soldOf(p) + this.reservedOf(p);
    }
    totalOf(p) {
        return p.total_lots || p.lot_count || 0;
    }
    valueLabel(p) {
        return fmtMoneyShort(p.total_value || p.stock_value) + " FCFA";
    }
    signedLabel(p) {
        return fmtMoneyShort(p.signed_revenue || p.sold_value) + " FCFA";
    }
    deliveryLabel(p) {
        return fmtMonth(p.delivery_date);
    }
    kpiSigned() {
        return fmtMoneyShort(this.state.stats.signed) + " FCFA";
    }
    kpiPotential() {
        return "sur " + fmtMoneyShort(this.state.stats.potential) + " FCFA potentiel";
    }

    // --- Interactions --------------------------------------------------
    setView(v) {
        this.state.view = v;
    }
    async setStatus(id) {
        this.state.statusFilter = id;
        await this.load();
    }
    async setType(id) {
        this.state.typeFilter = id;
        await this.load();
    }
    async onSearchInput(ev) {
        this.state.search = ev.target.value;
        await this.load();
    }

    openProgram(p) {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.program_360",
            params: { programId: p.id },
            target: "current",
        });
    }
    openPipeline() {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.placeholder",
            target: "current",
        });
    }
    openCreate() {
        this.state.dialog = { open: true, programId: false };
    }
    closeDialog() {
        this.state.dialog = { ...this.state.dialog, open: false };
    }
    async onDialogSaved() {
        this.closeDialog();
        await this.load();
    }

    onImport() {
        this.notification.add("Import CSV/Excel — bientôt disponible", { type: "info" });
    }

    /** Export CSV du portefeuille filtre (genere cote navigateur). */
    onExport() {
        const head = [
            "Référence", "Programme", "Type", "Statut", "Ville", "Quartier", "Promoteur",
            "Total lots", "Vendus", "Réservés", "Disponibles",
            "Commercialisation %", "Chantier %", "CA signé", "Valeur programme", "Livraison",
        ];
        const rows = this.state.programs.map((p) => [
            p.ref, p.name, this.typeLabel(p), this.statusMeta(p).label, p.city, p.district,
            p.developer, this.totalOf(p), this.soldOf(p), this.reservedOf(p), this.availableOf(p),
            p.commercial_progress, p.works_progress,
            p.signed_revenue || p.sold_value || 0, p.total_value || p.stock_value || 0,
            this.deliveryLabel(p),
        ]);
        const esc = (v) => `"${String(v === false || v === undefined || v === null ? "" : v).replace(/"/g, '""')}"`;
        const csv = [head, ...rows].map((r) => r.map(esc).join(";")).join("\n");
        const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "civora-programmes.csv";
        a.click();
        URL.revokeObjectURL(url);
        this.notification.add("Export généré", { type: "success" });
    }
}

registry.category("actions").add("civora.programs", CivoraProgramsScreen);
