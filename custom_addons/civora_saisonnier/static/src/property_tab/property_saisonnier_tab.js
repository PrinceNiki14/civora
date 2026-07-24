/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

function fmtMoney(v) {
    if (!v && v !== 0) return "0";
    return Number(v).toLocaleString("fr-FR");
}

export class PropertySaisonnierTab extends Component {
    static template = "civora_saisonnier.PropertySaisonnierTab";
    static props = {
        propertyId: { type: Number },
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            reservations: [],
            tariffs: [],
            stats: {},
        });
        onWillStart(() => this.load());
    }

    async load() {
        const pid = this.props.propertyId;
        if (!pid) return;

        const [reservations, tariffs] = await Promise.all([
            this.orm.searchRead("civora.reservation", [
                ["property_id", "=", pid],
            ], [
                "name", "guest_id", "checkin_date", "checkout_date",
                "num_nights", "total_amount", "state", "source",
            ], { order: "checkin_date desc", limit: 50 }),
            this.orm.searchRead("civora.seasonal.tariff", [
                ["property_id", "=", pid],
            ], [
                "name", "season", "date_start", "date_end",
                "tariff_night", "min_nights",
            ], { order: "date_start asc" }),
        ]);
        this.state.reservations = reservations;
        this.state.tariffs = tariffs;

        const active = reservations.filter(r => !["cancelled", "draft"].includes(r.state));
        const totalRevenue = active.reduce((s, r) => s + (r.total_amount || 0), 0);
        const totalNights = active.reduce((s, r) => s + (r.num_nights || 0), 0);
        this.state.stats = {
            total: reservations.length,
            active: active.length,
            revenue: totalRevenue,
            adr: active.length ? Math.round(totalRevenue / (totalNights || 1)) : 0,
        };
    }

    fmtMoney(v) { return fmtMoney(v); }

    stateLabel(s) {
        const m = { draft: "Brouillon", confirmed: "Confirmée", checkin: "En séjour", checkout: "Terminée", cancelled: "Annulée" };
        return m[s] || s;
    }

    seasonLabel(s) {
        const m = { basse: "Basse", moyenne: "Moyenne", haute: "Haute", fete: "Fêtes" };
        return m[s] || s;
    }

    openReservation(id) {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.reservation_360",
            params: { reservation_id: id },
        });
    }
}

registry.category("civora_property_360_tab").add("saisonnier", {
    Component: PropertySaisonnierTab,
    label: "Saisonnier",
    sequence: 30,
});
