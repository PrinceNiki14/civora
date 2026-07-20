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

    get trendClass() {
        if (this.props.trend === "down") return "civora-trend-down";
        if (this.props.trend === "neutral") return "civora-trend-neutral";
        return "civora-trend-up";
    }
}
