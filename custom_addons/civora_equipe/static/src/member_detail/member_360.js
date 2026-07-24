/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";

const DEPT_LABELS = {
    direction: "Direction",
    commercial: "Commercial",
    gestion: "Gestion locative",
    support: "Support",
};
const STATUS_LABELS = {
    actif: "Actif",
    conge: "En conge",
    inactif: "Inactif",
};

class CivoraMember360 extends Component {
    static template = "civora_equipe.Member360";
    static components = { CivoraStatCard };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.memberId = this.props.action.params?.member_id;
        this.state = useState({
            member: null,
            stats: {},
            activeTab: "overview",
        });
        onWillStart(() => this.load());
    }

    async load() {
        if (!this.memberId) return;
        const [member] = await this.orm.read("civora.team.member", [this.memberId], [
            "name", "user_id", "role_id", "department", "status",
            "hire_date", "phone", "email", "bio",
            "property_count", "lead_count", "sale_count",
            "location_count", "workflow_count", "event_count",
        ]);
        const stats = await this.orm.call(
            "civora.team.member", "get_member_stats", [this.memberId],
        );
        this.state.member = member;
        this.state.stats = stats;
    }

    goBack() {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.equipe",
        });
    }

    setTab(t) { this.state.activeTab = t; }

    deptLabel(d) { return DEPT_LABELS[d] || d; }
    deptClass(d) {
        const m = { direction: "violet", commercial: "accent", gestion: "info", support: "primary" };
        return m[d] || "";
    }
    statusLabel(s) { return STATUS_LABELS[s] || s; }
    statusClass(s) {
        const m = { actif: "success", conge: "warning", inactif: "danger" };
        return m[s] || "";
    }

    async setStatus(status) {
        await this.orm.write("civora.team.member", [this.memberId], { status });
        await this.load();
    }
}

registry.category("actions").add("civora.member_360", CivoraMember360);
