/* @odoo-module */
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";
import { CivoraBadge } from "@civora_core/components/civora_kit";

const CONSENT_META = {
    opt_in: { label: "Opt-in", variant: "success" },
    opt_out: { label: "Opt-out", variant: "danger" },
    none: { label: "—", variant: "neutral" },
};

const CHANNELS = [
    { code: "email", label: "Email", icon: "fa-envelope-o" },
    { code: "sms", label: "SMS", icon: "fa-comment-o" },
    { code: "whatsapp", label: "WhatsApp", icon: "fa-whatsapp" },
];

/**
 * Onglet "RGPD & Consentements" de l'écran Contacts.
 * Fournit :
 * - 4 KPIs : Opt-in marketing / Demandes traitées / Données à MAJ / Conformité globale
 * - Registre : tableau paginé des contacts avec leurs 3 consentements + dernier changement
 * - Actions par contact : Historique consentements · Export perso · Droit à l'oubli
 * - Actions globales : Export DPO (CSV registre complet)
 */
export class ContactsRgpdView extends Component {
    static template = "civora_contacts.RgpdView";
    static components = { CivoraStatCard, CivoraBadge };
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.channels = CHANNELS;

        this.state = useState({
            loading: true,
            kpis: null,
            rows: [],
            total: 0,
            offset: 0,
            limit: 100,
            filterChannel: "",
            filterValue: "",
            exporting: false,
            // Panneau historique (drawer léger)
            historyOpen: false,
            historyContact: null,
            historyEvents: [],
            historyLoading: false,
        });

        onWillStart(() => this.load());
    }

    consentMeta(v) { return CONSENT_META[v] || CONSENT_META.none; }

    async load(append = false) {
        this.state.loading = !append;
        try {
            const res = await this.orm.call(
                "res.partner", "civora_get_rgpd_registry",
                [], {
                    offset: append ? this.state.offset : 0,
                    limit: this.state.limit,
                    filter_channel: this.state.filterChannel || null,
                    filter_value: this.state.filterValue || null,
                }
            );
            if (append) {
                this.state.rows = [...this.state.rows, ...res.rows];
            } else {
                this.state.rows = res.rows;
                this.state.kpis = res.kpis;
            }
            this.state.total = res.total;
            this.state.offset = (append ? this.state.offset : 0) + res.rows.length;
        } catch (e) {
            console.error("[CIVORA-RGPD] load", e);
            this.notification.add("Erreur lors du chargement du registre RGPD.", { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }
    async loadMore() { await this.load(true); }

    async setFilterChannel(ev) {
        this.state.filterChannel = ev.target.value;
        if (!this.state.filterChannel) this.state.filterValue = "";
        this.state.offset = 0;
        await this.load();
    }
    async setFilterValue(ev) {
        this.state.filterValue = ev.target.value;
        this.state.offset = 0;
        await this.load();
    }

    get hasMore() {
        return this.state.rows.length < this.state.total;
    }

    async exportDpo() {
        if (this.state.exporting) return;
        this.state.exporting = true;
        try {
            const res = await this.orm.call(
                "res.partner", "civora_export_dpo",
                [], { domain: [["civora_is_contact", "=", true]] }
            );
            if (!res || !res.content) {
                this.notification.add("Export vide.", { type: "warning" });
                return;
            }
            const link = document.createElement("a");
            link.href = "data:text/csv;charset=utf-8;base64," + res.content;
            link.download = res.filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            this.notification.add(`Export DPO généré (${res.count} contacts).`,
                { type: "success" });
        } catch (e) {
            console.error("[CIVORA-RGPD] export", e);
            this.notification.add("Erreur lors de l'export DPO.", { type: "danger" });
        } finally {
            this.state.exporting = false;
        }
    }

    // ---- Historique consentements d'un contact ----
    async openHistory(row) {
        this.state.historyOpen = true;
        this.state.historyContact = row;
        this.state.historyEvents = [];
        this.state.historyLoading = true;
        try {
            const events = await this.orm.call(
                "res.partner", "civora_get_consent_history",
                [], { contact_id: row.id }
            );
            this.state.historyEvents = events || [];
        } catch (e) {
            this.notification.add("Erreur historique.", { type: "danger" });
        } finally {
            this.state.historyLoading = false;
        }
    }
    closeHistory() {
        this.state.historyOpen = false;
        this.state.historyContact = null;
    }

    // ---- Export perso (droit d'accès RGPD) ----
    async exportPersonal(row) {
        try {
            const res = await this.orm.call(
                "res.partner", "civora_export_personal_data",
                [], { contact_id: row.id }
            );
            if (!res || !res.success) {
                this.notification.add(res.error || "Erreur d'export.", { type: "danger" });
                return;
            }
            const link = document.createElement("a");
            link.href = "data:application/json;charset=utf-8;base64," + res.content;
            link.download = res.filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            this.notification.add("Export des données personnelles généré.",
                { type: "success" });
        } catch (e) {
            console.error("[CIVORA-RGPD] export perso", e);
            this.notification.add("Erreur lors de l'export.", { type: "danger" });
        }
    }

    // ---- Droit à l'oubli (2 clics de confirmation) ----
    async anonymize(row) {
        if (row.is_anonymized) {
            this.notification.add("Ce contact est déjà anonymisé.", { type: "warning" });
            return;
        }
        this.dialog.add(
            (await import("@web/core/confirmation_dialog/confirmation_dialog")).ConfirmationDialog,
            {
                title: "Droit à l'oubli — Confirmation",
                body: `Cette action va anonymiser définitivement ${row.name} : nom, email, téléphone, adresse effacés. Les statistiques (rôle, statut, score) et l'historique comptable sont conservés. Confirmer ?`,
                confirmLabel: "Anonymiser",
                cancelLabel: "Annuler",
                confirm: async () => {
                    try {
                        const res = await this.orm.call(
                            "res.partner", "civora_anonymize_contact",
                            [], { contact_id: row.id, reason: "Demande d'anonymisation via interface RGPD" }
                        );
                        if (res && res.success) {
                            this.notification.add(`${row.name} a été anonymisé.`,
                                { type: "success" });
                            await this.load();
                        } else {
                            this.notification.add(res.error || "Erreur.", { type: "danger" });
                        }
                    } catch (e) {
                        console.error("[CIVORA-RGPD] anonymize", e);
                        this.notification.add("Erreur lors de l'anonymisation.", { type: "danger" });
                    }
                },
                cancel: () => {},
            }
        );
    }

    // ---- Helpers ----
    fmtDate(s) {
        if (!s) return "—";
        const d = new Date(s);
        if (isNaN(d)) return s;
        return d.toLocaleDateString("fr-FR");
    }
    fmtDateTime(s) {
        if (!s) return "—";
        const d = new Date(s);
        if (isNaN(d)) return s;
        return d.toLocaleDateString("fr-FR") + " " +
               String(d.getHours()).padStart(2, "0") + ":" +
               String(d.getMinutes()).padStart(2, "0");
    }
}
