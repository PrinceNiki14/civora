import { Component } from "@odoo/owl";

/**
 * CIVORA StatCard - carte KPI (label, valeur, delta, hint, icone).
 * Portage OWL du StatCard de ui-kit.tsx.
 */
export class CivoraStatCard extends Component {
    static template = "civora_core.StatCard";
    static props = {
        label: String,
        value: String,
        delta: { type: String, optional: true },
        hint: { type: String, optional: true },
        trend: { type: String, optional: true }, // "up" | "down" | "neutral"
        icon: { type: String, optional: true },  // classe Font Awesome
    };

    /**
     * Le reste du design system (CivoraDrawer) attend une icone sans prefixe
     * ("fa-tag"). La StatCard, elle, injectait la valeur telle quelle : une
     * icone passee sous cette forme perdait la classe de base `fa` et ne
     * s'affichait donc jamais (toutes les cartes tombaient sur le meme glyphe
     * de secours). On normalise ici plutot que dans chaque ecran.
     */
    get iconClass() {
        const raw = (this.props.icon || "fa-circle-o").trim();
        const parts = raw.split(/\s+/);
        const family = parts.find((c) => ["fa", "fas", "far", "fab", "fal"].includes(c));
        return family ? raw : `fa ${raw}`;
    }

    get trendClass() {
        if (this.props.trend === "down") return "civora-trend-down";
        if (this.props.trend === "neutral") return "civora-trend-neutral";
        return "civora-trend-up";
    }
}
