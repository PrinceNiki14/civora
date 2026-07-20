import { Component } from "@odoo/owl";

/**
 * CIVORA Insight - carte "IA · Insight" (titre, corps, action, tonalite).
 * Portage OWL du AIInsight de ui-kit.tsx.
 */
export class CivoraInsight extends Component {
    static template = "civora_core.Insight";
    static props = {
        title: String,
        body: String,
        tone: { type: String, optional: true },          // "accent" | "info" | "warning"
        actionLabel: { type: String, optional: true },
        actionPrimary: { type: Boolean, optional: true },
    };

    onAction() {
        // Placeholder : a brancher sur une vraie action plus tard.
    }
}
