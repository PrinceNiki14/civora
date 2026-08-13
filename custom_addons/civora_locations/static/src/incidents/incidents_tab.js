import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CivoraBadge } from "@civora_core/components/civora_kit";
import { ReminderDrawer } from "./reminder_drawer";

const SEVERITY_META = {
    soft:     { label: "Léger",    variant: "warning", color: "#f59e0b" },
    moderate: { label: "Modéré",   variant: "warning", color: "#ea580c" },
    firm:     { label: "Ferme",    variant: "danger",  color: "#dc2626" },
    legal:    { label: "Critique", variant: "danger",  color: "#991b1b" },
};

const CHANNEL_ICONS = {
    email:    "fa-envelope",
    whatsapp: "fa-whatsapp",
    sms:      "fa-mobile",
    phone:    "fa-phone",
    letter:   "fa-file-text-o",
};

const LEVEL_META = {
    low:    { label: "Faible", color: "#00ab68", bg: "rgba(0,171,104,.10)" },
    medium: { label: "Modéré", color: "#ea580c", bg: "rgba(234,88,12,.10)" },
    high:   { label: "Élevé",  color: "#dc2626", bg: "rgba(220,38,38,.10)" },
};

/**
 * Onglet Incidents & Relances du Bail 360.
 * - Score de risque impayé (heuristique transparente)
 * - Tableau des échéances en retard avec sévérité graduée
 * - Historique des relances envoyées
 * - Bouton "Préparer relance" ouvre ReminderDrawer
 */
export class IncidentsTab extends Component {
    static template = "civora_locations.IncidentsTab";
    static components = { CivoraBadge, ReminderDrawer };
    static props = {
        leaseId: { type: [Number, Boolean] },
        currency: { type: String, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            loading: true,
            error: "",
            incidents: [],
            reminders: [],
            risk: { score: 0, level: "low", level_label: "Faible", breakdown: {} },
            drawer: { open: false, preselectedIds: [], defaultContext: null },
        });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        this.state.error = "";
        try {
            const [incidents, reminders, risk] = await Promise.all([
                this.orm.call("civora.lease", "get_incidents_data", [this.props.leaseId]),
                this.orm.call("civora.lease", "get_reminders_history", [this.props.leaseId]),
                this.orm.call("civora.lease", "get_risk_score", [this.props.leaseId]),
            ]);
            this.state.incidents = incidents || [];
            this.state.reminders = reminders || [];
            this.state.risk = risk || { score: 0, level: "low", level_label: "Faible", breakdown: {} };
        } catch (e) {
            this.state.error = "Impossible de charger les incidents.";
        }
        this.state.loading = false;
    }

    // ---- Helpers d'affichage ----
    severityMeta(sev) {
        return SEVERITY_META[sev] || { label: "—", variant: "neutral", color: "#94a3b8" };
    }
    levelMeta() {
        return LEVEL_META[this.state.risk.level] || LEVEL_META.low;
    }
    channelIcon(ch) {
        return "fa " + (CHANNEL_ICONS[ch] || "fa-bell");
    }
    fmtMoney(n) {
        n = Number(n || 0);
        if (n >= 1e6) return (n / 1e6).toFixed(n % 1e6 ? 1 : 0).replace(".", ",") + " M FCFA";
        if (n >= 1e3) return Math.round(n / 1e3) + " k FCFA";
        return n + " FCFA";
    }
    fmtDate(d) {
        if (!d) return "—";
        const [y, m, day] = String(d).split("-");
        return day && m && y ? `${day}/${m}/${y}` : d;
    }
    get hasIncidents() {
        return this.state.incidents.length > 0;
    }
    get hasReminders() {
        return this.state.reminders.length > 0;
    }
    get totalOverdue() {
        return this.state.incidents.reduce((s, i) => s + (i.amount_remaining || 0), 0);
    }
    get scoreGradientStyle() {
        const meta = this.levelMeta();
        return `background: ${meta.bg}; color: ${meta.color}; border-color: ${meta.color};`;
    }

    // ---- Actions ----
    openReminderDrawer(incident) {
        // incident peut être : null (tous les retards) ou un objet incident précis
        let preselectedIds, defaultContext;
        if (incident) {
            // Cliqué sur une ligne spécifique → prendre sévérité, période, jours
            preselectedIds = [incident.id];
            defaultContext = {
                severity: incident.severity,
                periods: [{
                    period_label: incident.period_label,
                    days_overdue: incident.days_overdue,
                    amount_remaining: incident.amount_remaining,
                }],
            };
        } else {
            // Cliqué sur "Préparer une relance" globale → toutes les échéances
            preselectedIds = this.state.incidents.map((i) => i.id);
            // Sévérité globale = la plus élevée parmi les retards
            const severityRank = { soft: 1, moderate: 2, firm: 3, legal: 4 };
            let maxSeverity = "soft";
            for (const i of this.state.incidents) {
                if ((severityRank[i.severity] || 0) > (severityRank[maxSeverity] || 0)) {
                    maxSeverity = i.severity;
                }
            }
            defaultContext = {
                severity: maxSeverity,
                periods: this.state.incidents.map((i) => ({
                    period_label: i.period_label,
                    days_overdue: i.days_overdue,
                    amount_remaining: i.amount_remaining,
                })),
            };
        }
        this.state.drawer = { open: true, preselectedIds, defaultContext };
    }
    closeReminderDrawer() {
        this.state.drawer = { open: false, preselectedIds: [], defaultContext: null };
    }
    async onReminderSaved() {
        this.closeReminderDrawer();
        await this.load();
    }
}
