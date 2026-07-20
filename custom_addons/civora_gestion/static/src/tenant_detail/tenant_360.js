import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";
import { CivoraAvatar, CivoraBadge } from "@civora_core/components/civora_kit";

const STATUS_META = {
    disponible: { label: "Disponible", variant: "success" },
    loue: { label: "Loué", variant: "info" },
    saisonnier: { label: "Saisonnier", variant: "warning" },
};
const BIEN_FIELDS = [
    "name", "ref", "city", "neighborhood", "status",
    "price", "monthly_revenue", "property_type_id", "image_128", "owner_id",
];
const LEASE_FIELDS = [
    "name", "property_id", "rent", "charges", "deposit", "date_start", "date_end",
    "payday", "status", "payment_rate", "total_monthly",
];
const LEASE_STATUS_META = {
    actif: { label: "Actif", variant: "success" },
    retard: { label: "Retard", variant: "danger" },
    expire_bientot: { label: "Expire bientôt", variant: "warning" },
    resilie: { label: "Résilié", variant: "neutral" },
};

export class CivoraTenant360 extends Component {
    static template = "civora_gestion.Tenant360";
    static components = { CivoraStatCard, CivoraAvatar, CivoraBadge };
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        const params = (this.props.action && this.props.action.params) || {};
        this.tenantId = Number(params.tenantId) || false;

        this.state = useState({
            loading: true,
            error: "",
            tenant: null,
            biens: [],
            leases: [],
            activeTab: "overview",
            stats: { count: 0, mrr: 0 },
            segment: "",
        });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        if (!this.tenantId) {
            this.state.error = "Locataire introuvable.";
            this.state.loading = false;
            return;
        }
        try {
            const [p] = await this.orm.read(
                "res.partner", [this.tenantId],
                ["name", "email", "phone", "civora_whatsapp", "city", "is_company",
                 "civora_ai_score", "civora_segment_ids", "create_date"]
            );
            if (!p) {
                this.state.error = "Locataire introuvable.";
                this.state.loading = false;
                return;
            }
            this.state.tenant = p;
            const segId = (p.civora_segment_ids || [])[0];
            if (segId) {
                try {
                    const [s] = await this.orm.read("civora.contact.segment", [segId], ["name"]);
                    this.state.segment = s ? s.name : "";
                } catch (e) {
                    this.state.segment = "";
                }
            }
            this.state.biens = await this.orm.searchRead(
                "civora.property", [["tenant_id", "=", this.tenantId]], BIEN_FIELDS, { order: "name" }
            );
            let mrr = 0;
            for (const b of this.state.biens) mrr += b.monthly_revenue || 0;
            this.state.stats = { count: this.state.biens.length, mrr };
            this.state.leases = await this.orm.searchRead(
                "civora.lease", [["tenant_id", "=", this.tenantId]], LEASE_FIELDS, { order: "date_start desc" }
            );
        } catch (e) {
            this.state.error = "Impossible de charger le locataire.";
        }
        this.state.loading = false;
    }

    goBack() {
        this.action.doAction({ type: "ir.actions.client", tag: "civora.tenants", target: "current" });
    }
    setTab(id) {
        this.state.activeTab = id;
    }
    openContact() {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.contact_360",
            params: {
                contactId: this.tenantId,
                origin: { tag: "civora.tenant_360", params: { tenantId: this.tenantId }, label: "Locataire" },
            },
            target: "current",
        });
    }
    openLease(l) {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.lease_360",
            params: {
                leaseId: l.id,
                origin: { tag: "civora.tenant_360", params: { tenantId: this.tenantId }, label: "Locataire" },
            },
            target: "current",
        });
    }
    leaseStatusMeta(l) {
        return LEASE_STATUS_META[l.status] || { label: "—", variant: "neutral" };
    }
    fmtDate(d) {
        if (!d) return "—";
        const [y, m, day] = String(d).split("-");
        return day && m && y ? `${day}/${m}/${y}` : d;
    }
    openProperty(b) {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.property_360",
            params: {
                propertyId: b.id,
                origin: { tag: "civora.tenant_360", params: { tenantId: this.tenantId }, label: "Locataire" },
            },
            target: "current",
        });
    }

    get tenant() {
        return this.state.tenant || {};
    }
    get tenantType() {
        return this.tenant.is_company ? "Société" : "Particulier";
    }
    statusMeta(b) {
        return STATUS_META[b.status] || { label: "—", variant: "neutral" };
    }
    typeLabel(b) {
        return b.property_type_id ? b.property_type_id[1] : "—";
    }
    ownerLabel(b) {
        return b.owner_id ? b.owner_id[1] : "—";
    }
    locLabel(b) {
        return [b.neighborhood, b.city].filter(Boolean).join(", ") || "—";
    }
    orDash(v) {
        return v || "—";
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
    get subtitle() {
        const c = this.state.stats.count;
        return this.tenantType + " · " + c + " bien" + (c > 1 ? "s" : "") + " loué" + (c > 1 ? "s" : "");
    }
    get tabList() {
        return [
            { id: "overview", label: "Vue d'ensemble" },
            { id: "biens", label: "Biens loués", count: this.state.stats.count },
            { id: "lease", label: "Bail", count: this.state.leases.length },
            { id: "payments", label: "Paiements" },
        ];
    }
}

registry.category("actions").add("civora.tenant_360", CivoraTenant360);
