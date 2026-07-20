import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";
import { CivoraAvatar, CivoraBadge, CivoraProgress } from "@civora_core/components/civora_kit";

const STATUS_DIST = [
    { key: "loue", label: "Loué", tone: "success" },
    { key: "saisonnier", label: "Saisonnier", tone: "info" },
    { key: "disponible", label: "Disponible", tone: "warning" },
];

/**
 * Ecran Proprietaires : agregation du parc par proprietaire (owner_id),
 * enrichie des donnees contact (segment, score, anciennete).
 * Onglets : Proprietaires (liste) · Portefeuille global · Reversements (a venir).
 */
export class CivoraOwnersScreen extends Component {
    static template = "civora_gestion.Owners";
    static components = { CivoraStatCard, CivoraAvatar, CivoraBadge, CivoraProgress };
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.statusDistDef = STATUS_DIST;
        this.state = useState({
            loading: true,
            view: "list",
            owners: [],
            search: "",
            stats: { count: 0, biens: 0, value: 0, mrr: 0, occupancy: 0 },
            statusDist: { disponible: 0, loue: 0, saisonnier: 0 },
            topOwners: [],
        });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;

        const groups = await this.orm.formattedReadGroup(
            "civora.property", [["owner_id", "!=", false]], ["owner_id"],
            ["price:sum", "monthly_revenue:sum"]
        );
        const occGroups = await this.orm.formattedReadGroup(
            "civora.property",
            [["owner_id", "!=", false], ["status", "in", ["loue", "saisonnier"]]],
            ["owner_id"], []
        );
        const statusGroups = await this.orm.formattedReadGroup(
            "civora.property", [["owner_id", "!=", false]], ["status"], []
        );

        const occMap = {};
        for (const g of occGroups) {
            if (g.owner_id) occMap[g.owner_id[0]] = g.__count || 0;
        }
        const statusDist = { disponible: 0, loue: 0, saisonnier: 0 };
        for (const g of statusGroups) {
            if (g.status in statusDist) statusDist[g.status] = g.__count || 0;
        }

        // Enrichissement contact : segment, score, anciennete
        const ownerIds = groups.filter((g) => g.owner_id).map((g) => g.owner_id[0]);
        const partnerMap = {};
        const segMap = {};
        if (ownerIds.length) {
            const segs = await this.orm.searchRead("civora.contact.segment", [], ["name"]);
            for (const s of segs) segMap[s.id] = s.name;
            const partners = await this.orm.read(
                "res.partner", ownerIds, ["civora_segment_ids", "civora_ai_score", "create_date"]
            );
            for (const p of partners) partnerMap[p.id] = p;
        }

        let totBiens = 0, totValue = 0, totMrr = 0, totOcc = 0;
        const owners = groups.filter((g) => g.owner_id).map((g) => {
            const id = g.owner_id[0];
            const count = g.__count || 0;
            const value = g["price:sum"] || 0;
            const mrr = g["monthly_revenue:sum"] || 0;
            const occ = occMap[id] || 0;
            totBiens += count; totValue += value; totMrr += mrr; totOcc += occ;
            const p = partnerMap[id] || {};
            const segId = (p.civora_segment_ids || [])[0];
            return {
                id,
                name: g.owner_id[1],
                count,
                value,
                mrr,
                occupancy: count ? Math.round((occ / count) * 100) : 0,
                segment: segId ? segMap[segId] || "" : "",
                score: p.civora_ai_score || 0,
                since: p.create_date ? String(p.create_date).slice(0, 4) : "",
            };
        });
        owners.sort((a, b) => b.value - a.value);

        this.allOwners = owners;
        this.state.stats = {
            count: owners.length,
            biens: totBiens,
            value: totValue,
            mrr: totMrr,
            occupancy: totBiens ? Math.round((totOcc / totBiens) * 100) : 0,
        };
        this.state.statusDist = statusDist;
        this.state.topOwners = owners.slice(0, 5);
        this.applyFilter();
        this.state.loading = false;
    }

    // --- Vue / filtres -------------------------------------------------
    setView(v) {
        this.state.view = v;
    }
    get tabList() {
        return [
            { id: "list", label: "Propriétaires", count: this.allOwners ? this.allOwners.length : 0 },
            { id: "portfolio", label: "Portefeuille global" },
            { id: "finance", label: "Reversements" },
        ];
    }
    applyFilter() {
        const q = (this.state.search || "").trim().toLowerCase();
        this.state.owners = q
            ? this.allOwners.filter((o) => (o.name || "").toLowerCase().includes(q))
            : this.allOwners;
    }
    onSearchInput(ev) {
        this.state.search = ev.target.value;
        this.applyFilter();
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
    occTone(occ) {
        return occ >= 90 ? "success" : occ >= 70 ? "accent" : "warning";
    }
    distCount(key) {
        return this.state.statusDist[key] || 0;
    }
    distPct(key) {
        const total = this.state.stats.biens;
        return total ? Math.round((this.distCount(key) / total) * 100) : 0;
    }

    openOwner(o) {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.owner_360",
            params: { ownerId: o.id },
            target: "current",
        });
    }
}

registry.category("actions").add("civora.owners", CivoraOwnersScreen);
