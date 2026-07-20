import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { CivoraBadge } from "@civora_core/components/civora_kit";

const TRANSACTION_LABEL = { vente: "Vente", location: "Loc.", saisonnier: "Saison." };

/** Onglet "Opportunités" injecte dans la fiche bien 360 (registre). */
export class PropertyOppsTab extends Component {
    static template = "civora_pipeline.PropertyOppsTab";
    static components = { CivoraBadge };
    static props = { propertyId: { type: [Number, Boolean] } };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ loading: true, opps: [] });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        if (!this.props.propertyId) {
            this.state.opps = [];
            this.state.loading = false;
            return;
        }
        this.state.opps = await this.orm.searchRead(
            "civora.opportunity", [["property_id", "=", this.props.propertyId]],
            ["name", "partner_id", "transaction", "stage_id", "expected_amount", "score", "is_won", "is_lost"],
            { order: "stage_sequence, id desc" }
        );
        this.state.loading = false;
    }

    stageMeta(o) {
        if (o.is_won) return { label: o.stage_id ? o.stage_id[1] : "Gagné", variant: "success" };
        if (o.is_lost) return { label: o.stage_id ? o.stage_id[1] : "Perdu", variant: "danger" };
        return { label: o.stage_id ? o.stage_id[1] : "—", variant: "info" };
    }
    partnerLabel(o) {
        return o.partner_id ? o.partner_id[1] : "Sans contact";
    }
    txLabel(o) {
        return TRANSACTION_LABEL[o.transaction] || "";
    }
    isRental(o) {
        return o.transaction === "location" || o.transaction === "saisonnier";
    }
    fmtMoney(n) {
        n = Number(n || 0);
        if (n >= 1e9) return (n / 1e9).toFixed(1).replace(".", ",") + " Md";
        if (n >= 1e6) return (n / 1e6).toFixed(n % 1e6 ? 1 : 0).replace(".", ",") + " M";
        if (n >= 1e3) return Math.round(n / 1e3) + " k";
        return "" + n;
    }
    amountLabel(o) {
        return this.fmtMoney(o.expected_amount) + (this.isRental(o) ? "/m" : "") + " FCFA";
    }
    open(o) {
        this.action.doAction({
            type: "ir.actions.client", tag: "civora.opportunity_360",
            params: {
                opportunityId: o.id,
                origin: { tag: "civora.property_360", params: { propertyId: this.props.propertyId }, label: "Bien" },
            },
            target: "current",
        });
    }
}

registry.category("civora_property_360_tab").add("deals", {
    id: "deals",
    label: "Opportunités",
    Component: PropertyOppsTab,
    sequence: 15,
});
