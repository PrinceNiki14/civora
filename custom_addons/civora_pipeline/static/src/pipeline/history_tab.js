import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Onglet Historique : timeline verticale des evenements et messages du chatter.
 * Fusionne mail.message (notes, emails, evenements) + tracking_value_ids
 * (changements de champs traces) pour offrir un fil unique style CIVORA.
 */
export class HistoryTab extends Component {
    static template = "civora_pipeline.HistoryTab";
    static props = { opportunityId: { type: [Number, Boolean] } };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            loading: true,
            events: [],       // liste normalisee triee anti-chronologique
            newNote: "",
            posting: false,
        });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        if (!this.props.opportunityId) {
            this.state.events = [];
            this.state.loading = false;
            return;
        }
        const messages = await this.orm.searchRead(
            "mail.message",
            [["model", "=", "civora.opportunity"], ["res_id", "=", this.props.opportunityId]],
            ["date", "body", "subject", "author_id", "message_type", "subtype_id", "tracking_value_ids"],
            { order: "date desc", limit: 200 },
        );

        // Charge en batch tous les tracking_value_ids referencees.
        const allTrackIds = messages.reduce((acc, m) => acc.concat(m.tracking_value_ids || []), []);
        const trackMap = {};
        if (allTrackIds.length) {
            const uniq = [...new Set(allTrackIds)];
            const rows = await this.orm.read("mail.tracking.value", uniq, [
                "field_id", "old_value_char", "new_value_char",
                "old_value_integer", "new_value_integer",
                "old_value_float", "new_value_float",
                "old_value_datetime", "new_value_datetime",
                "old_value_text", "new_value_text",
            ]);
            for (const r of rows) trackMap[r.id] = r;
        }

        // Normalisation en un tableau d'evenements.
        const events = [];
        for (const m of messages) {
            const author = m.author_id ? m.author_id[1] : "Système";
            const when = this.formatDate(m.date);
            const trackings = (m.tracking_value_ids || [])
                .map((tid) => trackMap[tid])
                .filter(Boolean);

            for (const tv of trackings) {
                const fieldLabel = tv.field_id ? tv.field_id[1] : "Champ";
                const oldV = this.trackValue(tv, "old");
                const newV = this.trackValue(tv, "new");
                events.push({
                    kind: "tracking",
                    icon: this.iconForField(fieldLabel),
                    tone: this.toneForField(fieldLabel),
                    title: `${fieldLabel} : ${oldV || "—"} → ${newV || "—"}`,
                    who: author, when, note: "",
                });
            }

            // Note / message avec corps texte.
            const cleanBody = this.stripHtml(m.body || "");
            if (cleanBody) {
                events.push({
                    kind: "message",
                    icon: m.message_type === "email" ? "fa-envelope" : "fa-comment-o",
                    tone: m.message_type === "email" ? "info" : "muted",
                    title: m.subject || (m.message_type === "email" ? "Email" : "Note interne"),
                    who: author, when, note: cleanBody,
                });
            } else if (!trackings.length) {
                // Message vide sans tracking : evenement systeme generique.
                events.push({
                    kind: "system",
                    icon: "fa-info-circle",
                    tone: "muted",
                    title: m.subject || "Événement",
                    who: author, when, note: "",
                });
            }
        }
        this.state.events = events;
        this.state.loading = false;
    }

    trackValue(tv, side) {
        const key = side === "old" ? "old_value_" : "new_value_";
        return tv[key + "char"] || tv[key + "text"] || tv[key + "datetime"] ||
               (tv[key + "float"] != null && tv[key + "float"] !== 0 ? String(tv[key + "float"]) : "") ||
               (tv[key + "integer"] != null && tv[key + "integer"] !== 0 ? String(tv[key + "integer"]) : "") ||
               "";
    }

    stripHtml(html) {
        if (!html) return "";
        const el = document.createElement("div");
        el.innerHTML = html;
        return (el.textContent || "").trim();
    }

    formatDate(d) {
        if (!d) return "";
        const dt = new Date(d.replace(" ", "T") + "Z");
        const now = Date.now();
        const diff = now - dt.getTime();
        const min = 60 * 1000, hour = 60 * min, day = 24 * hour;
        if (diff < min) return "à l'instant";
        if (diff < hour) return `il y a ${Math.floor(diff / min)} min`;
        if (diff < day) return `il y a ${Math.floor(diff / hour)} h`;
        if (diff < 7 * day) return `il y a ${Math.floor(diff / day)} j`;
        return dt.toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric" });
    }

    iconForField(label) {
        const l = (label || "").toLowerCase();
        if (l.includes("étape") || l.includes("etape") || l.includes("stage")) return "fa-arrow-circle-right";
        if (l.includes("montant") || l.includes("amount")) return "fa-money";
        if (l.includes("agent") || l.includes("user")) return "fa-user";
        if (l.includes("score")) return "fa-star";
        if (l.includes("probabil")) return "fa-percent";
        if (l.includes("bien") || l.includes("propert")) return "fa-building";
        if (l.includes("contact") || l.includes("partner")) return "fa-address-book-o";
        if (l.includes("transaction")) return "fa-exchange";
        return "fa-pencil-square-o";
    }
    toneForField(label) {
        const l = (label || "").toLowerCase();
        if (l.includes("étape") || l.includes("etape") || l.includes("stage")) return "accent";
        if (l.includes("score")) return "warning";
        return "info";
    }

    onNoteInput(ev) { this.state.newNote = ev.target.value; }

    async postNote() {
        const body = (this.state.newNote || "").trim();
        if (!body || this.state.posting) return;
        this.state.posting = true;
        try {
            await this.orm.call(
                "civora.opportunity", "message_post",
                [[this.props.opportunityId]],
                { body: body, message_type: "comment", subtype_xmlid: "mail.mt_note" },
            );
            this.state.newNote = "";
            await this.load();
        } finally {
            this.state.posting = false;
        }
    }
}
