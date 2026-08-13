import { patch } from "@web/core/utils/patch";
import { onWillStart } from "@odoo/owl";
import { CommandCenter } from "@civora_core/command_center/command_center";
import { useService } from "@web/core/utils/hooks";

/**
 * Patch du Command Center pour brancher les vraies données du module
 * civora_locations. Le composant reste 100% défini dans civora_core —
 * on remplace uniquement les valeurs illustratives par des vraies quand
 * la donnée est disponible côté serveur.
 *
 * Cartes remplacées avec vraies données :
 *  - MRR locatif
 *  - Baux actifs  (remplace "Programmes neufs" pour être aligné CDC)
 *  - Collections
 *  - Impayés
 *  - Taux occupation
 *
 * Sections remplacées :
 *  - Camembert Parc immobilier (occupancy_donut)
 *  - Activité live (activity)
 *
 * Les cartes illustratives restantes (Valeur portefeuille, Revenus du mois,
 * Pipeline value, Productivité équipe, VEFA, Acquéreurs, Visites) sont
 * laissées telles quelles — elles seront branchées par leurs modules
 * respectifs (comptabilité, pipeline, calendar).
 */
patch(CommandCenter.prototype, {
    setup() {
        // 1) Setup parent (initialise this.kpis, this.activity, etc. en illustratif)
        super.setup(...arguments);
        // 2) On garde une copie de secours des valeurs illustratives
        this._civoraLocationsFallback = {
            kpis: this.kpis.slice(),
            activity: this.activity.slice(),
            occupancyLegend: this.occupancyLegend.slice(),
        };
        // 3) Chargement des vraies données au willStart
        this.orm = useService("orm");
        onWillStart(async () => {
            try {
                const data = await this.orm.call(
                    "civora.lease", "get_command_center_kpis", []
                );
                if (data) {
                    this._applyLocationsData(data);
                }
            } catch (e) {
                // En cas d'erreur (ex : civora_locations pas installé, permissions),
                // on garde les valeurs illustratives silencieusement.
            }
        });
    },

    /**
     * Remplace les cartes KPI illustratives par les vraies quand la donnée
     * correspondante existe. On identifie chaque carte par son libellé
     * (comme défini dans civora_core) pour rester résilient à l'ordre.
     */
    _applyLocationsData(data) {
        const findAndReplace = (label, newProps) => {
            const idx = this.kpis.findIndex((k) => k.label === label);
            if (idx >= 0) {
                this.kpis[idx] = { ...this.kpis[idx], ...newProps };
            }
        };
        const fmtDelta = (pct) => {
            if (pct === null || pct === undefined) return "";
            const sign = pct > 0 ? "+" : "";
            return `${sign}${String(pct).replace(".", ",")}%`;
        };

        // --- MRR locatif ---
        if (data.mrr_locatif) {
            findAndReplace("MRR locatif", {
                value: data.mrr_locatif.value_fmt,
                delta: fmtDelta(data.mrr_locatif.delta_pct) || "vs mois précédent",
                hint: data.mrr_locatif.hint,
            });
        }
        // --- Baux actifs : remplace "Programmes neufs" (illustratif) ---
        // On préfère remplacer une carte illustrative pour ne pas casser la
        // grille 4×3 du Command Center.
        if (data.baux_actifs) {
            findAndReplace("Programmes neufs", {
                label: "Baux actifs",
                value: data.baux_actifs.value_fmt,
                delta: data.baux_actifs.hint,
                hint: "gestion locative",
                icon: "fa fa-key",
            });
        }
        // --- Collections ---
        if (data.collections) {
            findAndReplace("Collections", {
                value: data.collections.value_fmt,
                delta: fmtDelta(data.collections.delta_pct) || "encaissement",
                hint: data.collections.hint,
            });
        }
        // --- Impayés ---
        if (data.impayes) {
            findAndReplace("Impayés", {
                value: data.impayes.value_fmt,
                delta: fmtDelta(data.impayes.delta_pct) || "cumul en cours",
                hint: data.impayes.hint,
                trend: "down",
            });
        }
        // --- Taux occupation ---
        if (data.occupation) {
            findAndReplace("Taux occupation", {
                value: data.occupation.value_fmt,
                delta: fmtDelta(data.occupation.delta_pct) || "loué + réservé",
                hint: data.occupation.hint,
            });
        }

        // --- Donut Parc immobilier ---
        if (data.occupancy_donut && data.occupancy_donut.length) {
            this.occupancyLegend = data.occupancy_donut;
            // Reconstruire le chart config (même structure que civora_core)
            this.occupancyChart = {
                type: "doughnut",
                data: {
                    labels: this.occupancyLegend.map((o) => o.name),
                    datasets: [{
                        data: this.occupancyLegend.map((o) => o.value),
                        backgroundColor: this.occupancyLegend.map((o) => o.color),
                        borderWidth: 0,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: "70%",
                    plugins: { legend: { display: false } },
                },
            };
        }

        // --- Activité live ---
        if (data.activity && data.activity.length) {
            // Le composant XML lit t.t (title), t.d (detail), t.a (ago)
            this.activity = data.activity.map((it) => ({
                tone: it.tone,
                t: it.title,
                d: it.detail,
                a: it.ago,
            }));
        }
    },
});
