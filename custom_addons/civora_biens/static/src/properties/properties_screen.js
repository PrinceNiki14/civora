import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";
import { CivoraBadge } from "@civora_core/components/civora_kit";
import { PropertyDrawer } from "./property_drawer";
import { UnitDialog } from "./unit_dialog";
import { DuplicateUnitsDialog } from "./duplicate_units_dialog";

const STATUS_META = {
    disponible: { label: "Disponible", variant: "success" },
    loue: { label: "Loué", variant: "info" },
    saisonnier: { label: "Saisonnier", variant: "warning" },
};

// Statuts pour le panneau "Filtres"
const STATUSES = [
    { value: "tous", label: "Tous les statuts" },
    { value: "disponible", label: "Disponible" },
    { value: "loue", label: "Loué" },
    { value: "saisonnier", label: "Saisonnier" },
];

// Tri
const SORTS = [
    { value: "recent", label: "Récents", order: "id desc" },
    { value: "price-desc", label: "Prix ↓", order: "price desc, name" },
    { value: "price-asc", label: "Prix ↑", order: "price asc, name" },
    { value: "name", label: "Nom", order: "name" },
];

const FIELDS = [
    "name", "ref", "property_type_id", "status",
    "city", "neighborhood", "surface", "rooms", "bedrooms", "bathrooms",
    "price", "monthly_revenue", "yield_rate", "owner_id", "image_128",
    "is_building", "parent_id", "unit_count", "units_occupied", "occupancy_rate",
    "floor", "unit_number", "floors_count", "total_units",
];

export class CivoraPropertiesScreen extends Component {
    static template = "civora_biens.Properties";
    static components = { CivoraStatCard, CivoraBadge, PropertyDrawer, UnitDialog, DuplicateUnitsDialog };
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.statuses = STATUSES;
        this.sorts = SORTS;

        this.types = [];
        this.cities = [];

        this.state = useState({
            loading: true,
            properties: [],
            stats: { total: 0, occupancy: 0, value: 0, revenue: 0 },
            view: "grid",
            // filtres principaux (barre)
            typeFilter: "tous",
            search: "",
            sortBy: "recent",
            // panneau filtres avance
            showFilters: false,
            statusFilter: "tous",
            cityFilter: "toutes",
            bedsMin: 0,
            areaMin: 0,
            // modale bien
            drawer: { open: false, mode: "create", propertyId: false },
            // regroupement immeubles
            unitsByBuilding: {},      // { [buildingId]: [unit, ...] }
            expanded: {},             // { [buildingId]: bool }
            // modales unite / duplication
            unitDialog: { open: false, building: null },
            dupDialog: { open: false, building: null, units: [] },
        });

        onWillStart(async () => {
            await this.loadRefData();
            await this.load();
        });
    }

    // --- Getters -------------------------------------------------------
    get typeFilters() {
        return [{ id: "tous", label: "Tous" }, ...this.types.map((t) => ({ id: t.id, label: t.name }))];
    }
    get activeFilterCount() {
        let n = 0;
        if (this.state.statusFilter !== "tous") n++;
        if (this.state.cityFilter !== "toutes") n++;
        if (this.state.bedsMin > 0) n++;
        if (this.state.areaMin > 0) n++;
        return n;
    }
    get currentOrder() {
        const s = SORTS.find((x) => x.value === this.state.sortBy);
        return s ? s.order : "id desc";
    }
    get domain() {
        const dom = [];
        if (this.state.typeFilter !== "tous") {
            dom.push(["property_type_id", "=", Number(this.state.typeFilter)]);
        }
        if (this.state.statusFilter !== "tous") {
            dom.push(["status", "=", this.state.statusFilter]);
        }
        if (this.state.cityFilter !== "toutes") {
            dom.push(["city", "=", this.state.cityFilter]);
        }
        if (this.state.bedsMin > 0) {
            dom.push(["bedrooms", ">=", this.state.bedsMin]);
        }
        if (this.state.areaMin > 0) {
            dom.push(["surface", ">=", this.state.areaMin]);
        }
        const q = (this.state.search || "").trim();
        if (q) {
            dom.push("|", "|", "|",
                ["name", "ilike", q], ["ref", "ilike", q],
                ["city", "ilike", q], ["neighborhood", "ilike", q]);
        }
        return dom;
    }

    // --- Chargement ----------------------------------------------------
    async loadRefData() {
        this.types = await this.orm.searchRead(
            "civora.property.type", [], ["name"], { order: "sequence, name" }
        );
        try {
            const groups = await this.orm.formattedReadGroup("civora.property", [], ["city"], []);
            this.cities = groups.map((g) => g.city).filter(Boolean).sort();
        } catch {
            this.cities = [];
        }
    }

    async load() {
        this.state.loading = true;

        const total = await this.orm.searchCount("civora.property", []);
        const occupied = await this.orm.searchCount(
            "civora.property", [["status", "in", ["loue", "saisonnier"]]]
        );
        let value = 0;
        let revenue = 0;
        try {
            const g = await this.orm.formattedReadGroup(
                "civora.property", [], [], ["price:sum", "monthly_revenue:sum"]
            );
            if (g.length) {
                value = g[0]["price:sum"] || 0;
                revenue = g[0]["monthly_revenue:sum"] || 0;
            }
        } catch {
            value = 0;
            revenue = 0;
        }
        this.state.stats = {
            total,
            occupancy: total ? Math.round((occupied / total) * 100) : 0,
            value,
            revenue,
        };

        // Flux principal. Hors recherche/filtres, on masque les unites au niveau
        // racine (elles apparaissent regroupees sous leur immeuble). En recherche
        // ou filtre actif, on les montre a plat pour ne rien cacher a l'utilisateur.
        const grouping = !this.hasActiveQuery;
        const rootDomain = grouping ? [...this.domain, ["parent_id", "=", false]] : this.domain;

        const rows = await this.orm.searchRead(
            "civora.property", rootDomain, FIELDS, { limit: 200, order: this.currentOrder }
        );
        this.state.properties = rows;

        // Charge les unites des immeubles presents dans le flux (mode groupe).
        const map = {};
        if (grouping) {
            const buildingIds = rows.filter((p) => p.is_building).map((p) => p.id);
            if (buildingIds.length) {
                const units = await this.orm.searchRead(
                    "civora.property",
                    [["parent_id", "in", buildingIds]],
                    FIELDS,
                    { order: "floor, unit_number, name" }
                );
                for (const u of units) {
                    const pid = u.parent_id ? u.parent_id[0] : false;
                    if (!pid) continue;
                    (map[pid] = map[pid] || []).push(u);
                }
            }
        }
        this.state.unitsByBuilding = map;
        this.state.loading = false;
    }

    get hasActiveQuery() {
        return (
            !!(this.state.search || "").trim() ||
            this.state.typeFilter !== "tous" ||
            this.state.statusFilter !== "tous" ||
            this.state.cityFilter !== "toutes" ||
            this.state.bedsMin > 0 ||
            this.state.areaMin > 0
        );
    }
    unitsOf(p) {
        return this.state.unitsByBuilding[p.id] || [];
    }
    isExpanded(p) {
        return !!this.state.expanded[p.id];
    }
    toggleExpand(p) {
        this.state.expanded = { ...this.state.expanded, [p.id]: !this.state.expanded[p.id] };
    }
    buildingOccupancyLabel(p) {
        const units = this.unitsOf(p);
        if (!units.length) return "0 unité";
        const occ = units.filter((u) => u.status === "loue" || u.status === "saisonnier").length;
        return `${units.length} unité(s) · ${occ}/${units.length} occupée(s)`;
    }
    unitLabel(u) {
        return u.unit_number ? "N° " + u.unit_number : (u.name || "").slice(0, 18);
    }

    // --- Helpers d'affichage ------------------------------------------
    statusMeta(p) {
        return STATUS_META[p.status] || { label: "—", variant: "neutral" };
    }
    typeLabel(p) {
        return p.property_type_id ? p.property_type_id[1] : "—";
    }
    ownerLabel(p) {
        return p.owner_id ? p.owner_id[1] : "—";
    }
    locLabel(p) {
        return [p.neighborhood, p.city].filter(Boolean).join(", ") || "—";
    }
    surfaceLabel(p) {
        return p.surface ? Math.round(p.surface) + " m²" : "";
    }
    yieldLabel(p) {
        const y = p.yield_rate || 0;
        return y ? y.toFixed(1).replace(".", ",") + " %" : "—";
    }
    fmtMoney(n) {
        n = Number(n || 0);
        if (n >= 1e9) return (n / 1e9).toFixed(1).replace(".", ",") + " Md";
        if (n >= 1e6) return (n / 1e6).toFixed(n % 1e6 ? 1 : 0).replace(".", ",") + " M";
        if (n >= 1e3) return Math.round(n / 1e3) + " k";
        return "" + n;
    }
    kpiValue(n) {
        return this.fmtMoney(n) + " FCFA";
    }

    // --- Filtres / vue -------------------------------------------------
    setView(v) {
        this.state.view = v;
    }
    async setType(id) {
        this.state.typeFilter = id;
        await this.load();
    }
    async setSort(ev) {
        this.state.sortBy = ev.target.value;
        await this.load();
    }
    toggleFilters() {
        this.state.showFilters = !this.state.showFilters;
    }
    async onStatusChange(ev) {
        this.state.statusFilter = ev.target.value;
        await this.load();
    }
    async onCityChange(ev) {
        this.state.cityFilter = ev.target.value;
        await this.load();
    }
    async onBedsChange(ev) {
        this.state.bedsMin = ev.target.value === "" ? 0 : Number(ev.target.value);
        await this.load();
    }
    async onAreaChange(ev) {
        this.state.areaMin = ev.target.value === "" ? 0 : Number(ev.target.value);
        await this.load();
    }
    async resetFilters() {
        this.state.statusFilter = "tous";
        this.state.cityFilter = "toutes";
        this.state.bedsMin = 0;
        this.state.areaMin = 0;
        await this.load();
    }
    async onSearchInput(ev) {
        this.state.search = ev.target.value;
        await this.load();
    }

    // --- Navigation / creation / edition ------------------------------
    openProperty(p) {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.property_360",
            params: { propertyId: p.id },
            target: "current",
        });
    }
    openCreate() {
        this.state.drawer = { open: true, mode: "create", propertyId: false };
    }
    openEdit(p) {
        this.state.drawer = { open: true, mode: "edit", propertyId: p.id };
    }
    closeDrawer() {
        this.state.drawer = { ...this.state.drawer, open: false };
    }
    async onDrawerSaved() {
        this.closeDrawer();
        await this.loadRefData();
        await this.load();
    }

    // --- Immeuble : ajout d'unite / duplication ------------------------
    openAddUnit(building) {
        this.state.unitDialog = { open: true, building };
    }
    closeAddUnit() {
        this.state.unitDialog = { open: false, building: null };
    }
    async onUnitSaved() {
        const b = this.state.unitDialog.building;
        this.closeAddUnit();
        await this.load();
        if (b) {
            this.state.expanded = { ...this.state.expanded, [b.id]: true };
        }
    }
    openDuplicate(building) {
        this.state.dupDialog = {
            open: true,
            building,
            units: this.unitsOf(building),
        };
    }
    closeDuplicate() {
        this.state.dupDialog = { open: false, building: null, units: [] };
    }
    async onDuplicateSaved() {
        const b = this.state.dupDialog.building;
        this.closeDuplicate();
        await this.load();
        if (b) {
            this.state.expanded = { ...this.state.expanded, [b.id]: true };
        }
    }
}

registry.category("actions").add("civora.properties", CivoraPropertiesScreen);
