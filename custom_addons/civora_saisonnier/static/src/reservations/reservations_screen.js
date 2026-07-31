/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";
import { ReservationDrawer } from "./reservation_drawer";

function fmtMoney(v) {
    if (!v && v !== 0) return "0";
    return Number(v).toLocaleString("fr-FR");
}

const STATE_LABELS = {
    draft: "Brouillon",
    confirmed: "Confirmee",
    checkin: "En sejour",
    checkout: "Terminee",
    cancelled: "Annulee",
};

const SOURCE_LABELS = {
    direct: "Direct",
    airbnb: "Airbnb",
    booking: "Booking.com",
    whatsapp: "WhatsApp",
    referral: "Reference",
    other: "Autre",
};

const MONTHS_FR = [
    "Janvier", "Fevrier", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Aout", "Septembre", "Octobre", "Novembre", "Decembre"
];

class CivoraReservationsScreen extends Component {
    static template = "civora_saisonnier.ReservationsScreen";
    static components = { CivoraStatCard, ReservationDrawer };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            reservations: [],
            kpis: {},
            filter: "all",
            search: "",
            drawerOpen: false,
            drawerMode: "create",
            drawerRecordId: null,
            cleaningTasks: [],
            checkinsToday: [],
            checkoutsAndCleaning: [],
            recentReviews: [],
            activeTab: "reservations",
        });
        onWillStart(() => this.load());
    }

    async load() {
        const [kpis, reservations, cleaningTasks, checkinsToday, checkoutsAndCleaning, recentReviews] = await Promise.all([
            this.orm.call("civora.reservation", "get_seasonal_kpis", []),
            this.orm.searchRead("civora.reservation", [], [
                "name", "property_id", "guest_id", "agent_id",
                "checkin_date", "checkout_date", "num_nights",
                "tariff_night", "total_amount", "state", "source",
                "deposit_amount", "deposit_status", "num_guests",
            ], { order: "checkin_date desc", limit: 200 }),
            this.orm.searchRead("civora.cleaning.task", [
                ["state", "in", ["a_planifier", "planifie"]],
            ], [
                "property_id", "date", "time_slot", "state",
                "assigned_to", "reservation_id",
            ], { order: "date asc", limit: 50 }),
            this.orm.call("civora.reservation", "get_checkins_today", []),
            this.orm.call("civora.reservation", "get_checkouts_and_cleaning", []),
            this.orm.call("civora.reservation", "get_recent_reviews", []),
        ]);
        this.state.kpis = kpis;
        this.state.reservations = reservations;
        this.state.cleaningTasks = cleaningTasks;
        this.state.checkinsToday = checkinsToday;
        this.state.checkoutsAndCleaning = checkoutsAndCleaning;
        this.state.recentReviews = recentReviews;
    }

    get dynamicSubtitle() {
        const k = this.state.kpis;
        const now = new Date();
        const month = MONTHS_FR[now.getMonth()];
        const year = now.getFullYear();
        const props = k.property_count || 0;
        const occ = k.occupation_rate || 0;
        return `${month} ${year} · ${props} biens · ${occ}% d'occupation`;
    }

    get filteredReservations() {
        let list = this.state.reservations;
        const f = this.state.filter;
        const today = new Date().toISOString().slice(0, 10);
        if (f === "confirmed") list = list.filter(r => r.state === "confirmed");
        else if (f === "checkin_today") list = list.filter(r => r.checkin_date === today && r.state === "confirmed");
        else if (f === "checkout_today") list = list.filter(r => r.checkout_date === today && r.state === "checkin");
        else if (f === "in_stay") list = list.filter(r => r.state === "checkin");
        else if (f === "upcoming") list = list.filter(r => r.checkin_date > today && r.state === "confirmed");
        if (this.state.search) {
            const q = this.state.search.toLowerCase();
            list = list.filter(r =>
                (r.guest_id && r.guest_id[1] || "").toLowerCase().includes(q) ||
                (r.property_id && r.property_id[1] || "").toLowerCase().includes(q) ||
                (r.name || "").toLowerCase().includes(q)
            );
        }
        return list;
    }

    get tabs() {
        return [
            { key: "reservations", label: "Reservations", count: this.state.reservations.length },
            { key: "checkins", label: "Check-in aujourd'hui", count: this.state.checkinsToday.length },
            { key: "cleaning", label: "Menage & maintenance", count: this.state.cleaningTasks.length },
            { key: "reviews", label: "Avis recents", count: this.state.recentReviews.length },
        ];
    }

    setTab(tab) { this.state.activeTab = tab; }
    setFilter(f) { this.state.filter = f; }
    onSearch(ev) { this.state.search = ev.target.value; }

    stateLabel(s) { return STATE_LABELS[s] || s; }
    stateClass(s) {
        const m = { draft: "muted", confirmed: "info", checkin: "accent", checkout: "success", cancelled: "danger" };
        return m[s] || "";
    }
    sourceLabel(s) { return SOURCE_LABELS[s] || s; }
    fmtMoney(v) { return fmtMoney(v); }

    cleaningStateLabel(s) {
        if (s === "a_planifier") return "En attente";
        if (s === "planifie") return "Planifie";
        if (s === "done") return "Termine";
        return s;
    }

    ratingStars(rating) {
        return Math.round(rating || 0);
    }

    openDrawer(mode, id) {
        this.state.drawerMode = mode || "create";
        this.state.drawerRecordId = id || null;
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

    timeSlotLabel(s) {
        return s === "matin" ? "Matin" : "Apres-midi";
    }
}

registry.category("actions").add("civora.reservations", CivoraReservationsScreen);
