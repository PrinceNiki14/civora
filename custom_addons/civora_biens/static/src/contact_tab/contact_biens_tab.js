import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { CivoraBadge } from "@civora_core/components/civora_kit";

const STATUS_META = {
    disponible: { label: "Disponible", variant: "success" },
    loue: { label: "Loué", variant: "info" },
    saisonnier: { label: "Saisonnier", variant: "warning" },
};

/**
 * Onglet "Biens liés" injecte dans la fiche contact 360 (registre
 * civora_contact_360_tab). Liste les biens dont le contact est proprietaire.
 */
export class ContactBiensTab extends Component {
    static template = "civora_biens.ContactBiensTab";
    static components = { CivoraBadge };
    static props = {
        contactId: { type: [Number, Boolean] },
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ loading: true, biens: [] });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        if (!this.props.contactId) {
            this.state.biens = [];
            this.state.loading = false;
            return;
        }
        this.state.biens = await this.orm.searchRead(
            "civora.property",
            [["owner_id", "=", this.props.contactId]],
            ["name", "ref", "status", "city", "neighborhood", "price", "monthly_revenue", "image_128", "property_type_id"],
            { order: "name" }
        );
        this.state.loading = false;
    }

    statusMeta(p) {
        return STATUS_META[p.status] || { label: "—", variant: "neutral" };
    }
    typeLabel(p) {
        return p.property_type_id ? p.property_type_id[1] : "—";
    }
    locLabel(p) {
        return [p.neighborhood, p.city].filter(Boolean).join(", ") || "—";
    }
    fmtMoney(n) {
        n = Number(n || 0);
        if (n >= 1e9) return (n / 1e9).toFixed(1).replace(".", ",") + " Md";
        if (n >= 1e6) return (n / 1e6).toFixed(n % 1e6 ? 1 : 0).replace(".", ",") + " M";
        if (n >= 1e3) return Math.round(n / 1e3) + " k";
        return "" + n;
    }
    openProperty(p) {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.property_360",
            params: {
                propertyId: p.id,
                origin: {
                    tag: "civora.contact_360",
                    params: { contactId: this.props.contactId, tab: "properties" },
                    label: "Contact",
                },
            },
            target: "current",
        });
    }
}

registry.category("civora_contact_360_tab").add("properties", {
    id: "properties",
    label: "Biens liés",
    Component: ContactBiensTab,
    sequence: 20,
});
