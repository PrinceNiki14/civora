import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";
import { CivoraAvatar, CivoraBadge, CivoraProgress } from "@civora_core/components/civora_kit";
import { LeadDrawer } from "./lead_drawer";

const STATUS_META = {
    nouveau: { label: "Nouveau", variant: "info" },
    a_qualifier: { label: "À qualifier", variant: "warning" },
    qualifie: { label: "Qualifié", variant: "success" },
    rejete: { label: "Rejeté", variant: "danger" },
};
const STATUS_FILTERS = [
    { id: "tous", label: "Toutes" },
    { id: "nouveau", label: "Nouveau" },
    { id: "a_qualifier", label: "À qualifier" },
    { id: "qualifie", label: "Qualifié" },
    { id: "rejete", label: "Rejeté" },
];
const TRANSACTION_LABEL = { vente: "Vente", location: "Location", saisonnier: "Saisonnier" };
const FIELDS = [
    "name", "partner_id", "contact_name", "email", "phone", "source_id",
    "status", "score", "transaction", "budget_min", "budget_max",
    "property_id", "agent_id", "opportunity_id", "create_date",
];

// Mapping label de source -> icone FontAwesome + ton.
// La reconnaissance se fait sur le label lowercase pour absorber les variations
// de nommage (« WhatsApp Direct », « Facebook Ads », etc.).
const SOURCE_ICONS = [
    // Reseaux sociaux et messageries
    { match: ["whatsapp", "wa"],           icon: "fa-whatsapp",      tone: "wa"      },
    { match: ["facebook", "meta", "fb"],   icon: "fa-facebook",      tone: "fb"      },
    { match: ["instagram", "insta"],       icon: "fa-instagram",     tone: "ig"      },
    { match: ["tiktok"],                   icon: "fa-music",         tone: "tt"      },
    { match: ["linkedin"],                 icon: "fa-linkedin",      tone: "in"      },
    { match: ["telegram"],                 icon: "fa-paper-plane",   tone: "tg"      },
    // Plateformes immobilieres / saisonnier
    { match: ["booking"],                  icon: "fa-bed",           tone: "bk"      },
    { match: ["airbnb"],                   icon: "fa-home",          tone: "ab"      },
    { match: ["site web", "website", "site"], icon: "fa-globe",      tone: "web"     },
    // Canaux commerciaux directs
    { match: ["telephone", "tel", "appel", "phone"], icon: "fa-phone",  tone: "call" },
    { match: ["email", "mail", "@"],       icon: "fa-envelope",      tone: "mail"    },
    { match: ["sms"],                      icon: "fa-comment",       tone: "sms"     },
    { match: ["agence", "walk"],           icon: "fa-building-o",    tone: "agc"     },
    { match: ["partenaire", "referral", "referral"], icon: "fa-handshake-o", tone: "ref" },
    { match: ["direct"],                   icon: "fa-user-plus",     tone: "dir"     },
    { match: ["campagne", "ads", "publicit"], icon: "fa-bullhorn",   tone: "ads"     },
    { match: ["salon", "event"],           icon: "fa-star-o",        tone: "evt"     },
];
function iconForSource(label) {
    const l = (label || "").toLowerCase();
    for (const s of SOURCE_ICONS) {
        if (s.match.some((m) => l.includes(m))) return s;
    }
    return { icon: "fa-random", tone: "def" };
}

function emptyFilters() {
    return {
        source_ids: [],   // multi-select
        agent_id: false,
        transaction: "",
        budget_min: 0,
        budget_max: 0,
        max_days: 0,
    };
}

export class CivoraLeadsScreen extends Component {
    static template = "civora_pipeline.Leads";
    static components = { CivoraStatCard, CivoraAvatar, CivoraBadge, CivoraProgress, LeadDrawer };
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.statusFilters = STATUS_FILTERS;
        this.iconForSource = iconForSource;
        this.state = useState({
            loading: true,
            filter: "tous",
            selectedId: false,
            drawer: { open: false, leadId: false },
            stats: { new7: 0, toQualify: 0, qualifRate: 0, avgScore: 0 },
            funnel: { total: 0, a_qualifier: 0, qualifie: 0, rejete: 0 },
            sources: [],
            hotCount: 0,
            autoAssigning: false,
            // Filtres avances
            filtersOpen: false,
            filters: emptyFilters(),
            filtersDraft: emptyFilters(),
            allSources: [],
            allAgents: [],
        });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        this.leads = await this.orm.searchRead("civora.lead", [], FIELDS, { order: "score desc, create_date desc" });
        // Referentiels utilises par le modal de filtres.
        this.state.allSources = await this.orm.searchRead("civora.contact.source", [], ["name"], { order: "name" });
        this.state.allAgents = await this.orm.searchRead(
            "res.users", [["share", "=", false]], ["name"], { order: "name" },
        );

        const now = Date.now();
        const weekAgo = now - 7 * 24 * 3600 * 1000;
        let new7 = 0, toQualify = 0, qualifie = 0, rejete = 0, aQualifier = 0, scoreTot = 0, hot = 0;
        const srcMap = {};
        for (const l of this.leads) {
            if (l.create_date && new Date(l.create_date.replace(" ", "T")).getTime() >= weekAgo) new7++;
            if (l.status === "a_qualifier") { toQualify++; aQualifier++; }
            if (l.status === "qualifie") qualifie++;
            if (l.status === "rejete") rejete++;
            scoreTot += l.score || 0;
            if ((l.score || 0) >= 85) hot++;
            const src = l.source_id ? l.source_id[1] : "Direct";
            srcMap[src] = (srcMap[src] || 0) + 1;
        }
        const total = this.leads.length;
        this.state.stats = {
            new7,
            toQualify,
            qualifRate: total ? Math.round((qualifie / total) * 100) : 0,
            avgScore: total ? Math.round(scoreTot / total) : 0,
        };
        this.state.funnel = { total, a_qualifier: aQualifier, qualifie, rejete };
        this.state.hotCount = hot;
        this.state.sources = Object.entries(srcMap)
            .map(([label, n]) => {
                const meta = iconForSource(label);
                return { label, n, pct: total ? Math.round((n / total) * 100) : 0,
                         icon: meta.icon, tone: meta.tone };
            })
            .sort((a, b) => b.n - a.n);

        if (!this.state.selectedId || !this.leads.find((l) => l.id === this.state.selectedId)) {
            const first = this.filteredLeads[0];
            this.state.selectedId = first ? first.id : false;
        }
        this.state.loading = false;
    }

    // --- Filtres / selection ------------------------------------------
    get filteredLeads() {
        const f = this.state.filters;
        const now = Date.now();
        return this.leads.filter((l) => {
            // Chip statut principal
            if (this.state.filter !== "tous" && l.status !== this.state.filter) return false;
            // Sources (multi)
            if (f.source_ids.length) {
                const sid = l.source_id ? l.source_id[0] : false;
                if (!sid || !f.source_ids.includes(sid)) return false;
            }
            // Agent
            if (f.agent_id && (!l.agent_id || l.agent_id[0] !== f.agent_id)) return false;
            // Transaction
            if (f.transaction && l.transaction !== f.transaction) return false;
            // Budget min : on considere que le max du lead couvre au moins ce montant.
            if (Number(f.budget_min) > 0) {
                const target = (l.budget_max || l.budget_min || 0);
                if (target < Number(f.budget_min)) return false;
            }
            // Budget max : on considere que le min du lead ne depasse pas ce montant.
            if (Number(f.budget_max) > 0) {
                const target = (l.budget_min || l.budget_max || 0);
                if (target > Number(f.budget_max)) return false;
            }
            // Anciennete max (jours)
            if (Number(f.max_days) > 0 && l.create_date) {
                const d = new Date(l.create_date.replace(" ", "T")).getTime();
                const days = Math.floor((now - d) / (24 * 3600 * 1000));
                if (days > Number(f.max_days)) return false;
            }
            return true;
        });
    }
    get activeFilterCount() {
        const f = this.state.filters;
        let n = 0;
        if (f.source_ids.length) n++;
        if (f.agent_id) n++;
        if (f.transaction) n++;
        if (Number(f.budget_min) > 0) n++;
        if (Number(f.budget_max) > 0) n++;
        if (Number(f.max_days) > 0) n++;
        return n;
    }
    setFilter(id) {
        this.state.filter = id;
        const list = this.filteredLeads;
        if (!list.find((l) => l.id === this.state.selectedId)) {
            this.state.selectedId = list.length ? list[0].id : false;
        }
    }
    selectLead(l) {
        this.state.selectedId = l.id;
    }
    get selected() {
        return this.leads.find((l) => l.id === this.state.selectedId) || null;
    }

    // --- Actions -------------------------------------------------------
    async qualify(l) {
        await this.orm.call("civora.lead", "action_qualify", [[l.id]]);
        await this.load();
    }
    async reject(l) {
        await this.orm.call("civora.lead", "action_reject", [[l.id]]);
        await this.load();
    }
    openCreate() {
        this.state.drawer = { open: true, leadId: false };
    }
    async importVisits() {
        const n = await this.orm.call("civora.lead", "create_from_visit_requests", []);
        if (n > 0) {
            this.notification.add(`${n} demande(s) de visite importée(s) en piste.`, { type: "success" });
            await this.load();
        } else {
            this.notification.add("Aucune nouvelle demande de visite à importer.", { type: "info" });
        }
    }
    openEdit(l) {
        this.state.drawer = { open: true, leadId: l.id };
    }
    async closeDrawer(saved) {
        this.state.drawer = { open: false, leadId: false };
        if (saved) await this.load();
    }
    goPipeline() {
        this.action.doAction({ type: "ir.actions.client", tag: "civora.pipeline", target: "current" });
    }

    // --- Filtres avances ----------------------------------------------
    openFilters() {
        this.state.filtersDraft = {
            source_ids: [...this.state.filters.source_ids],
            agent_id: this.state.filters.agent_id,
            transaction: this.state.filters.transaction,
            budget_min: this.state.filters.budget_min,
            budget_max: this.state.filters.budget_max,
            max_days: this.state.filters.max_days,
        };
        this.state.filtersOpen = true;
    }
    closeFilters() { this.state.filtersOpen = false; }
    toggleFilterSource(id) {
        const arr = this.state.filtersDraft.source_ids;
        const idx = arr.indexOf(id);
        if (idx >= 0) arr.splice(idx, 1);
        else arr.push(id);
    }
    isSourceOn(id) { return this.state.filtersDraft.source_ids.includes(id); }
    setFilterField(field, ev) { this.state.filtersDraft[field] = ev.target.value; }
    setFilterNumber(field, ev) { this.state.filtersDraft[field] = Number(ev.target.value) || 0; }
    setFilterAgent(ev) {
        this.state.filtersDraft.agent_id = ev.target.value ? parseInt(ev.target.value) : false;
    }
    applyFilters() {
        this.state.filters = {
            source_ids: [...this.state.filtersDraft.source_ids],
            agent_id: this.state.filtersDraft.agent_id,
            transaction: this.state.filtersDraft.transaction,
            budget_min: this.state.filtersDraft.budget_min,
            budget_max: this.state.filtersDraft.budget_max,
            max_days: this.state.filtersDraft.max_days,
        };
        this.state.filtersOpen = false;
        // Ajuster la selection si l'element courant est filtre.
        const list = this.filteredLeads;
        if (!list.find((l) => l.id === this.state.selectedId)) {
            this.state.selectedId = list.length ? list[0].id : false;
        }
    }
    resetFilters() { this.state.filtersDraft = emptyFilters(); }
    clearFilters() {
        this.state.filters = emptyFilters();
        const list = this.filteredLeads;
        if (!list.find((l) => l.id === this.state.selectedId)) {
            this.state.selectedId = list.length ? list[0].id : false;
        }
    }

    // --- Auto-assignation des pistes chaudes ---------------------------
    async autoAssignHot() {
        if (this.state.autoAssigning) return;
        this.state.autoAssigning = true;
        try {
            const res = await this.orm.call("civora.lead", "action_auto_assign_hot", []);
            const assigned = (res && res.assigned) || 0;
            const skipped = (res && res.skipped) || 0;
            if (assigned > 0) {
                const nAg = res.agents || 0;
                this.notification.add(
                    `${assigned} piste(s) chaude(s) attribuée(s) à ${nAg} agent(s).`,
                    { type: "success" },
                );
                await this.load();
            } else if (skipped > 0) {
                this.notification.add(
                    `Aucun agent disponible pour attribuer ${skipped} piste(s) chaude(s).`,
                    { type: "warning" },
                );
            } else {
                this.notification.add(
                    "Aucune piste chaude à attribuer (toutes déjà assignées).",
                    { type: "info" },
                );
            }
        } catch (e) {
            this.notification.add("Auto-attribution impossible.", { type: "danger" });
        } finally {
            this.state.autoAssigning = false;
        }
    }

    // --- Export CSV ---------------------------------------------------
    exportCsv() {
        const list = this.filteredLeads;
        if (!list.length) {
            this.notification.add("Aucune piste à exporter.", { type: "info" });
            return;
        }
        const HEAD = [
            "Titre", "Statut", "Score", "Source", "Contact", "Email", "Téléphone",
            "Transaction", "Bien", "Budget min", "Budget max", "Agent", "Créée le",
        ];
        const rows = list.map((l) => [
            l.name || "",
            (STATUS_META[l.status] || {}).label || l.status || "",
            l.score || 0,
            this.sourceLabel(l),
            l.partner_id ? l.partner_id[1] : (l.contact_name || ""),
            l.email || "",
            l.phone || "",
            this.transactionLabel(l),
            l.property_id ? l.property_id[1] : "",
            l.budget_min || 0,
            l.budget_max || 0,
            l.agent_id ? l.agent_id[1] : "",
            l.create_date || "",
        ]);
        // Separateur `;` + BOM UTF-8 -> ouverture directe dans Excel FR.
        const escape = (v) => {
            const s = String(v == null ? "" : v);
            if (/[;"\n\r]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
            return s;
        };
        const csv = [HEAD, ...rows].map((r) => r.map(escape).join(";")).join("\r\n");
        const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const stamp = new Date().toISOString().slice(0, 10);
        const a = document.createElement("a");
        a.href = url;
        a.download = `civora_pistes_${stamp}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        setTimeout(() => URL.revokeObjectURL(url), 500);
        this.notification.add(`${list.length} piste(s) exportée(s).`, { type: "success" });
    }

    // --- Helpers -------------------------------------------------------
    statusMeta(l) {
        return STATUS_META[l.status] || { label: l.status || "—", variant: "neutral" };
    }
    sourceLabel(l) {
        return l.source_id ? l.source_id[1] : "Direct";
    }
    transactionLabel(l) {
        return TRANSACTION_LABEL[l.transaction] || "—";
    }
    agentLabel(l) {
        return l.agent_id ? l.agent_id[1] : "—";
    }
    contactLine(l) {
        const parts = [];
        if (l.transaction) parts.push(TRANSACTION_LABEL[l.transaction]);
        if (l.property_id) parts.push(l.property_id[1]);
        parts.push(this.budgetLabel(l));
        return parts.filter(Boolean).join(" · ");
    }
    fmtMoney(n) {
        n = Number(n || 0);
        if (n >= 1e9) return (n / 1e9).toFixed(1).replace(".", ",") + " Md";
        if (n >= 1e6) return (n / 1e6).toFixed(n % 1e6 ? 1 : 0).replace(".", ",") + " M";
        if (n >= 1e3) return Math.round(n / 1e3) + " k";
        return "" + n;
    }
    budgetLabel(l) {
        const mn = l.budget_min || 0;
        const mx = l.budget_max || 0;
        if (mn && mx) return this.fmtMoney(mn) + " – " + this.fmtMoney(mx) + " FCFA";
        if (mx) return "≤ " + this.fmtMoney(mx) + " FCFA";
        if (mn) return "≥ " + this.fmtMoney(mn) + " FCFA";
        return "Budget n.c.";
    }
    scoreTone(score) {
        return score >= 80 ? "success" : score >= 60 ? "warning" : "danger";
    }
    recommendation(score) {
        if (score >= 85) return "Piste très chaude — conversion immédiate recommandée.";
        if (score >= 60) return "Piste à qualifier — appel sortant sous 24h recommandé.";
        return "Piste faible — à cultiver via campagne de nurturing.";
    }
}

registry.category("actions").add("civora.leads", CivoraLeadsScreen);
