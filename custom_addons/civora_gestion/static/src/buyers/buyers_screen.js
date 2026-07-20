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
const STATUS_FILTERS = [
    { id: "tous", label: "Tous" },
    { id: "chaud", label: "Chaud" },
    { id: "actif", label: "Actif" },
    { id: "qualifie", label: "Qualifié" },
    { id: "a_risque", label: "À risque" },
    { id: "inactif", label: "Inactif" },
];

export class CivoraBuyersScreen extends Component {
    static template = "civora_gestion.Buyers";
    static components = { CivoraStatCard, CivoraAvatar, CivoraBadge };
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.statusFilters = STATUS_FILTERS;
        this.saleBiens = [];
        this.state = useState({
            loading: true,
            buyers: [],
            search: "",
            statusFilter: "tous",
            stats: { count: 0, budget: 0, inventory: 0, avgScore: 0 },
        });
        onWillStart(() => this.load());
    }

    get domain() {
        const dom = [["civora_role_ids.code", "=", "acheteur"]];
        if (this.state.statusFilter !== "tous") {
            dom.push(["civora_status", "=", this.state.statusFilter]);
        }
        const q = (this.state.search || "").trim();
        if (q) dom.push(["name", "ilike", q]);
        return dom;
    }

    async load() {
        this.state.loading = true;

        // Inventaire des biens a vendre disponibles (pour le matching budget)
        this.saleBiens = await this.orm.searchRead(
            "civora.property", [["transaction", "=", "vente"], ["status", "=", "disponible"]], ["price"]
        );

        const buyers = await this.orm.searchRead(
            "res.partner", this.domain,
            ["name", "civora_budget", "civora_ai_score", "civora_status", "civora_agent_id", "create_date"],
            { limit: 200, order: "civora_ai_score desc, name" }
        );

        let budgetTot = 0;
        let scoreTot = 0;
        const rows = buyers.map((b) => {
            budgetTot += b.civora_budget || 0;
            scoreTot += b.civora_ai_score || 0;
            const matches = b.civora_budget
                ? this.saleBiens.filter((s) => (s.price || 0) <= b.civora_budget).length
                : null;
            return {
                id: b.id,
                name: b.name,
                budget: b.civora_budget || 0,
                matches,
                score: b.civora_ai_score || 0,
                status: b.civora_status || "",
                agent: b.civora_agent_id ? b.civora_agent_id[1] : "—",
                since: b.create_date ? String(b.create_date).slice(0, 4) : "",
            };
        });

        this.state.buyers = rows;
        this.state.stats = {
            count: rows.length,
            budget: budgetTot,
            inventory: this.saleBiens.length,
            avgScore: rows.length ? Math.round(scoreTot / rows.length) : 0,
        };
        this.state.loading = false;
    }

    async setStatus(id) {
        this.state.statusFilter = id;
        await this.load();
    }
    async onSearchInput(ev) {
        this.state.search = ev.target.value;
        await this.load();
    }

    statusMeta(b) {
        return STATUS_META[b.status] || { label: "—", variant: "neutral" };
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
    matchLabel(b) {
        return b.matches === null ? "—" : b.matches + "";
    }
    openBuyer(b) {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.buyer_360",
            params: { buyerId: b.id },
            target: "current",
        });
    }
}

registry.category("actions").add("civora.buyers", CivoraBuyersScreen);
