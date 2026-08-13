import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";
import { MemberDialog } from "./member_drawer";

const TABS = [
    { key: "annuaire", label: "Annuaire" },
    { key: "performance", label: "Performance" },
    { key: "planning", label: "Planning" },
    { key: "objectifs", label: "Objectifs" },
    { key: "commissions", label: "Commissions" },
    { key: "formation", label: "Formation" },
    { key: "permissions", label: "Permissions" },
    { key: "activite", label: "Activité" },
];

const PRESENCE_LABELS = {
    present: "Présent",
    en_visite: "En visite",
    conge: "Congé",
    absent: "Absent",
};

const PLANNING_DAYS = [
    { label: "LUN 27", key: "lun" },
    { label: "MAR 28", key: "mar" },
    { label: "MER 29", key: "mer" },
    { label: "JEU 30", key: "jeu" },
    { label: "VEN 31", key: "ven" },
    { label: "SAM 01", key: "sam" },
    { label: "DIM 02", key: "dim" },
];

const PLANNING_EVENTS = {
    0: {
        lun: [{ type: "RDV client", time: "09:00-12:00", location: "Cocody", color: "green" }],
        mar: [{ type: "Visites terrain", time: "08:30-17:30", location: "Plateau", color: "blue" }],
        mer: [{ type: "Bureau", time: "09:00-17:00", color: "teal" }],
        jeu: [{ type: "Prospection", time: "08:30-13:00", color: "orange" }],
        ven: [{ type: "Closing notaire", time: "10:00-12:00", location: "Me Konan", color: "darkgreen" }],
    },
    1: {
        lun: [{ type: "Visites terrain", time: "08:30-17:30", location: "Yopougon", color: "blue" }],
        mar: [{ type: "Prospection", time: "09:00-16:00", color: "orange" }],
        mer: [{ type: "RDV client", time: "14:00-16:00", location: "Marcory", color: "green" }],
        jeu: [{ type: "Revue pipeline", time: "09:00-11:00", color: "blue" }],
        ven: [{ type: "Bureau", time: "09:00-17:00", color: "teal" }],
    },
    2: {
        lun: [{ type: "Prospection", time: "08:30-14:00", color: "orange" }],
        mar: [{ type: "Bureau", time: "09:00-17:00", color: "teal" }],
        mer: [{ type: "Visites terrain", time: "08:30-17:30", location: "Bingerville", color: "blue" }],
        jeu: [{ type: "RDV client", time: "10:00-12:00", location: "Cocody", color: "green" }],
        ven: [{ type: "Prospection", time: "09:00-15:00", color: "orange" }],
    },
    3: {
        lun: [{ type: "Bureau", time: "09:00-17:00", color: "teal" }],
        mar: [{ type: "RDV client", time: "09:00-11:00", location: "Plateau", color: "green" }],
        mer: [{ type: "Closing notaire", time: "14:00-16:00", location: "Me Bamba", color: "darkgreen" }],
        jeu: [{ type: "Visites terrain", time: "08:30-17:30", location: "Riviera", color: "blue" }],
        ven: [{ type: "Revue pipeline", time: "09:00-11:00", color: "blue" }],
    },
    4: {
        lun: [{ type: "RDV client", time: "10:00-12:00", location: "Treichville", color: "green" }],
        mar: [{ type: "Visites terrain", time: "08:30-17:30", location: "Abobo", color: "blue" }],
        mer: [{ type: "Prospection", time: "08:30-16:00", color: "orange" }],
        jeu: [{ type: "Bureau", time: "09:00-17:00", color: "teal" }],
        ven: [{ type: "RDV client", time: "14:00-17:00", location: "Zone 4", color: "green" }],
    },
};

const TRAINING_SESSIONS = [
    {
        id: 1,
        title: "Loi Bail 2024 — mise a jour reglementaire",
        category: "Reglementaire",
        mode: "Présentiel",
        hours: 3,
        participants: 3,
        instructor: "Cabinet Assoumou",
        date: "08 aout 2026",
        status: "Planifie",
        certified: false,
    },
    {
        id: 2,
        title: "Outils IA & CRM avance",
        category: "Outils & digital",
        mode: "Visio",
        hours: 4,
        participants: 4,
        instructor: "Awa Traore",
        date: "16 aout 2026",
        status: "Planifie",
        certified: false,
    },
    {
        id: 3,
        title: "Negociation acheteurs premium",
        category: "Commercial",
        mode: "Présentiel",
        hours: 8,
        participants: 3,
        instructor: "Institut Vente Abidjan",
        date: "16 juil. 2026",
        status: "Termine",
        certified: false,
    },
    {
        id: 4,
        title: "Onboarding CIVORA 360",
        category: "Onboarding",
        mode: "E-learning",
        hours: 16,
        participants: 1,
        instructor: "Karim Diallo",
        date: "Continu",
        status: "En cours",
        certified: false,
    },
    {
        id: 5,
        title: "Certification courtage immobilier",
        category: "Certification",
        mode: "Présentiel",
        hours: 40,
        participants: 2,
        instructor: "Chambre des courtiers CI",
        date: "13 oct. 2026",
        status: "Planifie",
        certified: true,
    },
];

const PERMISSIONS_MATRIX = [
    {
        role: "Administrateur",
        color: "red",
        members: [],
        perimeter: "Total · accès à toutes les données",
        access: 19,
        total: 19,
        count: 0,
    },
    {
        role: "Manager",
        color: "blue",
        members: ["Mariam Bamba", "Karim Diallo"],
        perimeter: "Pipeline, équipe, reporting",
        access: 18,
        total: 19,
        count: 2,
    },
    {
        role: "Agent",
        color: "green",
        members: ["Kofi Asante", "Lea N'Guessan", "Ibrahim Toure", "Aicha Konate", "Awa Traore"],
        perimeter: "Leads, biens et dossiers affectes",
        access: 17,
        total: 19,
        count: 5,
    },
    {
        role: "Finance",
        color: "yellow",
        members: ["Jean-Marc Koffi"],
        perimeter: "Comptabilité, commissions, factures",
        access: 12,
        total: 19,
        count: 1,
    },
];

const ACTIVITY_FEED = [
    {
        icon: "fa-handshake-o",
        iconColor: "green",
        text: "Mariam Bamba a close le deal Villa Cocody 5P",
        time: "il y a 1h",
    },
    {
        icon: "fa-calendar",
        iconColor: "blue",
        text: "Kofi Asante a planifie une visite avec M. Diallo",
        time: "il y a 2h",
    },
    {
        icon: "fa-star",
        iconColor: "yellow",
        text: "Lea N'Guessan a recu une note 4.8/5 du client Kouame",
        time: "il y a 3h",
    },
    {
        icon: "fa-user-plus",
        iconColor: "green",
        text: "Ibrahim Toure a ajoute 3 nouveaux mandats",
        time: "il y a 5h",
    },
    {
        icon: "fa-check-circle",
        iconColor: "green",
        text: "Aïcha Konaté — formation Négociation terminée",
        time: "il y a 1j",
    },
    {
        icon: "fa-exclamation-triangle",
        iconColor: "orange",
        text: "Awa Traore — conge valide du 15 au 30 juil.",
        time: "il y a 2j",
    },
    {
        icon: "fa-cog",
        iconColor: "gray",
        text: "Karim Diallo a mis à jour les permissions Agent",
        time: "il y a 3j",
    },
];

export class CivoraTeamScreen extends Component {
    static template = "civora_equipe.TeamScreen";
    static components = { CivoraStatCard, MemberDialog };
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.tabs = TABS;
        this.planningDays = PLANNING_DAYS;
        this.trainingSessions = TRAINING_SESSIONS;
        this.permissionsMatrix = PERMISSIONS_MATRIX;
        this.activityFeed = ACTIVITY_FEED;
        this.state = useState({
            members: [],
            kpis: {},
            activeTab: "annuaire",
            search: "",
            showDrawer: false,
            editMemberId: false,
        });
        onWillStart(() => this.load());
    }

    async load() {
        const [kpis, members] = await Promise.all([
            this.orm.call("civora.team.member", "get_team_kpis", []),
            this.orm.call("civora.team.member", "get_members_list", []),
        ]);
        this.state.kpis = kpis;
        this.state.members = members;
    }

    get filteredMembers() {
        const q = this.state.search.toLowerCase();
        if (!q) return this.state.members;
        return this.state.members.filter(m =>
            (m.name || "").toLowerCase().includes(q) ||
            (m.role || "").toLowerCase().includes(q) ||
            (m.location || "").toLowerCase().includes(q)
        );
    }

    get subtitle() {
        const k = this.state.kpis;
        const comm = this.fmtAmount(k.total_commission);
        return (k.total || 0) + " collaborateurs · " +
               (k.commerciaux || 0) + " commerciaux · Perf. moyenne " +
               (k.avg_performance || 0) + "% · " + comm +
               " FCFA de commissions Q4";
    }

    setTab(key) { this.state.activeTab = key; }
    onSearch(ev) { this.state.search = ev.target.value; }

    fmtAmount(n) {
        if (!n) return "0";
        if (n >= 1000000) return (n / 1000000).toFixed(1).replace(".", ",") + "M";
        if (n >= 1000) return (n / 1000).toFixed(0) + "K";
        return "" + n;
    }

    fmtCommission(n) {
        if (!n) return "—";
        return this.fmtAmount(n);
    }

    presenceLabel(p) { return PRESENCE_LABELS[p] || p; }

    presenceClass(p) {
        const m = { present: "present", en_visite: "visite", conge: "conge", absent: "absent" };
        return m[p] || "present";
    }

    perfBarColor(perf) {
        if (perf >= 85) return "#22c55e";
        if (perf >= 70) return "#f59e0b";
        return "#ef4444";
    }

    get commercialMembers() {
        return [...this.state.members]
            .filter(m => m.role && m.role.toLowerCase().includes("commercial"))
            .sort((a, b) => (b.deal_count || 0) - (a.deal_count || 0));
    }

    get rankedMembers() {
        const members = this.commercialMembers.length > 0
            ? this.commercialMembers
            : [...this.state.members].sort((a, b) => (b.deal_count || 0) - (a.deal_count || 0));
        return members.map((m, i) => ({ ...m, rank: i + 1 }));
    }

    get totalDeals() {
        return this.state.members.reduce((s, m) => s + (m.deal_count || 0), 0);
    }

    get totalCA() {
        return this.state.members.reduce((s, m) => s + (m.commission_amount || 0), 0);
    }

    get topPerformer() {
        if (!this.state.members.length) return null;
        return [...this.state.members].sort((a, b) => (b.performance || 0) - (a.performance || 0))[0];
    }

    get planningMembers() {
        return this.state.members.slice(0, 5);
    }

    getPlanningEvents(memberIndex, dayKey) {
        const events = PLANNING_EVENTS[memberIndex];
        if (!events) return [];
        return events[dayKey] || [];
    }

    get commissionRows() {
        const fixeAmounts = [1200000, 1000000, 950000, 900000, 850000, 800000, 800000, 800000];
        return this.state.members.map((m, i) => {
            const fixe = fixeAmounts[i] || 800000;
            const variable = m.commission_amount || 0;
            const isTop = (m.performance || 0) >= 85;
            const bonus = isTop ? 250000 : 0;
            return {
                ...m,
                fixe,
                variable,
                bonus,
                totalBrut: fixe + variable + bonus,
            };
        });
    }

    fmtNumber(n) {
        if (!n) return "0";
        return n.toLocaleString("fr-FR");
    }

    perfPercent(m) {
        const target = 120000000;
        const ca = m.commission_amount || 0;
        if (!target) return 0;
        return Math.min(100, Math.round((ca / target) * 100));
    }

    openDetail(id) {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.member_360",
            params: { member_id: id },
        });
    }

    openDrawer() {
        this.state.editMemberId = false;
        this.state.showDrawer = true;
    }
    openEditMember(id) {
        this.state.editMemberId = id;
        this.state.showDrawer = true;
    }
    closeDrawer() {
        this.state.showDrawer = false;
        this.state.editMemberId = false;
    }
    async onMemberSaved() {
        this.state.showDrawer = false;
        await this.load();
    }
}

registry.category("actions").add("civora.equipe", CivoraTeamScreen, { force: true });
