import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";
import { CivoraAvatar, CivoraBadge, CivoraProgress } from "@civora_core/components/civora_kit";
import { LeaseDrawer } from "./lease_drawer";
import { ArrearsView } from "@civora_locations/arrears/arrears_view";

const STATUS_META = {
    actif: { label: "Actif", variant: "success" },
    retard: { label: "Retard", variant: "danger" },
    expire_bientot: { label: "Expire bientôt", variant: "warning" },
    resilie: { label: "Résilié", variant: "neutral" },
};
const TYPE_LABEL = {
    residentiel: "Résidentiel",
    commercial: "Commercial",
};
const LEASE_FIELDS = [
    "name", "property_id", "tenant_id", "owner_id", "agent_id", "property_city",
    "rent", "charges", "deposit",
    "date_start", "date_end", "payday", "lease_type", "status", "payment_rate",
    "total_monthly", "arrears_amount",
];

/**
 * Ecran Locations : KPIs globaux + liste des baux filtrable.
 * Onglets Encaissements / Impayés / Renouvellements / Quittances / Maintenance
 * a venir dans un increment suivant (places en "soon" pour respecter l'UX du
 * front de reference).
 */
export class CivoraLeasesScreen extends Component {
    static template = "civora_locations.Leases";
    static components = { CivoraStatCard, CivoraAvatar, CivoraBadge, CivoraProgress, LeaseDrawer, ArrearsView };
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.statusMetaDef = STATUS_META;

        this.state = useState({
            loading: true,
            view: "leases",
            search: "",
            statusFilter: "all",
            typeFilter: "all",
            agentFilter: "all",
            ownerFilter: "all",
            cityFilter: "all",
            leases: [],
            stats: {
                activeCount: 0, totalRent: 0, collected: 0, collectionRate: 0,
                arrearsCount: 0, arrearsAmount: 0, expiringCount: 0,
            },
            drawer: { open: false, mode: "create", leaseId: false },
            receipts: [],
            receiptsLoaded: false,
        });
        onWillStart(() => this.load());
    }

    async setView(v) {
        this.state.view = v;
        if (v === "receipts" && !this.state.receiptsLoaded) {
            await this.loadReceipts();
        }
    }
    async loadReceipts() {
        this.state.receipts = await this.orm.searchRead(
            "civora.lease.receipt", [],
            ["name", "period_label", "amount_total", "date_issued", "tenant_id", "property_id", "payment_id"],
            { order: "date_issued desc, id desc", limit: 500 }
        );
        this.state.receiptsLoaded = true;
    }
    async printReceipt(receiptId) {
        await this.action.doAction({
            type: "ir.actions.report",
            report_name: "civora_locations.report_lease_receipt",
            report_type: "qweb-pdf",
            context: { active_ids: [receiptId], active_model: "civora.lease.receipt" },
        });
    }

    async load() {
        this.state.loading = true;
        const rows = await this.orm.searchRead("civora.lease", [], LEASE_FIELDS, { order: "date_start desc" });

        let totalRent = 0, collected = 0, arrearsCount = 0, arrearsAmount = 0, expiringCount = 0, activeCount = 0;
        const leases = rows.map((r) => {
            const monthly = r.total_monthly || 0;
            totalRent += monthly;
            collected += monthly * ((r.payment_rate || 0) / 100);
            if (r.status === "retard") { arrearsCount += 1; arrearsAmount += r.arrears_amount || 0; }
            if (r.status === "expire_bientot") expiringCount += 1;
            if (r.status !== "resilie") activeCount += 1;
            return {
                id: r.id,
                ref: r.name,
                propertyId: r.property_id ? r.property_id[0] : false,
                propertyName: r.property_id ? r.property_id[1] : "—",
                tenantId: r.tenant_id ? r.tenant_id[0] : false,
                tenantName: r.tenant_id ? r.tenant_id[1] : "—",
                ownerId: r.owner_id ? r.owner_id[0] : false,
                ownerName: r.owner_id ? r.owner_id[1] : "—",
                agentId: r.agent_id ? r.agent_id[0] : false,
                agentName: r.agent_id ? r.agent_id[1] : "—",
                city: r.property_city || "",
                rent: r.rent || 0,
                charges: r.charges || 0,
                deposit: r.deposit || 0,
                dateStart: r.date_start,
                dateEnd: r.date_end,
                payday: r.payday,
                leaseType: r.lease_type,
                status: r.status,
                paymentRate: r.payment_rate || 0,
            };
        });

        this.allLeases = leases;
        this.state.stats = {
            activeCount, totalRent, collected,
            collectionRate: totalRent ? Math.round((collected / totalRent) * 100) : 0,
            arrearsCount, arrearsAmount, expiringCount,
        };
        this.applyFilter();
        this.state.loading = false;
    }

    // --- Vue / filtres -------------------------------------------------
    get tabList() {
        return [
            { id: "leases", label: "Baux", count: this.allLeases ? this.allLeases.length : 0 },
            { id: "payments", label: "Encaissements" },
            { id: "arrears", label: "Impayés", count: this.state.stats.arrearsCount },
            { id: "renewals", label: "Renouvellements", count: this.state.stats.expiringCount },
            { id: "receipts", label: "Quittances" },
            { id: "maintenance", label: "Maintenance" },
        ];
    }

    // Listes dédupliquées pour les <select> de filtres
    get agentOptions() {
        const seen = new Map();
        for (const l of (this.allLeases || [])) {
            if (l.agentId && !seen.has(l.agentId)) {
                seen.set(l.agentId, l.agentName);
            }
        }
        return Array.from(seen.entries()).map(([id, name]) => ({ id, name }));
    }
    get ownerOptions() {
        const seen = new Map();
        for (const l of (this.allLeases || [])) {
            if (l.ownerId && !seen.has(l.ownerId)) {
                seen.set(l.ownerId, l.ownerName);
            }
        }
        return Array.from(seen.entries()).map(([id, name]) => ({ id, name }));
    }
    get cityOptions() {
        const seen = new Set();
        const result = [];
        for (const l of (this.allLeases || [])) {
            if (l.city && !seen.has(l.city)) {
                seen.add(l.city);
                result.push(l.city);
            }
        }
        return result.sort();
    }

    setStatusFilter(v) {
        this.state.statusFilter = v;
        this.applyFilter();
    }
    setTypeFilter(v) {
        this.state.typeFilter = v;
        this.applyFilter();
    }
    onAgentFilter(ev) {
        this.state.agentFilter = ev.target.value;
        this.applyFilter();
    }
    onOwnerFilter(ev) {
        this.state.ownerFilter = ev.target.value;
        this.applyFilter();
    }
    onCityFilter(ev) {
        this.state.cityFilter = ev.target.value;
        this.applyFilter();
    }
    onSearchInput(ev) {
        this.state.search = ev.target.value;
        this.applyFilter();
    }
    get statusTabs() {
        const all = this.allLeases || [];
        return [
            { id: "all", label: "Tous", count: all.length },
            { id: "actif", label: "Actifs", count: all.filter((l) => l.status === "actif").length },
            { id: "retard", label: "En retard", count: all.filter((l) => l.status === "retard").length },
            { id: "expire_bientot", label: "Expire <60j", count: all.filter((l) => l.status === "expire_bientot").length },
        ];
    }
    applyFilter() {
        const q = (this.state.search || "").trim().toLowerCase();
        const status = this.state.statusFilter;
        const type = this.state.typeFilter;
        const agentF = this.state.agentFilter;
        const ownerF = this.state.ownerFilter;
        const cityF = this.state.cityFilter;
        this.state.leases = (this.allLeases || []).filter((l) => {
            if (status !== "all" && l.status !== status) return false;
            if (type !== "all" && l.leaseType !== type) return false;
            if (agentF !== "all" && (l.agentId + "") !== agentF) return false;
            if (ownerF !== "all" && (l.ownerId + "") !== ownerF) return false;
            if (cityF !== "all" && l.city !== cityF) return false;
            if (!q) return true;
            return (
                (l.tenantName || "").toLowerCase().includes(q) ||
                (l.propertyName || "").toLowerCase().includes(q) ||
                (l.ref || "").toLowerCase().includes(q) ||
                (l.agentName || "").toLowerCase().includes(q) ||
                (l.ownerName || "").toLowerCase().includes(q) ||
                (l.city || "").toLowerCase().includes(q)
            );
        });
    }

    // --- Helpers -------------------------------------------------------
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
    fmtDate(d) {
        if (!d) return "—";
        const [y, m, day] = String(d).split("-");
        return day && m && y ? `${day}/${m}/${y}` : d;
    }
    statusMeta(l) {
        return STATUS_META[l.status] || { label: "—", variant: "neutral" };
    }
    typeLabel(l) {
        return TYPE_LABEL[l.leaseType] || "—";
    }
    rateTone(rate) {
        return rate >= 95 ? "accent" : rate >= 80 ? "warning" : "danger";
    }

    openLease(l) {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.lease_360",
            params: { leaseId: l.id },
            target: "current",
        });
    }

    // --- Drawer (creation / edition) -----------------------------------
    openCreateDrawer() {
        this.state.drawer = { open: true, mode: "create", leaseId: false };
    }
    closeDrawer() {
        this.state.drawer = { open: false, mode: "create", leaseId: false };
    }
    async onDrawerSaved() {
        this.closeDrawer();
        await this.load();
    }
}

registry.category("actions").add("civora.leases", CivoraLeasesScreen);
