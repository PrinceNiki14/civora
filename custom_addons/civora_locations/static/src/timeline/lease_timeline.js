/** @odoo-module **/
import { Component, onWillStart, useState, markup } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const CATEGORY_LABELS = {
    all:      "Tous les événements",
    contract: "Contrat",
    payment:  "Paiements",
    refund:   "Caution",
    other:    "Autres",
};

/**
 * Timeline chronologique unifiée du bail.
 *
 * Affiche tous les événements du bail, contrat lié, paiements et restitution,
 * regroupés par jour et triés du plus récent au plus ancien.
 *
 * Props :
 *   - leaseId (Number) : ID du bail
 */
export class LeaseTimeline extends Component {
    static template = "civora_locations.LeaseTimeline";
    static props = {
        leaseId: Number,
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            loading: true,
            events: [],
            filter: "all",
        });

        onWillStart(async () => {
            await this._load();
        });
    }

    async _load() {
        this.state.loading = true;
        try {
            const events = await this.orm.call(
                "civora.lease",
                "get_timeline",
                [[this.props.leaseId], this.state.filter]
            );
            this.state.events = events || [];
        } catch (e) {
            this.state.events = [];
        }
        this.state.loading = false;
    }

    async setFilter(filterKey) {
        this.state.filter = filterKey;
        await this._load();
    }

    // ── Regroupement par jour ─────────────────────────────────────────
    get groupedEvents() {
        const groups = {};
        const todayIso = new Date().toISOString().slice(0, 10);
        const yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);
        const yesterdayIso = yesterday.toISOString().slice(0, 10);

        for (const ev of this.state.events) {
            if (!ev.date) continue;
            const dayIso = ev.date.slice(0, 10);
            if (!groups[dayIso]) {
                let label;
                if (dayIso === todayIso) label = "Aujourd'hui";
                else if (dayIso === yesterdayIso) label = "Hier";
                else label = this._fmtDayLabel(dayIso);
                groups[dayIso] = { dayIso, label, items: [] };
            }
            groups[dayIso].items.push(ev);
        }
        // Retourner les groupes triés par date décroissante
        return Object.values(groups).sort(
            (a, b) => (b.dayIso > a.dayIso ? 1 : -1)
        );
    }

    _fmtDayLabel(iso) {
        const MOIS = ["janvier", "février", "mars", "avril", "mai", "juin",
                      "juillet", "août", "septembre", "octobre", "novembre", "décembre"];
        const d = new Date(iso + "T00:00:00");
        return `${d.getDate()} ${MOIS[d.getMonth()]} ${d.getFullYear()}`;
    }

    fmtTime(iso) {
        if (!iso) return "";
        const d = new Date(iso);
        return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
    }

    renderBody(html) {
        // Marque le HTML comme sûr (le contenu vient du chatter Odoo, déjà nettoyé)
        return markup(html || "");
    }

    get filterOptions() {
        return [
            { key: "all",      label: CATEGORY_LABELS.all      },
            { key: "contract", label: CATEGORY_LABELS.contract },
            { key: "payment",  label: CATEGORY_LABELS.payment  },
            { key: "refund",   label: CATEGORY_LABELS.refund   },
            { key: "other",    label: CATEGORY_LABELS.other    },
        ];
    }

    get isEmpty() {
        return !this.state.loading && this.state.events.length === 0;
    }
}
