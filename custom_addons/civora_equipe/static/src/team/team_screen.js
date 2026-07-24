/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";
import { CivoraDrawer } from "@civora_core/components/civora_drawer";
import { MemberDrawer } from "./member_drawer";

const DEPT_LABELS = {
    direction: "Direction",
    commercial: "Commercial",
    gestion: "Gestion",
    support: "Support",
};
const STATUS_LABELS = {
    actif: "Actif",
    conge: "En conge",
    inactif: "Inactif",
};

class CivoraTeamScreen extends Component {
    static template = "civora_equipe.TeamScreen";
    static components = { CivoraStatCard, CivoraDrawer, MemberDrawer };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            members: [],
            kpis: {},
            filter: "all",
            search: "",
            showDrawer: false,
        });
        onWillStart(() => this.load());
    }

    async load() {
        const [kpis, members] = await Promise.all([
            this.orm.call("civora.team.member", "get_team_kpis", []),
            this.orm.searchRead("civora.team.member", [], [
                "name", "user_id", "role_id", "department", "status",
                "hire_date", "phone", "email", "property_count",
                "lead_count", "sale_count", "workflow_count",
            ], { order: "sequence, name" }),
        ]);
        this.state.kpis = kpis;
        this.state.members = members;
    }

    get filteredMembers() {
        let list = this.state.members;
        if (this.state.filter === "actif") {
            list = list.filter(m => m.status === "actif");
        } else if (this.state.filter === "conge") {
            list = list.filter(m => m.status === "conge");
        } else if (this.state.filter === "inactif") {
            list = list.filter(m => m.status === "inactif");
        } else if (["direction", "commercial", "gestion", "support"].includes(this.state.filter)) {
            list = list.filter(m => m.department === this.state.filter);
        }
        const q = this.state.search.toLowerCase();
        if (q) {
            list = list.filter(m =>
                (m.name || "").toLowerCase().includes(q) ||
                (m.role_id && m.role_id[1] || "").toLowerCase().includes(q) ||
                (m.email || "").toLowerCase().includes(q)
            );
        }
        return list;
    }

    setFilter(f) { this.state.filter = f; }
    onSearch(ev) { this.state.search = ev.target.value; }

    deptLabel(d) { return DEPT_LABELS[d] || d; }
    deptClass(d) {
        const m = { direction: "violet", commercial: "accent", gestion: "info", support: "primary" };
        return m[d] || "";
    }
    statusLabel(s) { return STATUS_LABELS[s] || s; }
    statusClass(s) {
        const m = { actif: "success", conge: "warning", inactif: "muted" };
        return m[s] || "";
    }

    totalAssignments(m) {
        return (m.property_count || 0) + (m.lead_count || 0) +
               (m.sale_count || 0) + (m.workflow_count || 0);
    }

    openDetail(id) {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.member_360",
            params: { member_id: id },
        });
    }

    openDrawer() { this.state.showDrawer = true; }
    closeDrawer() { this.state.showDrawer = false; }
    async onMemberSaved() {
        this.state.showDrawer = false;
        await this.load();
    }
}

registry.category("actions").add("civora.equipe", CivoraTeamScreen);
