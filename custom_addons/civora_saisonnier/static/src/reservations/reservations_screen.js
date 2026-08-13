/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";
import { ReservationDrawer } from "./reservation_drawer";

const STATE_LABELS = {
    draft: "Brouillon",
    confirmed: "Confirmée",
    checkin: "En séjour",
    checkout: "Terminée",
    cancelled: "Annulée",
};

const SOURCE_LABELS = {
    direct: "Direct",
    airbnb: "Airbnb",
    booking: "Booking.com",
    whatsapp: "WhatsApp",
    referral: "Référence",
    other: "Autre",
};

const CHANNEL_ICON = {
    email: "fa-envelope-o",
    sms: "fa-mobile",
    whatsapp: "fa-whatsapp",
    upsell: "fa-shopping-basket",
};

class CivoraReservationsScreen extends Component {
    static template = "civora_saisonnier.ReservationsScreen";
    static components = { CivoraStatCard, ReservationDrawer };
    static props = { "*": true };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            error: "",
            kpis: {},
            d: {},                      // payload get_seasonal_dashboard
            checkinsToday: [],
            checkoutsAndCleaning: [],
            recentReviews: [],
            activeTab: "calendrier",
            filter: "all",
            search: "",
            threadId: null,
            reply: "",
            tplCategory: "all",
            drawerOpen: false,
            drawerMode: "create",
            drawerRecordId: false,
        });
        onWillStart(() => this.load());
    }

    async load() {
        try {
            const [kpis, dash, checkins, checkouts, reviews] = await Promise.all([
                this.orm.call("civora.reservation", "get_seasonal_kpis", []),
                this.orm.call("civora.reservation", "get_seasonal_dashboard", []),
                this.orm.call("civora.reservation", "get_checkins_today", []),
                this.orm.call("civora.reservation", "get_checkouts_and_cleaning", []),
                this.orm.call("civora.reservation", "get_recent_reviews", []),
            ]);
            this.state.kpis = kpis;
            this.state.d = dash;
            this.state.checkinsToday = checkins;
            this.state.checkoutsAndCleaning = checkouts;
            this.state.recentReviews = reviews;
            if (!this.state.threadId && (dash.threads || []).length) {
                this.state.threadId = dash.threads[0].id;
            }
            this.state.error = "";
        } catch (e) {
            this.state.error =
                "Impossible de charger le module Saisonnier. Vérifiez que le module est à jour.";
            console.error("civora.reservations load error", e);
        }
        this.state.loading = false;
    }

    /* =============================== FORMATS =============================== */
    fmtMoney(v) {
        if (!v && v !== 0) return "0";
        return `${Math.round(v)}`.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
    }

    fmtShort(v) {
        const n = v || 0;
        if (n >= 1000000) {
            const m = n / 1000000;
            return (m % 1 === 0 ? m : m.toFixed(2).replace(".", ",")) + "M";
        }
        if (n >= 1000) return Math.round(n / 1000) + "k";
        return `${n}`;
    }

    /** Formate une variation avec son signe : +24%, -9%, 0%. */
    fmtDelta(v, unit) {
        const n = Math.round(v || 0);
        const sign = n > 0 ? "+" : "";
        return `${sign}${n}${unit || ""}`;
    }

    fmtPct(v) {
        const n = v || 0;
        return `${n}`.replace(".", ",");
    }

    stateLabel(s) { return STATE_LABELS[s] || s; }
    stateClass(s) {
        return { draft: "muted", confirmed: "info", checkin: "accent",
                 checkout: "success", cancelled: "danger" }[s] || "";
    }
    sourceLabel(s) { return SOURCE_LABELS[s] || s; }
    channelIcon(c) { return CHANNEL_ICON[c] || "fa-envelope-o"; }
    ratingStars(r) { return Math.round(r || 0); }
    starList(r) {
        const n = Math.round(r || 0);
        return [1, 2, 3, 4, 5].map((i) => ({ i, on: i <= n }));
    }

    /* ================================ TABS ================================= */
    get tabs() {
        const d = this.state.d;
        return [
            { key: "calendrier", label: "Calendrier" },
            { key: "reservations", label: "Réservations", count: (d.reservations || []).length },
            { key: "inbox", label: "Inbox", count: this.unreadTotal },
            { key: "voyageurs", label: "Voyageurs", count: (d.guests || []).length },
            { key: "biens", label: "Mes biens", count: (d.planning || []).length },
            { key: "menage", label: "Ménage & maintenance" },
            { key: "channels", label: "Channel Manager" },
            { key: "tarification", label: "Tarification" },
            { key: "marche", label: "Marché & rate shopper" },
            { key: "booking", label: "Booking Engine" },
            { key: "journey", label: "Guest Journey" },
            { key: "upsells", label: "Upsells" },
            { key: "incidents", label: "Incidents & caution" },
            { key: "revenus", label: "Paiements & revenus" },
            { key: "regles", label: "Règles & frais" },
        ];
    }

    isTab(k) { return `${this.state.activeTab}` === `${k}`; }
    setTab(k) { this.state.activeTab = k; }

    get unreadTotal() {
        return (this.state.d.threads || []).reduce((s, t) => s + (t.unread || 0), 0);
    }

    get dynamicSubtitle() {
        const k = this.state.kpis;
        const d = this.state.d;
        const props = (d.planning || []).length || k.property_count || 0;
        return `${d.month_label || ""} · ${props} biens · ${k.occupation_rate || 0}% d'occupation`;
    }

    /* ============================= CALENDRIER ============================== */
    get days() {
        const n = this.state.d.days_in_month || 30;
        const out = [];
        for (let i = 1; i <= n; i++) out.push(i);
        return out;
    }

    isToday(day) { return day === this.state.d.today_day; }

    barStyle(bar) {
        const total = this.state.d.days_in_month || 30;
        const left = ((bar.start_day - 1) / total) * 100;
        const width = (bar.span / total) * 100;
        return `left:${left}%;width:${width}%;`;
    }

    barClass(bar) {
        if (bar.state === "draft") return "civora-sais-bar--option";
        if (bar.state === "cancelled") return "civora-sais-bar--blocked";
        return "civora-sais-bar--confirmed";
    }

    /* ============================ RESERVATIONS ============================= */
    get filteredReservations() {
        let list = this.state.d.reservations || [];
        const f = this.state.filter;
        const today = new Date().toISOString().slice(0, 10);
        if (f === "confirmed") list = list.filter((r) => r.state === "confirmed");
        else if (f === "in_stay") list = list.filter((r) => r.state === "checkin");
        else if (f === "checkin_today") list = list.filter((r) => r.checkin === today);
        else if (f === "checkout_today") list = list.filter((r) => r.checkout === today);
        else if (f === "upcoming") list = list.filter((r) => r.checkin > today);
        const q = (this.state.search || "").toLowerCase().trim();
        if (q) {
            list = list.filter((r) =>
                (r.guest || "").toLowerCase().includes(q) ||
                (r.property || "").toLowerCase().includes(q) ||
                (r.ref || "").toLowerCase().includes(q));
        }
        return list;
    }

    isFilter(f) { return `${this.state.filter}` === `${f}`; }
    setFilter(f) { this.state.filter = f; }
    onSearch(ev) { this.state.search = ev.target.value; }

    /* ================================ INBOX ================================ */
    get threads() { return this.state.d.threads || []; }

    get activeThread() {
        return this.threads.find((t) => t.id === this.state.threadId) || null;
    }

    isThread(id) { return this.state.threadId === id; }

    async selectThread(id) {
        this.state.threadId = id;
        const th = this.threads.find((t) => t.id === id);
        if (th && th.unread) {
            await this.orm.call("civora.seasonal.thread", "action_mark_read", [[id]]);
            await this.load();
            this.state.threadId = id;
        }
    }

    onReply(ev) { this.state.reply = ev.target.value; }

    useTemplate(tpl) { this.state.reply = tpl.body; }

    async sendReply() {
        const body = (this.state.reply || "").trim();
        if (!body || !this.state.threadId) return;
        await this.orm.create("civora.seasonal.message", [{
            thread_id: this.state.threadId,
            body,
            direction: "out",
            unread: false,
        }]);
        this.state.reply = "";
        const keep = this.state.threadId;
        await this.load();
        this.state.threadId = keep;
        this.notification.add("Message envoyé au voyageur.", { type: "success" });
    }

    /* ============================== CHANNELS =============================== */
    async toggleChannel(ch) {
        await this.orm.call("civora.seasonal.channel", "action_toggle_connection", [[ch.id]]);
        await this.load();
    }

    async syncAll() {
        const ids = (this.state.d.channels || []).filter((c) => c.connected).map((c) => c.id);
        if (!ids.length) return;
        await this.orm.call("civora.seasonal.channel", "action_sync", [ids]);
        await this.load();
        this.notification.add("Canaux synchronisés.", { type: "success" });
    }

    async resolveConflict(c) {
        await this.orm.call("civora.seasonal.conflict", "action_resolve", [[c.id]]);
        await this.load();
        this.notification.add("Conflit marqué comme résolu.", { type: "success" });
    }

    /* =============================== UPSELLS =============================== */
    async toggleUpsell(u) {
        await this.orm.call("civora.seasonal.upsell", "action_toggle_active", [[u.id]]);
        await this.load();
    }

    /* =============================== REVENUS =============================== */
    async markPaid(p) {
        await this.orm.call("civora.seasonal.payout", "action_mark_paid", [[p.id]]);
        await this.load();
        this.notification.add("Versement marqué comme reçu.", { type: "success" });
    }

    async sendStatements() {
        const ids = (this.state.d.statements || []).map((s) => s.id);
        if (!ids.length) return;
        await this.orm.call("civora.seasonal.owner.statement", "action_send_statement", [ids]);
        await this.load();
        this.notification.add("Relevés propriétaires envoyés.", { type: "success" });
    }

    /* ================================ REGLES =============================== */
    async toggleAutoMessage(m) {
        await this.orm.call("civora.seasonal.auto.message", "action_toggle", [[m.id]]);
        await this.load();
    }

    /* ============================== EXPORTS ================================ */
    exportCsv(rows, headers, filename) {
        const esc = (v) => `"${`${v == null ? "" : v}`.replace(/"/g, '""')}"`;
        const lines = [headers.map((h) => esc(h.label)).join(";")];
        for (const r of rows) lines.push(headers.map((h) => esc(r[h.key])).join(";"));
        const blob = new Blob(["﻿" + lines.join("\n")], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
        this.notification.add(`${rows.length} lignes exportées.`, { type: "success" });
    }

    exportGuests() {
        this.exportCsv(this.state.d.guests || [], [
            { key: "name", label: "Voyageur" }, { key: "country", label: "Pays" },
            { key: "stays", label: "Séjours" }, { key: "nights", label: "Nuits" },
            { key: "total", label: "Total dépensé" }, { key: "last_stay", label: "Dernier séjour" },
            { key: "rating", label: "Note" }, { key: "tag_label", label: "Segment" },
        ], "civora-voyageurs.csv");
    }

    exportIncidents() {
        this.exportCsv(this.state.d.incidents || [], [
            { key: "ref", label: "Référence" }, { key: "property", label: "Bien" },
            { key: "guest", label: "Voyageur" }, { key: "date", label: "Date" },
            { key: "type", label: "Type" }, { key: "description", label: "Description" },
            { key: "amount", label: "Montant" }, { key: "severity_label", label: "Sévérité" },
            { key: "state_label", label: "Statut" },
        ], "civora-incidents.csv");
    }

    exportPayouts() {
        this.exportCsv(this.state.d.payouts || [], [
            { key: "date", label: "Date" }, { key: "channel", label: "Canal" },
            { key: "reference", label: "Référence" }, { key: "gross", label: "Brut" },
            { key: "commission", label: "Commission" }, { key: "net", label: "Net" },
            { key: "state_label", label: "Statut" },
        ], "civora-versements.csv");
    }

    copySnippet() {
        const cfg = this.state.d.booking_config || {};
        navigator.clipboard.writeText(cfg.snippet || "").then(
            () => this.notification.add("Snippet copié dans le presse-papier.", { type: "success" }),
            () => this.notification.add("Copie impossible.", { type: "warning" }),
        );
    }

    /* ============================== DRAWER ================================= */
    openDrawer(mode, id) {
        this.state.drawerMode = mode || "create";
        this.state.drawerRecordId = id || false;
        this.state.drawerOpen = true;
    }

    closeDrawer() { this.state.drawerOpen = false; }

    async onSaved() {
        this.state.drawerOpen = false;
        await this.load();
    }

    openDetail(id) {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.reservation_360",
            params: { reservation_id: id },
        });
    }

    timeSlotLabel(s) { return s === "matin" ? "Matin" : "Après-midi"; }
}

registry.category("actions").add("civora.reservations", CivoraReservationsScreen);
