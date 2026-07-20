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
    "name", "ref", "city", "neighborhood", "status", "transaction",
    "price", "monthly_revenue", "yield_rate", "property_type_id", "image_128",
];

export class CivoraOwner360 extends Component {
    static template = "civora_gestion.Owner360";
    static components = { CivoraStatCard, CivoraAvatar, CivoraBadge };
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        const params = (this.props.action && this.props.action.params) || {};
        this.ownerId = Number(params.ownerId) || false;

        this.state = useState({
            loading: true,
            error: "",
            owner: null,
            biens: [],
            activeTab: "overview",
            stats: { count: 0, value: 0, mrr: 0, yield: 0, occupancy: 0, loue: 0, saisonnier: 0, dispo: 0 },
            segment: "",
        });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        if (!this.ownerId) {
            this.state.error = "Propriétaire introuvable.";
            this.state.loading = false;
            return;
        }
        try {
            const [p] = await this.orm.read(
                "res.partner", [this.ownerId],
                ["name", "email", "phone", "civora_whatsapp", "city", "civora_ai_score", "civora_segment_ids", "create_date"]
            );
            if (!p) {
                this.state.error = "Propriétaire introuvable.";
                this.state.loading = false;
                return;
            }
            this.state.owner = p;
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
                "civora.property", [["owner_id", "=", this.ownerId]], BIEN_FIELDS, { order: "price desc, name" }
            );
            this.computeStats();
        } catch (e) {
            this.state.error = "Impossible de charger le propriétaire.";
        }
        this.state.loading = false;
    }

    computeStats() {
        let value = 0, mrr = 0, loue = 0, saisonnier = 0, dispo = 0;
        for (const b of this.state.biens) {
            value += b.price || 0;
            mrr += b.monthly_revenue || 0;
            if (b.status === "loue") loue++;
            else if (b.status === "saisonnier") saisonnier++;
            else dispo++;
        }
        const count = this.state.biens.length;
        const occupied = loue + saisonnier;
        this.state.stats = {
            count,
            value,
            mrr,
            yield: value ? (mrr * 12 / value * 100) : 0,
            occupancy: count ? Math.round((occupied / count) * 100) : 0,
            loue,
            saisonnier,
            dispo,
        };
    }

    // --- Navigation ----------------------------------------------------
    goBack() {
        this.action.doAction({ type: "ir.actions.client", tag: "civora.owners", target: "current" });
    }
    setTab(id) {
        this.state.activeTab = id;
    }
    openContact() {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.contact_360",
            params: {
                contactId: this.ownerId,
                origin: { tag: "civora.owner_360", params: { ownerId: this.ownerId }, label: "Propriétaire" },
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
                origin: { tag: "civora.owner_360", params: { ownerId: this.ownerId }, label: "Propriétaire" },
            },
            target: "current",
        });
    }

    // --- Helpers -------------------------------------------------------
    get owner() {
        return this.state.owner || {};
    }
    statusMeta(b) {
        return STATUS_META[b.status] || { label: "—", variant: "neutral" };
    }
    typeLabel(b) {
        return b.property_type_id ? b.property_type_id[1] : "—";
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
    yieldLabel() {
        const y = this.state.stats.yield || 0;
        return y ? y.toFixed(1).replace(".", ",") + " %" : "—";
    }
    get subtitle() {
        const s = this.state.stats;
        const parts = [s.count + " bien" + (s.count > 1 ? "s" : "")];
        if (s.loue) parts.push(s.loue + " loué" + (s.loue > 1 ? "s" : ""));
        if (s.saisonnier) parts.push(s.saisonnier + " saisonnier" + (s.saisonnier > 1 ? "s" : ""));
        return parts.join(" · ");
    }
    get tabList() {
        return [
            { id: "overview", label: "Vue d'ensemble" },
            { id: "biens", label: "Biens en mandat", count: this.state.stats.count },
            { id: "finance", label: "Reversements" },
            { id: "documents", label: "Documents" },
        ];
    }
}

registry.category("actions").add("civora.owner_360", CivoraOwner360);
