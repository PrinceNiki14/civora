import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { CivoraBadge, CivoraProgress } from "@civora_core/components/civora_kit";

const STATUS_META = {
    actif: { label: "Actif", variant: "success" },
    retard: { label: "Retard", variant: "danger" },
    expire_bientot: { label: "Expire bientôt", variant: "warning" },
    resilie: { label: "Résilié", variant: "neutral" },
};
const LEASE_FIELDS = [
    "name", "tenant_id", "rent", "charges", "deposit", "date_start", "date_end",
    "payday", "status", "payment_rate", "total_monthly",
];

/**
 * Onglet "Bail" injecte dans la fiche bien 360 (registre civora_property_360_tab).
 * Affiche le(s) bail(aux) de ce bien (le plus recent en tete).
 */
export class PropertyLeaseTab extends Component {
    static template = "civora_locations.PropertyLeaseTab";
    static components = { CivoraBadge, CivoraProgress };
    static props = {
        propertyId: { type: [Number, Boolean], optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ loading: true, leases: [] });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        if (!this.props.propertyId) {
            this.state.leases = [];
            this.state.loading = false;
            return;
        }
        this.state.leases = await this.orm.searchRead(
            "civora.lease",
            [["property_id", "=", this.props.propertyId]],
            LEASE_FIELDS,
            { order: "date_start desc" }
        );
        this.state.loading = false;
    }

    statusMeta(l) {
        return STATUS_META[l.status] || { label: "—", variant: "neutral" };
    }
    fmtDate(d) {
        if (!d) return "—";
        const [y, m, day] = String(d).split("-");
        return day && m && y ? `${day}/${m}/${y}` : d;
    }
    fmtMoney(n) {
        n = Number(n || 0);
        if (n >= 1e9) return (n / 1e9).toFixed(1).replace(".", ",") + " Md";
        if (n >= 1e6) return (n / 1e6).toFixed(n % 1e6 ? 1 : 0).replace(".", ",") + " M";
        if (n >= 1e3) return Math.round(n / 1e3) + " k";
        return "" + n;
    }
    kpiMoney(n) {
        return this.fmtMoney(n) + " FCFA";
    }
    openLease(l) {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.lease_360",
            params: {
                leaseId: l.id,
                origin: {
                    tag: "civora.property_360",
                    params: { propertyId: this.props.propertyId },
                    label: "Bien",
                },
            },
            target: "current",
        });
    }
}

registry.category("civora_property_360_tab").add("lease", {
    id: "lease",
    label: "Bail",
    Component: PropertyLeaseTab,
    sequence: 30,
});
