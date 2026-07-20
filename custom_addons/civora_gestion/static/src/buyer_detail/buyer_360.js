import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";
import { CivoraAvatar, CivoraBadge } from "@civora_core/components/civora_kit";

const STATUS_META = {
    chaud: { label: "Chaud", variant: "danger" },
    actif: { label: "Actif", variant: "success" },
    qualifie: { label: "Qualifié", variant: "info" },
    a_risque: { label: "À risque", variant: "warning" },
    inactif: { label: "Inactif", variant: "neutral" },
};
const MATCH_FIELDS = [
    "name", "ref", "city", "neighborhood", "surface", "bedrooms",
    "price", "yield_rate", "property_type_id", "image_128", "owner_id",
];

export class CivoraBuyer360 extends Component {
    static template = "civora_gestion.Buyer360";
    static components = { CivoraStatCard, CivoraAvatar, CivoraBadge };
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        const params = (this.props.action && this.props.action.params) || {};
        this.buyerId = Number(params.buyerId) || false;

        this.state = useState({
            loading: true,
            error: "",
            buyer: null,
            matches: [],
            activeTab: "overview",
            segment: "",
        });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        if (!this.buyerId) {
            this.state.error = "Acquéreur introuvable.";
            this.state.loading = false;
            return;
        }
        try {
            const [p] = await this.orm.read(
                "res.partner", [this.buyerId],
                ["name", "email", "phone", "civora_whatsapp", "city", "is_company",
                 "civora_budget", "civora_ai_score", "civora_status", "civora_agent_id",
                 "civora_source_id", "civora_next_action", "civora_segment_ids", "create_date"]
            );
            if (!p) {
                this.state.error = "Acquéreur introuvable.";
                this.state.loading = false;
                return;
            }
            this.state.buyer = p;
            const segId = (p.civora_segment_ids || [])[0];
            if (segId) {
                try {
                    const [s] = await this.orm.read("civora.contact.segment", [segId], ["name"]);
                    this.state.segment = s ? s.name : "";
                } catch (e) {
                    this.state.segment = "";
                }
            }
            const dom = [["transaction", "=", "vente"], ["status", "=", "disponible"]];
            if (p.civora_budget) {
                dom.push(["price", "<=", p.civora_budget]);
            }
            this.state.matches = await this.orm.searchRead(
                "civora.property", dom, MATCH_FIELDS, { limit: 60, order: "price desc" }
            );
        } catch (e) {
            this.state.error = "Impossible de charger l'acquéreur.";
        }
        this.state.loading = false;
    }

    goBack() {
        this.action.doAction({ type: "ir.actions.client", tag: "civora.buyers", target: "current" });
    }
    setTab(id) {
        this.state.activeTab = id;
    }
    openContact() {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.contact_360",
            params: {
                contactId: this.buyerId,
                origin: { tag: "civora.buyer_360", params: { buyerId: this.buyerId }, label: "Acquéreur" },
            },
            target: "current",
        });
    }
    openProperty(b) {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.property_360",
            params: {
                propertyId: b.id,
                origin: { tag: "civora.buyer_360", params: { buyerId: this.buyerId }, label: "Acquéreur" },
            },
            target: "current",
        });
    }
    async createOpportunity(b) {
        const res = await this.orm.create("civora.opportunity", [{
            name: (this.buyer.name || "Acquéreur") + " — " + b.name,
            partner_id: this.buyerId,
            property_id: b.id,
            transaction: "vente",
            expected_amount: b.price || 0,
            score: this.buyer.civora_ai_score || 0,
        }]);
        const oppId = Array.isArray(res) ? res[0] : res;
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.opportunity_360",
            params: {
                opportunityId: oppId,
                origin: { tag: "civora.buyer_360", params: { buyerId: this.buyerId }, label: "Acquéreur" },
            },
            target: "current",
        });
    }

    get buyer() {
        return this.state.buyer || {};
    }
    get buyerType() {
        return this.buyer.is_company ? "Société" : "Particulier";
    }
    get statusInfo() {
        return STATUS_META[this.buyer.civora_status] || { label: "—", variant: "neutral" };
    }
    agentLabel() {
        return this.buyer.civora_agent_id ? this.buyer.civora_agent_id[1] : "—";
    }
    sourceLabel() {
        return this.buyer.civora_source_id ? this.buyer.civora_source_id[1] : "—";
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
    surfaceLabel(b) {
        return b.surface ? Math.round(b.surface) + " m²" : "";
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
    budgetLabel() {
        return this.buyer.civora_budget ? this.kpiMoney(this.buyer.civora_budget) : "—";
    }
    get subtitle() {
        return this.buyerType + " · budget " + this.budgetLabel();
    }
    get tabList() {
        return [
            { id: "overview", label: "Vue d'ensemble" },
            { id: "matches", label: "Biens correspondants", count: this.state.matches.length },
            { id: "financing", label: "Financement" },
            { id: "documents", label: "Documents" },
        ];
    }
}

registry.category("actions").add("civora.buyer_360", CivoraBuyer360);
