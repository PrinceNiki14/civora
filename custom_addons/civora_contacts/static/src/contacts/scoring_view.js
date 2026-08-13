/* @odoo-module */
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";
import { CivoraBadge, CivoraProgress } from "@civora_core/components/civora_kit";

const STATUS_LABELS = {
    chaud: "Chaud",
    actif: "Actif",
    qualifie: "Qualifié",
    a_risque: "À risque",
    inactif: "Inactif",
};

const RECO_META = {
    to_close: {
        tone: "success",
        icon: "fa-trophy",
        title: "leads ultra-chauds à closer",
        hint: "Score ≥ 85 · contact dans les 7 derniers jours",
    },
    to_revive: {
        tone: "warning",
        icon: "fa-bell-o",
        title: "contacts à relancer",
        hint: "Score 30-84 · aucun échange depuis plus de 14 jours",
    },
    to_reclass: {
        tone: "accent",
        icon: "fa-random",
        title: "contacts à reclasser",
        hint: "Score et statut CRM incohérents",
    },
};
const RECO_ORDER = ["to_close", "to_revive", "to_reclass"];

/**
 * Onglet "Scoring IA" de l'écran Contacts.
 *
 * Affiche la distribution réelle du score IA calculé par
 * res.partner.civora_compute_ai_score (formule v10.1.0), les pondérations
 * effectives de cette formule, et trois recommandations calculées.
 *
 * Principe directeur : aucun chiffre décoratif. Tout ce qui est affiché
 * correspond à une requête réelle sur la base, pour qu'un gestionnaire
 * puisse justifier chaque nombre devant son client.
 */
export class ContactsScoringView extends Component {
    static template = "civora_contacts.ScoringView";
    static components = { CivoraStatCard, CivoraBadge, CivoraProgress };
    static props = {
        onFilterScore: { type: Function, optional: true },
        onOpenContact: { type: Function, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.recoOrder = RECO_ORDER;
        this.recoMeta = RECO_META;

        this.state = useState({
            loading: true,
            error: "",
            data: null,
            listMode: "top",        // "top" | "flop"
            expandedReco: "",       // clé de la reco dépliée
            recomputing: false,
        });

        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        this.state.error = "";
        try {
            this.state.data = await this.orm.call(
                "res.partner", "civora_get_scoring_analytics", []
            );
        } catch (e) {
            console.error("[CIVORA-SCORING] load", e);
            this.state.error = "Impossible de charger les statistiques de scoring.";
        } finally {
            this.state.loading = false;
        }
    }

    // ---- Helpers d'affichage ----------------------------------------
    statusLabel(code) {
        return STATUS_LABELS[code] || "—";
    }

    statusVariant(code) {
        if (code === "chaud") return "danger";
        if (code === "actif") return "success";
        if (code === "qualifie") return "info";
        if (code === "a_risque") return "warning";
        return "neutral";
    }

    scoreTone(score) {
        if (score >= 85) return "success";
        if (score >= 60) return "success";
        if (score >= 30) return "warning";
        return "danger";
    }

    get currentList() {
        if (!this.state.data) return [];
        return this.state.listMode === "top"
            ? this.state.data.top
            : this.state.data.flop;
    }

    /** Total des pondérations — sert de contrôle de cohérence affiché. */
    get weightTotal() {
        if (!this.state.data) return 0;
        return this.state.data.weights.reduce((acc, w) => acc + w.weight, 0);
    }

    formatDate(str) {
        if (!str) return "—";
        const d = new Date(str.replace(" ", "T") + "Z");
        if (isNaN(d.getTime())) return "—";
        return d.toLocaleDateString("fr-FR", {
            day: "2-digit", month: "short", year: "numeric",
            hour: "2-digit", minute: "2-digit",
        });
    }

    // ---- Interactions -----------------------------------------------
    setListMode(mode) {
        this.state.listMode = mode;
    }

    toggleReco(key) {
        this.state.expandedReco = this.state.expandedReco === key ? "" : key;
    }

    /** Clic sur une tranche → filtre l'Annuaire sur cette plage de score. */
    onBucketClick(bucket) {
        if (!bucket.count) {
            this.notification.add(
                "Aucun contact dans la tranche « " + bucket.label + " ».",
                { type: "info", sticky: false }
            );
            return;
        }
        if (this.props.onFilterScore) {
            this.props.onFilterScore(bucket.min, bucket.max, bucket.label);
        }
    }

    onContactClick(item) {
        if (this.props.onOpenContact) {
            this.props.onOpenContact({ id: item.id });
        }
    }

    /**
     * Programme un recalcul global. Le traitement est asynchrone (cron) :
     * on ne bloque pas la requête HTTP sur un portefeuille de grande taille.
     */
    async recomputeAll() {
        if (this.state.recomputing) return;
        this.state.recomputing = true;
        try {
            const res = await this.orm.call(
                "res.partner", "civora_request_score_recompute", []
            );
            if (res && res.queued) {
                this.notification.add(
                    "Recalcul programmé sur " + res.pending + " contacts. " +
                    "Il démarrera dans moins d'une minute — actualisez ensuite.",
                    { type: "success", sticky: false }
                );
            } else {
                this.notification.add(
                    (res && res.error) || "Recalcul impossible.",
                    { type: "warning" }
                );
            }
        } catch (e) {
            console.error("[CIVORA-SCORING] recompute", e);
            this.notification.add(
                "Impossible de programmer le recalcul. Consultez les logs serveur.",
                { type: "danger" }
            );
        } finally {
            this.state.recomputing = false;
        }
    }
}
