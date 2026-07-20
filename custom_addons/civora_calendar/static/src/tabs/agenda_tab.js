import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { CivoraBadge } from "@civora_core/components/civora_kit";
import { EventDrawer } from "../calendar/event_drawer";

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
const STATUS_META = {
    planifie: { label: "Planifié", variant: "info" },
    a_confirmer: { label: "À confirmer", variant: "warning" },
    confirme: { label: "Confirmé", variant: "success" },
    realise: { label: "Réalisé", variant: "neutral" },
    annule: { label: "Annulé", variant: "danger" },
};

/** Onglet "Agenda" injecte dans les fiches contact / bien / opportunite. */
export class AgendaTab extends Component {
    static template = "civora_calendar.AgendaTab";
    static components = { CivoraBadge, EventDrawer };
    static props = {
        contactId: { type: [Number, Boolean], optional: true },
        propertyId: { type: [Number, Boolean], optional: true },
        opportunityId: { type: [Number, Boolean], optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ loading: true, events: [], drawer: { open: false, eventId: false } });
        onWillStart(() => this.load());
    }

    get link() {
        if (this.props.contactId) return { field: "partner_id", id: this.props.contactId, prefill: { partner_id: this.props.contactId } };
        if (this.props.propertyId) return { field: "property_id", id: this.props.propertyId, prefill: { property_id: this.props.propertyId } };
        if (this.props.opportunityId) return { field: "opportunity_id", id: this.props.opportunityId, prefill: { opportunity_id: this.props.opportunityId } };
        return null;
    }

    async load() {
        this.state.loading = true;
        const l = this.link;
        if (!l) { this.state.events = []; this.state.loading = false; return; }
        this.state.events = await this.orm.searchRead(
            "civora.event", [[l.field, "=", l.id]],
            ["name", "event_type", "start", "status", "allday", "agent_id"],
            { order: "start desc" }
        );
        this.state.loading = false;
    }

    plan() {
        this.state.drawer = { open: true, eventId: false };
    }
    openEvent(e) {
        this.state.drawer = { open: true, eventId: e.id };
    }
    async closeDrawer(saved) {
        this.state.drawer = { open: false, eventId: false };
        if (saved) await this.load();
    }
    get prefill() {
        const l = this.link;
        return l ? l.prefill : {};
    }
    todayKey() {
        const d = new Date();
        const p = (n) => String(n).padStart(2, "0");
        return d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate());
    }

    typeMeta(e) { return TYPE_META[e.event_type] || TYPE_META.autre; }
    statusMeta(e) { return STATUS_META[e.status] || { label: "", variant: "neutral" }; }
    dateLabel(e) {
        const s = e.start || "";
        if (!s) return "";
        const d = s.slice(8, 10) + "/" + s.slice(5, 7) + "/" + s.slice(0, 4);
        return e.allday ? d : d + " · " + s.slice(11, 16);
    }
    agentLabel(e) { return e.agent_id ? e.agent_id[1] : ""; }
}

const entry = { id: "agenda", label: "Agenda", Component: AgendaTab, sequence: 30 };
registry.category("civora_contact_360_tab").add("agenda", entry);
registry.category("civora_property_360_tab").add("agenda", entry);
registry.category("civora_opportunity_360_tab").add("agenda", entry);
