import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";
import { EventDrawer } from "./event_drawer";

const TYPE_META = {
    visite: { label: "Visite", color: "#6366f1" },
    rdv: { label: "RDV", color: "#0ea5e9" },
    relance: { label: "Relance", color: "#efa831" },
    signature: { label: "Signature", color: "#e11d63" },
    call: { label: "Appel", color: "#14b8a6" },
    edl: { label: "État des lieux", color: "#8b5cf6" },
    checkin: { label: "Check-in", color: "#00ab68" },
    checkout: { label: "Check-out", color: "#f97316" },
    maintenance: { label: "Maintenance", color: "#64748b" },
    autre: { label: "Autre", color: "#94a3b8" },
};
const STATUS_LABEL = {
    planifie: "Planifié", a_confirmer: "À confirmer", confirme: "Confirmé",
    realise: "Réalisé", annule: "Annulé",
};
const MONTHS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"];
const DAYS_FR = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"];
const FIELDS = ["name", "event_type", "start", "stop", "allday", "status", "mode", "location",
    "agent_id", "partner_id", "property_id", "opportunity_id", "lead_id"];
const HOURS = Array.from({ length: 12 }, (_, i) => 8 + i); // 8h -> 19h
const HOUR_PX = 56;

function pad(n) { return String(n).padStart(2, "0"); }
function ymd(d) { return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()); }
function addDays(d, n) { const x = new Date(d); x.setDate(x.getDate() + n); return x; }
function startOfWeek(d) {
    const x = new Date(d);
    const day = (x.getDay() + 6) % 7; // Lundi = 0
    x.setDate(x.getDate() - day);
    x.setHours(0, 0, 0, 0);
    return x;
}

export class CivoraCalendarScreen extends Component {
    static template = "civora_calendar.Calendar";
    static components = { CivoraStatCard, EventDrawer };
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.typeMetaMap = TYPE_META;
        this.typeList = Object.keys(TYPE_META).map((k) => ({ id: k, ...TYPE_META[k] }));
        this.hours = HOURS;
        this.state = useState({
            loading: true,
            view: "mois",
            anchorKey: ymd(new Date()),
            events: [],
            typeFilters: [],
            drawer: { open: false, eventId: false, defaultDate: false, defaultStart: false, prefill: {} },
        });
        onWillStart(() => this.load());
    }

    get anchor() {
        return new Date(this.state.anchorKey + "T00:00:00");
    }
    set anchor(d) {
        this.state.anchorKey = ymd(d);
    }

    async load() {
        this.state.loading = true;
        this.allEvents = await this.orm.searchRead("civora.event", [], FIELDS, { limit: 1000, order: "start" });
        const users = await this.orm.searchRead("res.users", [["share", "=", false]], ["name"], { limit: 20, order: "name" });
        const palette = ["#6366f1", "#00ab68", "#e11d63", "#efa831", "#0ea5e9", "#8b5cf6", "#f97316", "#14b8a6", "#64748b", "#e62c2c"];
        this.agents = users.map((u, i) => ({ id: u.id, name: u.name, color: palette[i % palette.length] }));
        this.agentColorMap = {};
        for (const a of this.agents) this.agentColorMap[a.id] = a.color;
        this.state.loading = false;
    }

    // --- Filtres type --------------------------------------------------
    toggleType(id) {
        const arr = this.state.typeFilters;
        this.state.typeFilters = arr.includes(id) ? arr.filter((x) => x !== id) : [...arr, id];
    }
    typeActive(id) {
        return this.state.typeFilters.length === 0 || this.state.typeFilters.includes(id);
    }
    get visibleEvents() {
        const f = this.state.typeFilters;
        if (!f.length) return this.allEvents;
        return this.allEvents.filter((e) => f.includes(e.event_type));
    }
    eventsOn(dateKey) {
        return this.visibleEvents.filter((e) => (e.start || "").slice(0, 10) === dateKey);
    }

    // --- Range de la periode + KPIs -----------------------------------
    get periodEvents() {
        if (this.state.view === "jour") {
            return this.visibleEvents.filter((e) => (e.start || "").slice(0, 10) === this.state.anchorKey);
        }
        if (this.state.view === "mois") {
            const y = this.anchor.getFullYear(), m = this.anchor.getMonth();
            return this.visibleEvents.filter((e) => {
                const s = e.start || "";
                return s.slice(0, 4) == String(y) && s.slice(5, 7) == pad(m + 1);
            });
        }
        if (this.state.view === "semaine" || this.state.view === "planning" || this.state.view === "ressources") {
            const ws = startOfWeek(this.anchor);
            const keys = [];
            for (let i = 0; i < 7; i++) keys.push(ymd(addDays(ws, i)));
            return this.visibleEvents.filter((e) => keys.includes((e.start || "").slice(0, 10)));
        }
        return this.visibleEvents;
    }
    get stats() {
        const ev = this.periodEvents;
        return {
            total: ev.length,
            visites: ev.filter((e) => e.event_type === "visite").length,
            signatures: ev.filter((e) => e.event_type === "signature").length,
            relances: ev.filter((e) => e.event_type === "relance").length,
            aConfirmer: ev.filter((e) => e.status === "a_confirmer").length,
        };
    }

    // --- Grilles -------------------------------------------------------
    get monthWeeks() {
        const first = new Date(this.anchor.getFullYear(), this.anchor.getMonth(), 1);
        const gridStart = startOfWeek(first);
        const weeks = [];
        const todayKey = ymd(new Date());
        const curMonth = this.anchor.getMonth();
        for (let w = 0; w < 6; w++) {
            const days = [];
            for (let d = 0; d < 7; d++) {
                const date = addDays(gridStart, w * 7 + d);
                const key = ymd(date);
                days.push({
                    key,
                    num: date.getDate(),
                    inMonth: date.getMonth() === curMonth,
                    today: key === todayKey,
                    events: this.eventsOn(key),
                });
            }
            weeks.push(days);
        }
        return weeks;
    }
    get weekDays() {
        const ws = startOfWeek(this.anchor);
        const todayKey = ymd(new Date());
        const out = [];
        for (let i = 0; i < 7; i++) {
            const date = addDays(ws, i);
            const key = ymd(date);
            out.push({
                key, dow: DAYS_FR[i], num: date.getDate(),
                month: MONTHS_FR[date.getMonth()].slice(0, 3),
                today: key === todayKey,
                events: this.eventsOn(key).slice().sort((a, b) => (a.start || "").localeCompare(b.start || "")),
            });
        }
        return out;
    }
    get listEvents() {
        return this.periodEvents.slice().sort((a, b) => (a.start || "").localeCompare(b.start || ""));
    }
    get dowHeaders() {
        return DAYS_FR;
    }

    // --- Grille horaire (Jour / Semaine) ------------------------------
    parseDT(s) {
        if (!s) return null;
        const d = new Date(s.replace(" ", "T").replace(/-/g, "/").replace("T", " "));
        return isNaN(d) ? null : d;
    }
    eventHour(e) {
        const s = e.start || "";
        return parseInt(s.slice(11, 13) || "0", 10) + parseInt(s.slice(14, 16) || "0", 10) / 60;
    }
    eventDurationH(e) {
        if (!e.stop) return 1;
        const st = e.start || "", sp = e.stop || "";
        const h1 = parseInt(st.slice(11, 13) || "0", 10) + parseInt(st.slice(14, 16) || "0", 10) / 60;
        const h2 = parseInt(sp.slice(11, 13) || "0", 10) + parseInt(sp.slice(14, 16) || "0", 10) / 60;
        const d = h2 - h1;
        return d > 0 ? d : 1;
    }
    eventTop(e) {
        return Math.max(0, (this.eventHour(e) - 8) * HOUR_PX);
    }
    eventHeight(e) {
        return Math.max(22, this.eventDurationH(e) * HOUR_PX - 4);
    }
    gridEventsOn(dateKey) {
        return this.visibleEvents.filter((e) => {
            if ((e.start || "").slice(0, 10) !== dateKey || e.allday) return false;
            const h = this.eventHour(e);
            return h >= 8 && h <= 20;
        });
    }
    alldayOn(dateKey) {
        return this.visibleEvents.filter((e) => (e.start || "").slice(0, 10) === dateKey && e.allday);
    }
    get gridHeight() {
        return HOURS.length * HOUR_PX;
    }
    hourLabel(h) {
        return pad(h) + ":00";
    }
    get dayDate() {
        const d = this.anchor;
        return DAYS_FR[(d.getDay() + 6) % 7] + " " + d.getDate() + " " + MONTHS_FR[d.getMonth()];
    }

    // --- Planning equipe (agents x jours) / Ressources (biens x jours) --
    agentIdOf(e) {
        return e.agent_id ? e.agent_id[0] : 0;
    }
    get planningRows() {
        const wk = this.weekDays;
        return this.agents.map((a) => {
            const days = wk.map((d) => ({ key: d.key, events: d.events.filter((e) => this.agentIdOf(e) === a.id) }));
            const load = days.reduce((n, d) => n + d.events.length, 0);
            return { agent: a, days, load };
        });
    }
    get ressourceRows() {
        const wk = this.weekDays;
        const map = {};
        for (const d of wk) {
            for (const e of d.events) {
                if (e.property_id) map[e.property_id[0]] = e.property_id[1];
            }
        }
        return Object.keys(map).map((id) => {
            const pid = Number(id);
            return {
                id: pid,
                name: map[id],
                days: wk.map((d) => ({ key: d.key, events: d.events.filter((e) => e.property_id && e.property_id[0] === pid) })),
            };
        });
    }
    planCreate(dayKey, agentId) {
        this.state.drawer = { open: true, eventId: false, defaultDate: false, defaultStart: dayKey + "T09:00", prefill: { agent_id: agentId } };
    }
    resCreate(dayKey, propId) {
        this.state.drawer = { open: true, eventId: false, defaultDate: dayKey, defaultStart: false, prefill: { property_id: propId } };
    }

    // --- Detection de conflits ----------------------------------------
    get conflictIds() {
        const set = new Set();
        const byAgent = {};
        for (const e of this.periodEvents) {
            if (e.status === "annule") continue;
            const key = e.agent_id ? e.agent_id[0] : 0;
            (byAgent[key] = byAgent[key] || []).push(e);
        }
        const endOf = (e) => {
            if (e.stop) return e.stop;
            // start + 1h par defaut
            const s = e.start || "";
            const h = parseInt(s.slice(11, 13) || "0", 10) + 1;
            return s.slice(0, 11) + pad(h) + s.slice(13);
        };
        for (const arr of Object.values(byAgent)) {
            const sorted = arr.slice().sort((x, y) => (x.start || "").localeCompare(y.start || ""));
            for (let i = 0; i < sorted.length - 1; i++) {
                const a = sorted[i], aEnd = endOf(a);
                for (let j = i + 1; j < sorted.length; j++) {
                    const b = sorted[j];
                    if ((b.start || "") >= aEnd) break;
                    set.add(a.id); set.add(b.id);
                    this._firstConflict = this._firstConflict || [a, b];
                }
            }
        }
        return set;
    }
    get conflicts() {
        this._firstConflict = null;
        const ids = this.conflictIds;
        return { count: ids.size, pair: this._firstConflict };
    }
    isConflict(e) {
        return this.conflictIds.has(e.id);
    }
    get insight() {
        const c = this.conflicts;
        if (c.count && c.pair) {
            return {
                tone: "warn",
                title: (c.pair.length ? "Conflit d'agenda détecté" : "Conflit détecté"),
                body: "Un agent a des créneaux qui se chevauchent : « " + c.pair[0].name + " » ↔ « " + c.pair[1].name + " ». Ajustez les horaires pour éviter le double-booking.",
            };
        }
        const visites = this.periodEvents.filter((e) => e.event_type === "visite").length;
        if (visites >= 2) {
            return {
                tone: "tip",
                title: "Optimisation de tournée",
                body: "Regrouper les visites d'un même quartier sur un créneau permettrait d'économiser du temps de trajet par agent.",
            };
        }
        return null;
    }

    // --- Navigation ----------------------------------------------------
    setView(v) {
        this.state.view = v;
    }
    today() {
        this.anchor = new Date();
    }
    prev() {
        if (this.state.view === "mois") {
            const d = this.anchor; this.anchor = new Date(d.getFullYear(), d.getMonth() - 1, 1);
        } else if (this.state.view === "jour") {
            this.anchor = addDays(this.anchor, -1);
        } else {
            this.anchor = addDays(this.anchor, -7);
        }
    }
    next() {
        if (this.state.view === "mois") {
            const d = this.anchor; this.anchor = new Date(d.getFullYear(), d.getMonth() + 1, 1);
        } else if (this.state.view === "jour") {
            this.anchor = addDays(this.anchor, 1);
        } else {
            this.anchor = addDays(this.anchor, 7);
        }
    }
    get periodLabel() {
        const d = this.anchor;
        if (this.state.view === "mois") return MONTHS_FR[d.getMonth()] + " " + d.getFullYear();
        if (this.state.view === "jour") return DAYS_FR[(d.getDay() + 6) % 7] + " " + pad(d.getDate()) + " " + MONTHS_FR[d.getMonth()] + " " + d.getFullYear();
        if (this.state.view === "semaine" || this.state.view === "planning" || this.state.view === "ressources") {
            const ws = startOfWeek(d), we = addDays(ws, 6);
            return pad(ws.getDate()) + " → " + pad(we.getDate()) + " " + MONTHS_FR[we.getMonth()] + " " + we.getFullYear();
        }
        return "Tous les événements";
    }

    // --- Actions -------------------------------------------------------
    openCreate(dateKey) {
        this.state.drawer = { open: true, eventId: false, defaultDate: dateKey || this.state.anchorKey, defaultStart: false, prefill: {} };
    }
    openCreateAt(dateKey, hour) {
        this.state.drawer = { open: true, eventId: false, defaultDate: false, defaultStart: dateKey + "T" + pad(hour) + ":00", prefill: {} };
    }
    openEvent(e) {
        this.state.drawer = { open: true, eventId: e.id, defaultDate: false, defaultStart: false, prefill: {} };
    }
    async closeDrawer(saved) {
        this.state.drawer = { open: false, eventId: false, defaultDate: false, defaultStart: false, prefill: {} };
        if (saved) await this.load();
    }

    // --- Helpers -------------------------------------------------------
    typeMeta(e) {
        return TYPE_META[e.event_type] || TYPE_META.autre;
    }
    statusLabel(e) {
        return STATUS_LABEL[e.status] || "";
    }
    timeLabel(e) {
        if (e.allday) return "Journée";
        return (e.start || "").slice(11, 16);
    }
    agentLabel(e) {
        return e.agent_id ? e.agent_id[1] : "";
    }
    subLabel(e) {
        return [e.partner_id && e.partner_id[1], e.property_id && e.property_id[1]].filter(Boolean).join(" · ");
    }
}

registry.category("actions").add("civora.calendar", CivoraCalendarScreen);
