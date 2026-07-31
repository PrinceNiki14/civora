/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

const TABS = [
    { key: "overview", label: "Vue d'ensemble" },
    { key: "performance", label: "Performance" },
    { key: "portfolio", label: "Portefeuille" },
    { key: "planning", label: "Planning" },
    { key: "commissions", label: "Commissions" },
    { key: "permissions", label: "Permissions" },
];

const PRESENCE_LABELS = {
    present: "Au bureau",
    remote: "A distance",
    absent: "Absent",
    terrain: "Sur le terrain",
};

export class CivoraMember360 extends Component {
    static template = "civora_equipe.Member360";
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.tabs = TABS;
        this.state = useState({
            member: null,
            activeTab: "overview",
        });
        onWillStart(() => this.load());
    }

    async load() {
        const memberId = this.props.action?.params?.member_id;
        if (!memberId) return;
        const members = await this.orm.call("civora.team.member", "get_members_list", []);
        this.state.member = members.find((m) => m.id === memberId) || null;
    }

    goBack() {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.equipe",
        });
    }

    setTab(tab) {
        this.state.activeTab = tab;
    }

    get portfolioCount() {
        const m = this.state.member;
        return m ? (m.deal_count || 0) : 0;
    }

    get tabsWithCounts() {
        return this.tabs.map((t) => {
            if (t.key === "portfolio") {
                return { ...t, label: `Portefeuille`, count: this.portfolioCount };
            }
            return t;
        });
    }

    get anciennete() {
        const m = this.state.member;
        if (!m || !m.hire_year) return 0;
        const now = new Date();
        return now.getFullYear() - m.hire_year;
    }

    get presenceLabel() {
        const m = this.state.member;
        if (!m) return "";
        return PRESENCE_LABELS[m.presence] || m.presence || "";
    }

    get objectifPct() {
        const m = this.state.member;
        if (!m) return 0;
        return Math.min(Math.round(m.performance || 0), 100);
    }

    get commissionDisplay() {
        const m = this.state.member;
        if (!m) return "0";
        return (m.commission_amount || 0).toLocaleString("fr-FR");
    }

    get ratingDisplay() {
        const m = this.state.member;
        if (!m) return "0";
        return (m.rating || 0).toFixed(1);
    }

    get perfBadge() {
        const m = this.state.member;
        return m ? Math.round(m.performance || 0) : 0;
    }

    get mandatsActifs() {
        const m = this.state.member;
        return m ? (m.deal_count || 0) : 0;
    }
}

registry.category("actions").add("civora.member_360", CivoraMember360, { force: true });
