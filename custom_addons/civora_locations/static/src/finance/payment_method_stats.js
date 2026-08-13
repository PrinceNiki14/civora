/** @odoo-module **/
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

// Palette CIVORA fixe pour les méthodes de paiement
const METHOD_COLORS = {
    virement:     "#0891b2",  // cyan
    wave:         "#1a56db",  // bleu Wave
    orange_money: "#ea580c",  // orange
    mtn_momo:     "#facc15",  // jaune MTN
    cheque:       "#7c3aed",  // violet
    especes:      "#16a34a",  // vert
    autre:        "#9aa2ad",  // gris
};

/**
 * Composant : Répartition par méthode de paiement
 *
 * Props :
 *   - leaseId (Number) : ID du bail
 *
 * Affiche un donut SVG + une liste avec méthodes, montants, pourcentages.
 */
export class PaymentMethodStats extends Component {
    static template = "civora_locations.PaymentMethodStats";
    static props = {
        leaseId: Number,
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            loading: true,
            stats: [],
            total: 0,
        });

        onWillStart(async () => {
            await this._load();
        });
    }

    async _load() {
        this.state.loading = true;
        try {
            const stats = await this.orm.call(
                "civora.lease",
                "get_payment_method_stats",
                [[this.props.leaseId]]
            );
            this.state.stats = stats || [];
            this.state.total = (stats || []).reduce((s, x) => s + x.amount, 0);
        } catch (_) {
            this.state.stats = [];
            this.state.total = 0;
        }
        this.state.loading = false;
    }

    // ── Helpers ───────────────────────────────────────────────────────
    colorFor(methodKey) {
        return METHOD_COLORS[methodKey] || METHOD_COLORS.autre;
    }

    fmtAmount(v) {
        const n = Number(v) || 0;
        return n.toLocaleString("fr-FR").replace(/,/g, " ") + " FCFA";
    }

    fmtCount(n) {
        return n === 1 ? "1 versement" : `${n} versements`;
    }

    // ── Donut SVG : arcs calculés ─────────────────────────────────────
    get donutSegments() {
        if (!this.state.stats.length || !this.state.total) return [];
        const cx = 60, cy = 60, r = 45, sw = 18;
        const total = this.state.total;
        let currentAngle = -Math.PI / 2; // Départ à 12h
        const segs = [];
        for (const s of this.state.stats) {
            const fraction = s.amount / total;
            const angleSpan = fraction * 2 * Math.PI;
            const endAngle = currentAngle + angleSpan;
            const x1 = cx + r * Math.cos(currentAngle);
            const y1 = cy + r * Math.sin(currentAngle);
            const x2 = cx + r * Math.cos(endAngle);
            const y2 = cy + r * Math.sin(endAngle);
            const largeArc = angleSpan > Math.PI ? 1 : 0;
            // Path d'arc SVG (arc uniquement pour le trait épais)
            const d = `M ${x1.toFixed(2)} ${y1.toFixed(2)} A ${r} ${r} 0 ${largeArc} 1 ${x2.toFixed(2)} ${y2.toFixed(2)}`;
            segs.push({
                d,
                color: this.colorFor(s.method),
                strokeWidth: sw,
                method: s.method,
                methodLabel: s.method_label,
                percent: s.percent,
            });
            currentAngle = endAngle;
        }
        return segs;
    }

    get isEmpty() {
        return !this.state.loading && (!this.state.stats.length || this.state.total <= 0);
    }
}
