import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";
import { CivoraAvatar, CivoraBadge } from "@civora_core/components/civora_kit";

/**
 * Ecran Locataires : contacts occupant un bien (tenant_id), agreges depuis
 * civora.property. Le bail complet (dates, encaissements) viendra avec le
 * module Locations / comptabilite.
 */
export class CivoraTenantsScreen extends Component {
    static template = "civora_gestion.Tenants";
    static components = { CivoraStatCard, CivoraAvatar, CivoraBadge };
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            view: "list",
            tenants: [],
            search: "",
            stats: { count: 0, mrr: 0 },
        });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;

        const biens = await this.orm.searchRead(
            "civora.property", [["tenant_id", "!=", false]],
            ["tenant_id", "name", "monthly_revenue", "status"], { order: "name" }
        );
        // Regroupement par locataire
        const map = {};
        for (const b of biens) {
            const id = b.tenant_id[0];
            if (!map[id]) map[id] = { id, name: b.tenant_id[1], biens: [], mrr: 0 };
            map[id].biens.push(b);
            map[id].mrr += b.monthly_revenue || 0;
        }
        const ids = Object.keys(map).map(Number);

        const partnerMap = {};
        if (ids.length) {
            const partners = await this.orm.read(
                "res.partner", ids, ["is_company", "civora_ai_score", "create_date"]
            );
            for (const p of partners) partnerMap[p.id] = p;
        }

        let mrrTot = 0;
        const tenants = Object.values(map).map((t) => {
            mrrTot += t.mrr;
            const p = partnerMap[t.id] || {};
            return {
                id: t.id,
                name: t.name,
                count: t.biens.length,
                bienLabel: t.biens.length === 1 ? t.biens[0].name : t.biens.length + " biens",
                mrr: t.mrr,
                type: p.is_company ? "Société" : "Particulier",
                score: p.civora_ai_score || 0,
                since: p.create_date ? String(p.create_date).slice(0, 4) : "",
            };
        });
        tenants.sort((a, b) => b.mrr - a.mrr);

        this.allTenants = tenants;
        this.state.stats = { count: tenants.length, mrr: mrrTot };
        this.applyFilter();
        this.state.loading = false;
    }

    setView(v) {
        this.state.view = v;
    }
    get tabList() {
        return [
            { id: "list", label: "Locataires", count: this.allTenants ? this.allTenants.length : 0 },
            { id: "leases", label: "Baux" },
            { id: "payments", label: "Encaissements" },
        ];
    }
    applyFilter() {
        const q = (this.state.search || "").trim().toLowerCase();
        this.state.tenants = q
            ? this.allTenants.filter((t) => (t.name || "").toLowerCase().includes(q))
            : this.allTenants;
    }
    onSearchInput(ev) {
        this.state.search = ev.target.value;
        this.applyFilter();
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
    openTenant(t) {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.tenant_360",
            params: { tenantId: t.id },
            target: "current",
        });
    }
}

registry.category("actions").add("civora.tenants", CivoraTenantsScreen);
