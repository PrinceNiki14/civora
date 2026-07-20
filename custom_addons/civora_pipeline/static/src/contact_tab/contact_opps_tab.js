import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { CivoraBadge } from "@civora_core/components/civora_kit";

const TRANSACTION_LABEL = { vente: "Vente", location: "Loc.", saisonnier: "Saison." };

/** Onglet "Opportunités" injecte dans la fiche contact 360 (registre). */
export class ContactOppsTab extends Component {
    static template = "civora_pipeline.ContactOppsTab";
    static components = { CivoraBadge };
    static props = { contactId: { type: [Number, Boolean] } };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ loading: true, opps: [] });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        if (!this.props.contactId) {
            this.state.opps = [];
            this.state.loading = false;
            return;
        }
        this.state.opps = await this.orm.searchRead(
            "civora.opportunity", [["partner_id", "=", this.props.contactId]],
            ["name", "property_id", "transaction", "stage_id", "expected_amount", "score", "is_won", "is_lost"],
            { order: "stage_sequence, id desc" }
        );
        this.state.loading = false;
    }

    stageMeta(o) {
        if (o.is_won) return { label: o.stage_id ? o.stage_id[1] : "Gagné", variant: "success" };
        if (o.is_lost) return { label: o.stage_id ? o.stage_id[1] : "Perdu", variant: "danger" };
        return { label: o.stage_id ? o.stage_id[1] : "—", variant: "info" };
    }
    propertyLabel(o) {
        return o.property_id ? o.property_id[1] : "—";
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
                origin: { tag: "civora.contact_360", params: { contactId: this.props.contactId, tab: "deals" }, label: "Contact" },
            },
            target: "current",
        });
    }
}

registry.category("civora_contact_360_tab").add("deals", {
    id: "deals",
    label: "Opportunités",
    Component: ContactOppsTab,
    sequence: 15,
});
