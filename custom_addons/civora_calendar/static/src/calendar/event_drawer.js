import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CivoraDrawer } from "@civora_core/components/civora_drawer";

const TYPES = [
    { value: "visite", label: "Visite" },
    { value: "rdv", label: "Rendez-vous" },
    { value: "relance", label: "Relance" },
    { value: "signature", label: "Signature" },
    { value: "call", label: "Appel" },
    { value: "edl", label: "État des lieux" },
    { value: "checkin", label: "Check-in" },
    { value: "checkout", label: "Check-out" },
    { value: "maintenance", label: "Maintenance" },
    { value: "autre", label: "Autre" },
];
const STATUSES = [
    { value: "planifie", label: "Planifié" },
    { value: "a_confirmer", label: "À confirmer" },
    { value: "confirme", label: "Confirmé" },
    { value: "realise", label: "Réalisé" },
    { value: "annule", label: "Annulé" },
];
const MODES = [
    { value: "", label: "—" },
    { value: "physique", label: "Sur place" },
    { value: "visio", label: "Visio" },
    { value: "tel", label: "Téléphone" },
];

function toLocalInput(dt) {
    if (!dt) return "";
    return dt.slice(0, 16).replace(" ", "T");
}
function toOdoo(v) {
    if (!v) return false;
    return v.replace("T", " ") + ":00";
}

export class EventDrawer extends Component {
    static template = "civora_calendar.EventDrawer";
    static components = { CivoraDrawer };
    static props = {
        eventId: { type: [Number, Boolean], optional: true },
        defaultDate: { type: [String, Boolean], optional: true },
        defaultStart: { type: [String, Boolean], optional: true },
        prefill: { type: Object, optional: true },
        onClose: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.types = TYPES;
        this.statuses = STATUSES;
        this.modes = MODES;
        this.partners = [];
        this.properties = [];
        this.opportunities = [];
        this.leads = [];
        this.users = [];
        this.state = useState({ loading: true, saving: false, error: "", form: this.emptyForm() });
        onWillStart(() => this.load());
    }

    emptyForm() {
        const day = this.props.defaultDate || "";
        const pf = this.props.prefill || {};
        let start = day ? day + "T09:00" : "";
        let stop = day ? day + "T10:00" : "";
        if (this.props.defaultStart) {
            start = this.props.defaultStart.slice(0, 16);
            const d = new Date(start.replace("T", " ").replace(/-/g, "/"));
            if (!isNaN(d)) {
                d.setHours(d.getHours() + 1);
                const p = (n) => String(n).padStart(2, "0");
                stop = d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate()) + "T" + p(d.getHours()) + ":" + p(d.getMinutes());
            }
        }
        return {
            name: "", event_type: "rdv", status: "planifie", mode: "",
            start, stop, allday: false, location: "",
            agent_id: pf.agent_id || false,
            partner_id: pf.partner_id || false,
            property_id: pf.property_id || false,
            opportunity_id: pf.opportunity_id || false,
            lead_id: pf.lead_id || false,
            notes: "",
        };
    }

    async load() {
        this.state.loading = true;
        this.partners = await this.orm.searchRead("res.partner", [["civora_is_contact", "=", true]], ["name"], { limit: 500, order: "name" });
        this.properties = await this.orm.searchRead("civora.property", [], ["name"], { limit: 500, order: "name" });
        this.opportunities = await this.orm.searchRead("civora.opportunity", [], ["name"], { limit: 500, order: "id desc" });
        this.leads = await this.orm.searchRead("civora.lead", [], ["name"], { limit: 500, order: "id desc" });
        this.users = await this.orm.searchRead("res.users", [["share", "=", false]], ["name"], { order: "name" });

        if (this.props.eventId) {
            const m2o = (v) => (v ? v[0] : false);
            const [rec] = await this.orm.read("civora.event", [this.props.eventId], [
                "name", "event_type", "status", "mode", "start", "stop", "allday", "location",
                "agent_id", "partner_id", "property_id", "opportunity_id", "lead_id", "notes",
            ]);
            if (rec) {
                this.state.form = {
                    name: rec.name || "",
                    event_type: rec.event_type || "rdv",
                    status: rec.status || "planifie",
                    mode: rec.mode || "",
                    start: toLocalInput(rec.start),
                    stop: toLocalInput(rec.stop),
                    allday: !!rec.allday,
                    location: rec.location || "",
                    agent_id: m2o(rec.agent_id),
                    partner_id: m2o(rec.partner_id),
                    property_id: m2o(rec.property_id),
                    opportunity_id: m2o(rec.opportunity_id),
                    lead_id: m2o(rec.lead_id),
                    notes: rec.notes || "",
                };
            }
        }
        this.state.loading = false;
    }

    get drawerTitle() {
        return this.props.eventId ? "Modifier l'événement" : "Nouvel événement";
    }
    setField(field, ev) { this.state.form[field] = ev.target.value; }
    setCheckbox(field, ev) { this.state.form[field] = ev.target.checked; }
    setM2O(field, ev) { this.state.form[field] = ev.target.value ? parseInt(ev.target.value) : false; }

    buildVals() {
        const f = this.state.form;
        return {
            name: f.name || "Événement",
            event_type: f.event_type,
            status: f.status,
            mode: f.mode || false,
            start: toOdoo(f.start),
            stop: toOdoo(f.stop),
            allday: !!f.allday,
            location: f.location || false,
            agent_id: f.agent_id || false,
            partner_id: f.partner_id || false,
            property_id: f.property_id || false,
            opportunity_id: f.opportunity_id || false,
            lead_id: f.lead_id || false,
            notes: f.notes || false,
        };
    }

    async save() {
        if (!this.state.form.name.trim()) { this.state.error = "Le titre est obligatoire."; return; }
        if (!this.state.form.start) { this.state.error = "La date de début est obligatoire."; return; }
        this.state.saving = true;
        this.state.error = "";
        try {
            const vals = this.buildVals();
            if (this.props.eventId) {
                await this.orm.write("civora.event", [this.props.eventId], vals);
            } else {
                await this.orm.create("civora.event", [vals]);
            }
            this.props.onClose(true);
        } catch (e) {
            this.state.error = "Enregistrement impossible.";
            this.state.saving = false;
        }
    }
    async remove() {
        if (!this.props.eventId) return;
        this.state.saving = true;
        try {
            await this.orm.unlink("civora.event", [this.props.eventId]);
            this.props.onClose(true);
        } catch (e) {
            this.state.error = "Suppression impossible.";
            this.state.saving = false;
        }
    }
}
