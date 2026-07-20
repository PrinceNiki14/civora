import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { user } from "@web/core/user";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";
import { CivoraBadge } from "@civora_core/components/civora_kit";
import { PropertyDrawer } from "./property_drawer";

const STATUS_META = {
    disponible: { label: "Disponible", variant: "success" },
    loue: { label: "Loué", variant: "info" },
    saisonnier: { label: "Saisonnier", variant: "warning" },
};

const FIELDS = [
    "name", "ref", "property_type_id", "transaction", "mandate_type", "status",
    "city", "neighborhood", "street", "latitude", "longitude",
    "surface", "rooms", "bedrooms", "bathrooms", "year_built",
    "price", "monthly_revenue", "yield_rate",
    "owner_id", "agent_id", "tenant_id", "description", "note",
    "rental_deposit", "rental_charges", "rental_min_stay", "rental_advance", "rental_agency_fees",
    "sale_negotiable", "sale_notary", "sale_payment", "sale_handover",
    "is_building", "floors_count", "total_units", "parent_id", "floor", "unit_number",
];

const TRANSACTION_LABEL = { vente: "À vendre", location: "À louer", saisonnier: "Location saisonnière" };
const MANDATE_LABEL = { exclusif: "Exclusif", simple: "Simple", delegue: "Délégué" };

const VR_STATE = {
    new: { label: "Nouvelle", variant: "info" },
    contacted: { label: "Contacté", variant: "warning" },
    scheduled: { label: "Planifiée", variant: "success" },
    done: { label: "Réalisée", variant: "neutral" },
    cancelled: { label: "Annulée", variant: "danger" },
};

export class CivoraProperty360 extends Component {
    static template = "civora_biens.Property360";
    static components = { CivoraStatCard, CivoraBadge, PropertyDrawer };
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        const params = (this.props.action && this.props.action.params) || {};
        this.propertyId = Number(params.propertyId) || false;
        this.origin = params.origin || null;
        this.contribTabs = registry
            .category("civora_property_360_tab")
            .getAll()
            .slice()
            .sort((a, b) => (a.sequence || 100) - (b.sequence || 100));

        this.state = useState({
            loading: true,
            error: "",
            record: null,
            images: [],           // [{id}]
            activeImageId: false,
            activeTab: "overview",
            edit: { open: false },
            share: { loading: true, is_shared: false, url: "", copied: false },
            requests: [],
            units: [],
        });

        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        this.state.error = "";
        if (!this.propertyId) {
            this.state.error = "Bien introuvable.";
            this.state.loading = false;
            return;
        }
        try {
            const [rec] = await this.orm.read("civora.property", [this.propertyId], FIELDS);
            if (!rec) {
                this.state.error = "Bien introuvable.";
                this.state.loading = false;
                return;
            }
            this.state.record = rec;
            const imgs = await this.orm.searchRead(
                "civora.property.image", [["property_id", "=", this.propertyId]], ["name"], { order: "sequence, id" }
            );
            this.state.images = imgs.map((i) => ({ id: i.id }));
            this.state.activeImageId = imgs.length ? imgs[0].id : false;
            this.state.requests = await this.orm.searchRead(
                "civora.visit.request", [["property_id", "=", this.propertyId]],
                ["name", "phone", "email", "message", "state", "create_date", "assigned_user_id"],
                { order: "create_date desc" }
            );
            await this.loadShare();
            this.state.units = rec.is_building
                ? await this.orm.searchRead(
                    "civora.property", [["parent_id", "=", this.propertyId]],
                    ["name", "ref", "status", "unit_number", "floor", "price",
                     "monthly_revenue", "bedrooms", "bathrooms", "surface", "image_128"],
                    { order: "floor, unit_number, name" })
                : [];
        } catch (e) {
            this.state.error = "Impossible de charger le bien.";
        }
        this.state.loading = false;
    }

    async loadShare() {
        this.state.share.loading = true;
        try {
            const info = await this.orm.call("civora.property", "share_get", [this.propertyId]);
            this.state.share.is_shared = !!info.is_shared;
            this.state.share.url = info.url || "";
        } catch (e) {
            this.state.share.is_shared = false;
            this.state.share.url = "";
        }
        this.state.share.loading = false;
    }
    async toggleShare() {
        const enable = !this.state.share.is_shared;
        const info = await this.orm.call("civora.property", "share_set", [this.propertyId, enable]);
        this.state.share.is_shared = !!info.is_shared;
        this.state.share.url = info.url || "";
        this.state.share.copied = false;
    }
    async copyShareLink() {
        if (!this.state.share.url) {
            return;
        }
        try {
            await navigator.clipboard.writeText(this.state.share.url);
            this.state.share.copied = true;
            setTimeout(() => (this.state.share.copied = false), 2000);
        } catch (e) {
            // clipboard indisponible : on laisse l'utilisateur copier manuellement
        }
    }
    openPublic() {
        if (this.state.share.url) {
            window.open(this.state.share.url, "_blank");
        }
    }

    // --- Navigation / actions -----------------------------------------
    goBack() {
        if (this.origin && this.origin.tag) {
            this.action.doAction({
                type: "ir.actions.client",
                tag: this.origin.tag,
                params: this.origin.params || {},
                target: "current",
            });
        } else {
            this.action.doAction({ type: "ir.actions.client", tag: "civora.properties", target: "current" });
        }
    }
    get backLabel() {
        return this.origin && this.origin.label ? this.origin.label : "Biens";
    }
    setTab(id) {
        this.state.activeTab = id;
    }
    setImage(id) {
        this.state.activeImageId = id;
    }
    openEdit() {
        this.state.edit = { open: true };
    }
    closeEdit() {
        this.state.edit = { open: false };
    }
    async onEditSaved() {
        this.state.edit = { open: false };
        await this.load();
    }

    // --- Helpers -------------------------------------------------------
    get record() {
        return this.state.record || {};
    }
    get statusInfo() {
        return STATUS_META[this.record.status] || { label: "—", variant: "neutral" };
    }
    get mainImageSrc() {
        return this.state.activeImageId
            ? "/web/image/civora.property.image/" + this.state.activeImageId + "/image_512"
            : false;
    }
    thumbSrc(id) {
        return "/web/image/civora.property.image/" + id + "/image_128";
    }
    typeLabel() {
        return this.record.property_type_id ? this.record.property_type_id[1] : "—";
    }
    ownerLabel() {
        return this.record.owner_id ? this.record.owner_id[1] : "—";
    }
    agentLabel() {
        return this.record.agent_id ? this.record.agent_id[1] : "—";
    }
    tenantLabel() {
        return this.record.tenant_id ? this.record.tenant_id[1] : "—";
    }
    transactionLabel() {
        return TRANSACTION_LABEL[this.record.transaction] || "—";
    }
    mandateLabel() {
        return MANDATE_LABEL[this.record.mandate_type] || "—";
    }
    get rentalConditions() {
        const r = this.record;
        return [
            { label: "Caution", value: r.rental_deposit },
            { label: "Avance", value: r.rental_advance },
            { label: "Charges", value: r.rental_charges },
            { label: "Durée min.", value: r.rental_min_stay },
            { label: "Frais d'agence", value: r.rental_agency_fees },
        ].filter((x) => x.value);
    }
    get saleConditions() {
        const r = this.record;
        return [
            { label: "Négociation", value: r.sale_negotiable },
            { label: "Paiement", value: r.sale_payment },
            { label: "Notaire", value: r.sale_notary },
            { label: "Remise des clés", value: r.sale_handover },
        ].filter((x) => x.value);
    }
    unitStatus(u) {
        return STATUS_META[u.status] || { label: "—", variant: "neutral" };
    }
    get isBuilding() {
        return !!(this.state.record && this.state.record.is_building);
    }
    // Statistiques consolidees de l'immeuble a partir des unites chargees.
    get buildingStats() {
        const units = this.state.units || [];
        const rec = this.state.record || {};
        const total = units.length;
        const rented = units.filter((u) => u.status === "loue").length;
        const seasonal = units.filter((u) => u.status === "saisonnier").length;
        const occupied = rented + seasonal;
        const available = units.filter((u) => u.status === "disponible").length;
        const monthlyRevenue = units.reduce((s, u) => s + (u.monthly_revenue || 0), 0);
        const portfolioValue = units.reduce((s, u) => s + (u.price || 0), 0);
        const planned = rec.total_units || total;
        return {
            total,
            planned,
            rented,
            seasonal,
            occupied,
            available,
            occupancy: total ? Math.round((occupied / total) * 100) : 0,
            monthlyRevenue,
            portfolioValue,
        };
    }
    unitThumb(u) {
        return u.image_128
            ? "/web/image/civora.property/" + u.id + "/image_512"
            : false;
    }
    unitPriceLabel(u) {
        if (u.status === "loue" || u.status === "saisonnier" || u.monthly_revenue) {
            return u.monthly_revenue ? this.fmtMoney(u.monthly_revenue) + " /mois" : "—";
        }
        return u.price ? this.kpiMoney(u.price) : "—";
    }
    unitAptLabel(u) {
        return u.unit_number ? "Apt " + u.unit_number : (u.name || "").slice(0, 16);
    }
    unitSurface(u) {
        return u.surface ? Math.round(u.surface) + " m²" : "";
    }
    openUnit(u) {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.property_360",
            params: {
                propertyId: u.id,
                origin: { tag: "civora.property_360", params: { propertyId: this.propertyId }, label: "Immeuble" },
            },
            target: "current",
        });
    }
    reqState(s) {
        return VR_STATE[s] || { label: s || "—", variant: "neutral" };
    }
    reqDate(v) {
        if (!v) return "";
        const [d, t] = String(v).split(" ");
        if (!d) return v;
        const [Y, M, D] = d.split("-");
        return D + "/" + M + "/" + Y + (t ? " · " + t.slice(0, 5) : "");
    }
    assignedLabel(r) {
        return r.assigned_user_id ? r.assigned_user_id[1] : "";
    }
    isMine(r) {
        return r.assigned_user_id && r.assigned_user_id[0] === user.userId;
    }
    async reloadRequests() {
        this.state.requests = await this.orm.searchRead(
            "civora.visit.request", [["property_id", "=", this.propertyId]],
            ["name", "phone", "email", "message", "state", "create_date", "assigned_user_id"],
            { order: "create_date desc" }
        );
    }
    async takeRequest(r) {
        const vals = { assigned_user_id: user.userId };
        if (r.state === "new") {
            vals.state = "contacted";
        }
        await this.orm.write("civora.visit.request", [r.id], vals);
        await this.reloadRequests();
    }
    async releaseRequest(r) {
        await this.orm.write("civora.visit.request", [r.id], { assigned_user_id: false });
        await this.reloadRequests();
    }
    async setRequestState(r, ev) {
        await this.orm.write("civora.visit.request", [r.id], { state: ev.target.value });
        await this.reloadRequests();
    }
    get requestStates() {
        return [
            { value: "new", label: "Nouvelle" },
            { value: "contacted", label: "Contacté" },
            { value: "scheduled", label: "Visite planifiée" },
            { value: "done", label: "Réalisée" },
            { value: "cancelled", label: "Annulée" },
        ];
    }
    locLabel() {
        return [this.record.neighborhood, this.record.city].filter(Boolean).join(", ") || "—";
    }
    orDash(v) {
        return v || "—";
    }
    numOr(v, suffix) {
        return v ? v + (suffix || "") : "—";
    }
    yieldLabel() {
        const y = this.record.yield_rate || 0;
        return y ? y.toFixed(1).replace(".", ",") + " %" : "—";
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
    get tabList() {
        return [
            { id: "overview", label: "Aperçu" },
            { id: "photos", label: "Photos", count: this.state.images.length },
            { id: "visits", label: "Demandes", count: this.state.requests.length },
            ...this.contribTabs.map((t) => ({ id: t.id, label: t.label })),
            { id: "occupancy", label: "Occupation" },
            { id: "finance", label: "Finance" },
            { id: "documents", label: "Documents" },
        ];
    }
    get activeContrib() {
        return this.contribTabs.find((t) => t.id === this.state.activeTab) || null;
    }
}

registry.category("actions").add("civora.property_360", CivoraProperty360);
