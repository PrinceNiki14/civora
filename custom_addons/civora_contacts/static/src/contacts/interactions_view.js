/* @odoo-module */
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";
import { CivoraBadge, CivoraAvatar, CivoraProgress } from "@civora_core/components/civora_kit";

const PAGE_SIZE = 30;

const PERIOD_OPTIONS = [
    { value: "7", label: "7 jours" },
    { value: "30", label: "30 jours" },
    { value: "90", label: "90 jours" },
    { value: "", label: "Tout l'historique" },
];

/**
 * Onglet "Interactions" de l'écran Contacts.
 *
 * Flux global multi-contacts (tous contacts confondus) alimenté par le
 * modèle civora.interaction, avec filtres canal / agent / période et
 * pagination incrémentale — le flux d'une grande agence n'est jamais
 * chargé en entier.
 *
 * Les événements 'role_change' sont exclus côté serveur : ce sont des
 * traces d'audit, visibles dans la timeline de la fiche 360°.
 */
export class ContactsInteractionsView extends Component {
    static template = "civora_contacts.InteractionsView";
    static components = { CivoraStatCard, CivoraBadge, CivoraAvatar, CivoraProgress };
    static props = {
        onOpenContact: { type: Function, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.periodOptions = PERIOD_OPTIONS;

        this.state = useState({
            loading: true,
            loadingMore: false,
            error: "",
            rows: [],
            total: 0,
            offset: 0,
            hasMore: false,
            stats: null,
            channels: [],
            agents: [],
            filters: {
                kind: "",
                agent_id: "",
                days: "30",
            },
        });

        onWillStart(async () => {
            await this.loadMeta();
            await this.reload();
        });
    }

    async loadMeta() {
        try {
            const meta = await this.orm.call(
                "civora.interaction", "civora_get_feed_meta", []
            );
            this.state.channels = meta.channels || [];
            this.state.agents = meta.agents || [];
        } catch (e) {
            console.error("[CIVORA-INTERACTIONS] meta", e);
        }
    }

    /** Recharge flux + statistiques (remise à zéro de la pagination). */
    async reload() {
        this.state.loading = true;
        this.state.error = "";
        this.state.offset = 0;
        try {
            const [feed, stats] = await Promise.all([
                this.fetchFeed(0),
                this.fetchStats(),
            ]);
            this.state.rows = feed.rows;
            this.state.total = feed.total;
            this.state.hasMore = feed.has_more;
            this.state.offset = feed.rows.length;
            this.state.stats = stats;
        } catch (e) {
            console.error("[CIVORA-INTERACTIONS] reload", e);
            this.state.error = "Impossible de charger le flux d'interactions.";
        } finally {
            this.state.loading = false;
        }
    }

    fetchFeed(offset) {
        const f = this.state.filters;
        return this.orm.call(
            "civora.interaction", "civora_get_global_feed",
            [], {
                offset: offset,
                limit: PAGE_SIZE,
                kind: f.kind || null,
                agent_id: f.agent_id ? parseInt(f.agent_id, 10) : null,
                days: f.days ? parseInt(f.days, 10) : null,
            }
        );
    }

    fetchStats() {
        // Le widget "Canaux" reste sur une fenêtre glissante cohérente avec
        // le filtre de période choisi (30 jours par défaut).
        const days = this.state.filters.days
            ? parseInt(this.state.filters.days, 10)
            : 365;
        return this.orm.call(
            "civora.interaction", "civora_get_channel_stats", [], { days: days }
        );
    }

    async loadMore() {
        if (this.state.loadingMore || !this.state.hasMore) return;
        this.state.loadingMore = true;
        try {
            const feed = await this.fetchFeed(this.state.offset);
            this.state.rows = [...this.state.rows, ...feed.rows];
            this.state.hasMore = feed.has_more;
            this.state.offset += feed.rows.length;
        } catch (e) {
            console.error("[CIVORA-INTERACTIONS] loadMore", e);
            this.notification.add("Impossible de charger la suite du flux.", {
                type: "danger",
            });
        } finally {
            this.state.loadingMore = false;
        }
    }

    // ---- Filtres -----------------------------------------------------
    setFilter(field, value) {
        this.state.filters[field] = value;
        this.reload();
    }

    resetFilters() {
        this.state.filters.kind = "";
        this.state.filters.agent_id = "";
        this.state.filters.days = "30";
        this.reload();
    }

    get activeFilterCount() {
        const f = this.state.filters;
        let n = 0;
        if (f.kind) n++;
        if (f.agent_id) n++;
        if (f.days !== "30") n++;
        return n;
    }

    // ---- Helpers d'affichage -----------------------------------------
    channelMeta(code) {
        return this.state.channels.find((c) => c.code === code) || {
            label: code, icon: "fa-circle-o", variant: "neutral",
        };
    }

    channelVariant(code) {
        return this.channelMeta(code).variant;
    }

    channelLabel(code) {
        return this.channelMeta(code).label;
    }

    get periodLabel() {
        const d = this.state.filters.days;
        const opt = PERIOD_OPTIONS.find((o) => o.value === d);
        return opt ? opt.label : "30 jours";
    }

    onContactClick(row) {
        if (row.contact_id && this.props.onOpenContact) {
            this.props.onOpenContact({ id: row.contact_id });
        }
    }
}
