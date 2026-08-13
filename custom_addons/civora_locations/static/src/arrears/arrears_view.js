import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CivoraBadge } from "@civora_core/components/civora_kit";
import { ReminderDrawer } from "@civora_locations/incidents/reminder_drawer";
import { BulkReminderDialog } from "./bulk_reminder_dialog";

const SEVERITY_META = {
    soft: { label: "Léger", variant: "warning", color: "#f59e0b", order: 3 },
    moderate: { label: "Modéré", variant: "warning", color: "#ea580c", order: 2 },
    firm: { label: "Ferme", variant: "danger", color: "#dc2626", order: 1 },
    legal: { label: "Critique", variant: "danger", color: "#991b1b", order: 0 },
};

/**
 * Vue Impayes du portefeuille.
 *
 * Complementaire de l'onglet Incidents du Bail 360 : celui-ci traite UN
 * bail en profondeur, celui-la donne au gestionnaire sa file de travail
 * du matin, tous baux confondus, triee par gravite puis par montant.
 *
 * Toutes les donnees viennent d'un seul RPC agrege
 * (civora.lease.get_arrears_portfolio) : boucler cote client sur les
 * echeances de chaque bail rendrait l'ecran inutilisable des quelques
 * centaines de baux.
 */
export class ArrearsView extends Component {
    static template = "civora_locations.ArrearsView";
    static components = { CivoraBadge, ReminderDrawer, BulkReminderDialog };
    static props = {
        onOpenLease: { type: Function, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.rows = [];
        this.state = useState({
            loading: true,
            error: "",
            list: [],
            summary: {},
            queue: [],
            severity: "all",
            query: "",
            selected: {},
            drawer: null,
            bulk: null,
            noticeBusy: 0,
        });

        onWillStart(async () => {
            await this.load();
        });
    }

    // ── Chargement ─────────────────────────────────────────────────────
    async load() {
        this.state.loading = true;
        this.state.error = "";
        try {
            const [rows, summary, queue] = await Promise.all([
                this.orm.call("civora.lease", "get_arrears_portfolio", []),
                this.orm.call("civora.lease", "get_arrears_summary", []),
                this.orm.call("civora.lease.reminder", "civora_get_pending_queue", []),
            ]);
            this.rows = rows || [];
            this.state.summary = summary || {};
            this.state.queue = queue || [];
            this.applyFilter();
        } catch (e) {
            console.error("[CIVORA-ARREARS] load", e);
            this.state.error =
                "Impossible de charger les impayés. Rechargez la page ou contactez votre administrateur.";
            this.rows = [];
            this.state.list = [];
        }
        this.state.loading = false;
    }

    applyFilter() {
        const sev = this.state.severity;
        const q = (this.state.query || "").trim().toLowerCase();
        this.state.list = this.rows.filter((r) => {
            if (sev !== "all" && r.severity !== sev) return false;
            if (!q) return true;
            return (
                (r.tenant_name || "").toLowerCase().includes(q) ||
                (r.property_name || "").toLowerCase().includes(q) ||
                (r.lease_ref || "").toLowerCase().includes(q)
            );
        });
        // Une ligne filtrée hors vue ne doit pas rester sélectionnée : sinon
        // un envoi groupé partirait vers des baux que l'écran ne montre plus.
        const visible = new Set(this.state.list.map((r) => r.lease_id));
        for (const id of Object.keys(this.state.selected)) {
            if (!visible.has(parseInt(id, 10))) delete this.state.selected[id];
        }
    }

    setSeverity(s) {
        this.state.severity = s;
        this.applyFilter();
    }

    onSearch(ev) {
        this.state.query = ev.target.value;
        this.applyFilter();
    }

    // ── Sélection ──────────────────────────────────────────────────────
    isSelected(id) {
        return !!this.state.selected[id];
    }

    toggleRow(id) {
        if (this.state.selected[id]) {
            delete this.state.selected[id];
        } else {
            this.state.selected[id] = true;
        }
    }

    toggleAll() {
        if (this.allSelected) {
            this.state.selected = {};
        } else {
            const next = {};
            for (const r of this.state.list) next[r.lease_id] = true;
            this.state.selected = next;
        }
    }

    get selectedIds() {
        return Object.keys(this.state.selected).map((k) => parseInt(k, 10));
    }

    get selectedCount() {
        return this.selectedIds.length;
    }

    get allSelected() {
        return this.state.list.length > 0 && this.selectedCount === this.state.list.length;
    }

    get selectedAmount() {
        const ids = new Set(this.selectedIds);
        return this.rows
            .filter((r) => ids.has(r.lease_id))
            .reduce((sum, r) => sum + (r.amount_due || 0), 0);
    }

    // ── Filtres et compteurs ───────────────────────────────────────────
    get severityTabs() {
        const counts = { all: this.rows.length, soft: 0, moderate: 0, firm: 0, legal: 0 };
        for (const r of this.rows) counts[r.severity] = (counts[r.severity] || 0) + 1;
        return [
            { id: "all", label: "Tous", count: counts.all },
            { id: "legal", label: "Critique", count: counts.legal },
            { id: "firm", label: "Ferme", count: counts.firm },
            { id: "moderate", label: "Modéré", count: counts.moderate },
            { id: "soft", label: "Léger", count: counts.soft },
        ];
    }

    // ── Formatage ──────────────────────────────────────────────────────
    fmtMoney(v) {
        const n = Math.round(v || 0);
        return n.toLocaleString("fr-FR").replace(/\u202f|\u00a0/g, " ") + " F";
    }

    severityMeta(s) {
        return SEVERITY_META[s] || { label: "—", variant: "neutral", color: "#94a3b8" };
    }

    lastReminderLabel(r) {
        if (!r.last_reminder_date) return "Jamais relancé";
        const d = r.last_reminder_days;
        if (d === 0) return "Relancé aujourd'hui";
        if (d === 1) return "Relancé hier";
        return `Dernière relance : il y a ${d} jours`;
    }

    periodsLabel(r) {
        const extra = r.installment_count - 3;
        return extra > 0 ? `${r.periods} +${extra}` : r.periods;
    }

    // ── Actions unitaires ──────────────────────────────────────────────
    openLease(id) {
        if (this.props.onOpenLease) this.props.onOpenLease(id);
    }

    openReminder(row, channel) {
        // Le drawer est partage avec l'onglet Incidents du Bail 360 : il
        // attend un defaultContext { severity, periods: [...] }, chaque
        // periode portant period_label / days_overdue / amount_remaining.
        this.state.drawer = {
            leaseId: row.lease_id,
            installmentIds: row.installment_ids || [],
            context: {
                severity: row.severity,
                channel,
                periods: row.periods_detail || [],
            },
        };
    }

    closeReminder() {
        this.state.drawer = null;
    }

    async onReminderSaved() {
        this.state.drawer = null;
        await this.load();
        this.notification.add("Relance enregistrée.", { type: "success" });
    }

    openWhatsapp(row) {
        const phone = (row.tenant_phone || "").replace(/[^0-9]/g, "");
        if (!phone) {
            this.notification.add("Ce locataire n'a pas de numéro de téléphone.", {
                type: "warning",
            });
            return;
        }
        const msg =
            `Bonjour ${row.tenant_name}, votre loyer pour ${row.periods} ` +
            `présente un retard de ${row.days_overdue} jour(s), soit ` +
            `${this.fmtMoney(row.amount_due)} restant dû. Merci de régulariser.`;
        window.open(`https://wa.me/${phone}?text=${encodeURIComponent(msg)}`, "_blank");
        // On ouvre aussi le drawer : un message WhatsApp non trace dans
        // CIVORA n'existe pas en cas de litige.
        this.openReminder(row, "whatsapp");
    }

    async createFormalNotice(row) {
        if (this.state.noticeBusy) return;
        this.state.noticeBusy = row.lease_id;
        try {
            const res = await this.orm.call(
                "civora.lease.reminder",
                "civora_create_formal_notice",
                [row.lease_id]
            );
            if (!res || !res.success) {
                this.notification.add(
                    (res && res.error) || "Impossible d'établir la mise en demeure.",
                    { type: "danger" }
                );
                return;
            }
            this.notification.add(`Mise en demeure ${res.name} établie.`, {
                type: "success",
            });
            window.open(
                `/report/pdf/civora_locations.report_formal_notice/${res.reminder_id}`,
                "_blank"
            );
            await this.load();
        } catch (e) {
            console.error("[CIVORA-ARREARS] formal notice", e);
            this.notification.add("Erreur lors de l'établissement de la mise en demeure.", {
                type: "danger",
            });
        } finally {
            this.state.noticeBusy = 0;
        }
    }

    // ── Relance groupée ────────────────────────────────────────────────
    openBulk() {
        if (!this.selectedCount) return;
        this.state.bulk = { leaseIds: this.selectedIds };
    }

    closeBulk() {
        this.state.bulk = null;
    }

    async onBulkDone(result) {
        this.state.bulk = null;
        this.state.selected = {};
        await this.load();
        if (result && result.sent) {
            const suffix = result.failed ? ` · ${result.failed} échec(s)` : "";
            this.notification.add(`${result.sent} relance(s) envoyée(s)${suffix}.`, {
                type: result.failed ? "warning" : "success",
            });
        }
    }
}
