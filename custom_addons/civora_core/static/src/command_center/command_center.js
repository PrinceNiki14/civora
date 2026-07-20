import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { CivoraStatCard } from "../components/civora_stat_card";
import { CivoraInsight } from "../components/civora_insight";
import { CivoraChart } from "../components/civora_chart";

/**
 * CIVORA - Command Center
 * Ecran d'accueil full-custom (client action OWL), calque sur le front CIVORA.
 * Aucune vue Odoo : composants CIVORA + donnees.
 *
 * NB : les valeurs KPI ci-dessous sont pour l'instant illustratives (les
 * modules immobiliers ne sont pas encore developpes). Chaque KPI est un objet
 * simple -> il suffira de remplacer "value" par un chargement ORM le moment venu.
 */
export class CommandCenter extends Component {
    static template = "civora_core.CommandCenter";
    static components = { CivoraStatCard, CivoraInsight, CivoraChart };
    static props = { ...standardActionServiceProps };

    setup() {
        this.insights = [
            {
                title: "3 biens à repositionner",
                body: "Le studio Marcory 2 a 28j sans visite. Baisse suggérée de 8% pour matcher le marché Q3.",
                tone: "accent",
                actionLabel: "Voir suggestions",
                actionPrimary: true,
            },
            {
                title: "Pic saisonnier détecté",
                body: "Demande +34% sur Cocody/Riviera mi-décembre. Ajustez les prix dynamiques de 6 biens.",
                tone: "info",
                actionLabel: "Activer pricing IA",
            },
            {
                title: "Risque impayé · 2 locataires",
                body: "Score IA dégradé pour Bamba S. et N'Guessan A. Lancer une relance personnalisée ?",
                tone: "warning",
                actionLabel: "Préparer relance",
            },
        ];

        this.kpis = [
            { label: "Valeur portefeuille", value: "14,8Md FCFA", delta: "+6,2% YoY", hint: "248 biens", icon: "fa fa-building-o" },
            { label: "MRR locatif", value: "142M FCFA", delta: "+12,3%", hint: "172 baux actifs", icon: "fa fa-key" },
            { label: "Revenus du mois", value: "35,8M", delta: "+18,4%", hint: "vs 30,2M cible", icon: "fa fa-money" },
            { label: "Taux occupation", value: "86%", delta: "+2,1 pts", hint: "seuil cible 82%", icon: "fa fa-line-chart" },

            { label: "Pipeline value", value: "3,4Md", delta: "+24%", hint: "58 deals actifs", icon: "fa fa-bullseye" },
            { label: "Collections", value: "92%", delta: "+1,8 pts", hint: "vs N-1", icon: "fa fa-credit-card" },
            { label: "Impayés", value: "4,2M", delta: "-12%", hint: "7 dossiers", icon: "fa fa-exclamation-circle", trend: "down" },
            { label: "Productivité équipe", value: "118%", delta: "vs objectif", hint: "12 agents", icon: "fa fa-bolt" },

            { label: "Programmes neufs", value: "6 actifs", delta: "+2 ce trim.", hint: "312 lots · 41% pré-vendus", icon: "fa fa-cubes" },
            { label: "Acquéreurs en cours", value: "84", delta: "+18 ce mois", hint: "Réservations VEFA + neuf", icon: "fa fa-handshake-o" },
            { label: "Visites planifiées", value: "37", delta: "cette semaine", hint: "22 confirmées · 6 reportées", icon: "fa fa-calendar" },
            { label: "CA VEFA prévisionnel", value: "2,1Md", delta: "+9,4%", hint: "Signatures Q4 attendues", icon: "fa fa-money" },
        ];

        this.pipeline = [
            { stage: "Leads", n: 142, v: "1,2Md", pct: 100 },
            { stage: "Qualifiés", n: 87, v: "980M", pct: 70 },
            { stage: "Visite", n: 54, v: "620M", pct: 48 },
            { stage: "Offre", n: 28, v: "420M", pct: 28 },
            { stage: "Signature", n: 12, v: "180M", pct: 12 },
        ];

        this.activity = [
            { tone: "accent", t: "Nouvelle réservation", d: "Villa Cocody · 3 nuits · 480k FCFA", a: "il y a 12 min" },
            { tone: "primary", t: "Bail signé électroniquement", d: "Appt. Plateau · 850k FCFA/mois", a: "il y a 1 h" },
            { tone: "warning", t: "Loyer en retard", d: "Studio Marcory · 3 jours · Bamba S.", a: "il y a 3 h" },
            { tone: "info", t: "Nouveau lead qualifié IA", d: "Famille Diallo · Villa 4 ch.", a: "il y a 5 h" },
            { tone: "success", t: "Paiement reçu", d: "1,2M FCFA · M. Touré", a: "hier" },
        ];

        this.agents = [
            { n: "Mariam B.", v: "12 ventes · 84M", accent: true },
            { n: "Kofi A.", v: "9 ventes · 62M" },
            { n: "Léa N.", v: "7 ventes · 51M" },
        ];

        // --- Graphe : Revenus & forecast (aire + ligne pointillee) ---
        const months = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août"];
        this.revenueChart = {
            type: "line",
            data: {
                labels: months,
                datasets: [
                    {
                        label: "Réalisé",
                        data: [18400, 21200, 24800, 22500, 28900, 31400, 35800, null],
                        borderColor: "#091e40",
                        backgroundColor: "rgba(9, 30, 64, .10)",
                        fill: true, tension: 0.4, pointRadius: 0, borderWidth: 2,
                    },
                    {
                        label: "Locations",
                        data: [12400, 13100, 14600, 15200, 16800, 17400, 18900, null],
                        borderColor: "#00ab68",
                        backgroundColor: "rgba(0, 171, 104, .14)",
                        fill: true, tension: 0.4, pointRadius: 0, borderWidth: 2,
                    },
                    {
                        label: "Forecast",
                        data: [19000, 22000, 25500, 26000, 30000, 33000, 38000, 40500],
                        borderColor: "#25afd2",
                        borderDash: [5, 5],
                        fill: false, tension: 0.4, pointRadius: 0, borderWidth: 2,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: "index", intersect: false },
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { display: false }, ticks: { color: "#626a75", font: { size: 11 } } },
                    y: {
                        grid: { color: "rgba(9, 30, 64, .06)" },
                        ticks: {
                            color: "#626a75", font: { size: 11 },
                            callback: (v) => v / 1000 + "k",
                        },
                    },
                },
            },
        };

        // --- Graphe : Parc immobilier (donut) ---
        this.occupancyLegend = [
            { name: "Loué", value: 68, color: "#00ab68" },
            { name: "Saisonnier", value: 18, color: "#25afd2" },
            { name: "Disponible", value: 14, color: "#c7ccd3" },
        ];
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

        // --- Graphe : Cash flow 7j (barres entrees vs sorties) ---
        this.cashflowChart = {
            type: "bar",
            data: {
                labels: ["L", "M", "M", "J", "V", "S", "D"],
                datasets: [
                    {
                        label: "Entrées",
                        data: [4.2, 5.6, 3.8, 6.1, 7.2, 2.4, 1.8],
                        backgroundColor: "#00ab68",
                        borderRadius: 4,
                    },
                    {
                        label: "Sorties",
                        data: [2.1, 3.2, 2.4, 4.0, 3.6, 1.1, 0.9],
                        backgroundColor: "#c7ccd3",
                        borderRadius: 4,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { display: false }, ticks: { color: "#626a75", font: { size: 11 } } },
                    y: {
                        beginAtZero: true,
                        grid: { color: "rgba(9, 30, 64, .06)" },
                        ticks: { color: "#626a75", font: { size: 11 } },
                    },
                },
            },
        };
    }

    get companyName() {
        return (user.activeCompany && user.activeCompany.name) || "CIVORA";
    }

    get subtitle() {
        return "Agence Premium Abidjan · 3 entités · 248 biens · 12 agents";
    }

    dotClass(tone) {
        return "civora-dot civora-dot-" + (tone || "muted");
    }

    initials(name) {
        return (name || "")
            .split(" ")
            .map((s) => s[0])
            .join("")
            .slice(0, 2)
            .toUpperCase();
    }
}

registry.category("actions").add("civora.command_center", CommandCenter);

// --- Ecran d'accueil : on remplace l'action "menu" par le Command Center ---
// (apres web_enterprise/home_menu qui enregistre "menu" dans son start())
const civoraHomeService = {
    dependencies: ["home_menu"],
    start() {
        registry.category("actions").add("menu", CommandCenter, { force: true });
    },
};
registry.category("services").add("civora_home", civoraHomeService);
