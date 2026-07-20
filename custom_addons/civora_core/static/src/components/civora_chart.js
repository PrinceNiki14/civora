import { Component, onWillStart, onMounted, onWillUnmount, useRef } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";

/**
 * CIVORA Chart - composant graphe reutilisable base sur Chart.js
 * (bundle Odoo "web.chartjs_lib"). Props : type, data, options.
 */
export class CivoraChart extends Component {
    static template = "civora_core.Chart";
    static props = {
        type: String,
        data: Object,
        options: { type: Object, optional: true },
    };

    setup() {
        this.canvasRef = useRef("canvas");
        onWillStart(() => loadBundle("web.chartjs_lib"));
        onMounted(() => this._mountChart());
        onWillUnmount(() => this.chart && this.chart.destroy());
    }

    _mountChart() {
        // window.Chart est disponible apres loadBundle("web.chartjs_lib")
        this.chart = new window.Chart(this.canvasRef.el, {
            type: this.props.type,
            data: this.props.data,
            options: this.props.options || {},
        });
    }
}
