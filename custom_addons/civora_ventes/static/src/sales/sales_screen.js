/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";
import { SaleDrawer } from "./sale_drawer";

function fmtMoney(v) {
    if (!v && v !== 0) return "0";
    return Number(v).toLocaleString("fr-FR");
}

const STATE_LABELS = {
    mandat: "Mandat",
    commercialisation: "Commercialisation",
    offre: "Offre",
    compromis: "Compromis",
    acte: "Acte",
    cloture: "Cloture",
    annule: "Annule",
};

const MANDATE_LABELS = {
    exclusif: "Exclusif",
    simple: "Simple",
    delegue: "Delegue",
};

class CivoraVentesScreen extends Component {
    static template = "civora_ventes.SalesScreen";
    static components = { CivoraStatCard, SaleDrawer };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            sales: [],
            kpis: {},
            filter: "all",
            search: "",
            drawerOpen: false,
            drawerMode: "create",
            drawerRecordId: null,
        });
        onWillStart(() => this.load());
    }

    async load() {
        const [kpis, sales] = await Promise.all([
            this.orm.call("civora.sale", "get_sales_kpis", []),
            this.orm.searchRead("civora.sale", [], [
                "name", "property_id", "seller_id", "buyer_id", "agent_id",
                "state", "mandate_type", "mandate_date", "asking_price",
                "sale_amount", "commission_amount", "offer_count",
                "compromis_date", "acte_date",
            ], { order: "create_date desc", limit: 200 }),
        ]);
        this.state.kpis = kpis;
        this.state.sales = sales;
    }

    get filteredSales() {
        let list = this.state.sales;
        const f = this.state.filter;
        if (f === "mandats") list = list.filter(r => r.state === "mandat" || r.state === "commercialisation");
        else if (f === "offres") list = list.filter(r => r.state === "offre");
        else if (f === "compromis") list = list.filter(r => r.state === "compromis");
        else if (f === "acte") list = list.filter(r => r.state === "acte");
        else if (f === "cloture") list = list.filter(r => r.state === "cloture");
        else if (f === "annule") list = list.filter(r => r.state === "annule");
        if (this.state.search) {
            const q = this.state.search.toLowerCase();
            list = list.filter(r =>
                (r.property_id && r.property_id[1] || "").toLowerCase().includes(q) ||
                (r.seller_id && r.seller_id[1] || "").toLowerCase().includes(q) ||
                (r.buyer_id && r.buyer_id[1] || "").toLowerCase().includes(q) ||
                (r.name || "").toLowerCase().includes(q)
            );
        }
        return list;
    }

    setFilter(f) { this.state.filter = f; }
    onSearch(ev) { this.state.search = ev.target.value; }

    stateLabel(s) { return STATE_LABELS[s] || s; }
    stateClass(s) {
        const m = {
            mandat: "muted",
            commercialisation: "info",
            offre: "warning",
            compromis: "violet",
            acte: "primary",
            cloture: "success",
            annule: "danger",
        };
        return m[s] || "";
    }
    mandateLabel(s) { return MANDATE_LABELS[s] || s; }
    fmtMoney(v) { return fmtMoney(v); }

    openDrawer(mode, id) {
        this.state.drawerMode = mode || "create";
        this.state.drawerRecordId = id || null;
        this.state.drawerOpen = true;
    }

    closeDrawer() { this.state.drawerOpen = false; }

    async onSaved() {
        this.state.drawerOpen = false;
        await this.load();
    }

    openDetail(id) {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.sale_360",
            params: { sale_id: id },
        });
    }
}

registry.category("actions").add("civora.ventes", CivoraVentesScreen);
