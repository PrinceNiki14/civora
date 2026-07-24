/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

function fmtMoney(v) {
    if (!v && v !== 0) return "0";
    return Number(v).toLocaleString("fr-FR");
}

const STATE_LABELS = {
    mandat: "Mandat",
    commercialisation: "Commercialisation",
    offre: "Offre",
    compromis: "Compromis",
    acte: "Acte",
    cloture: "Cloture",
    annule: "Annule",
};

class PropertyVentesTab extends Component {
    static template = "civora_ventes.PropertyVentesTab";
    static props = {
        propertyId: { type: Number },
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            sales: [],
            totalVolume: 0,
            activeSales: 0,
        });
        onWillStart(() => this.load());
    }

    async load() {
        const sales = await this.orm.searchRead("civora.sale", [
            ["property_id", "=", this.props.propertyId],
        ], [
            "name", "seller_id", "buyer_id", "state", "mandate_type",
            "asking_price", "sale_amount", "mandate_date", "acte_date",
        ], { order: "create_date desc" });
        this.state.sales = sales;
        this.state.totalVolume = sales
            .filter(s => s.state === "cloture")
            .reduce((sum, s) => sum + (s.sale_amount || 0), 0);
        this.state.activeSales = sales.filter(
            s => !["cloture", "annule"].includes(s.state)
        ).length;
    }

    fmtMoney(v) { return fmtMoney(v); }
    stateLabel(s) { return STATE_LABELS[s] || s; }
    stateClass(s) {
        const m = {
            mandat: "muted",
            commercialisation: "info",
            offre: "warning",
            compromis: "violet",
            acte: "primary",
            cloture: "success",
            annule: "danger",
        };
        return m[s] || "";
    }
}

registry.category("civora_property_360_tab").add("ventes", {
    Component: PropertyVentesTab,
    label: "Ventes",
    sequence: 25,
});
