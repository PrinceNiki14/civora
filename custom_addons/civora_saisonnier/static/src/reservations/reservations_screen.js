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
        });
        onWillStart(() => this.load());
    }

    async load() {
        const [kpis, reservations, cleaningTasks] = await Promise.all([
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
        ]);
        this.state.kpis = kpis;
        this.state.reservations = reservations;
        this.state.cleaningTasks = cleaningTasks;
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

    setFilter(f) { this.state.filter = f; }
    onSearch(ev) { this.state.search = ev.target.value; }

    stateLabel(s) { return STATE_LABELS[s] || s; }
    stateClass(s) {
        const m = { draft: "muted", confirmed: "info", checkin: "accent", checkout: "success", cancelled: "danger" };
        return m[s] || "";
    }
    sourceLabel(s) { return SOURCE_LABELS[s] || s; }
    fmtMoney(v) { return fmtMoney(v); }

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
        return s === "matin" ? "Matin" : "Après-midi";
    }
}

registry.category("actions").add("civora.reservations", CivoraReservationsScreen);
