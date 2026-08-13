import { Component, onWillStart, useExternalListener, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";
import { CivoraBadge } from "@civora_core/components/civora_kit";
import { OpportunityDrawer } from "./opportunity_drawer";

const TRANSACTION_LABEL = { vente: "Vente", location: "Loc.", saisonnier: "Saison." };
const OPP_FIELDS = [
    "name", "partner_id", "property_id", "transaction", "stage_id",
    "expected_amount", "probability", "score", "agent_id", "create_date",
    "is_won", "is_lost", "date_won", "date_lost", "date_stage_updated",
];
// Seuils de la barre de progression : anciennete DANS L'ETAPE COURANTE.
// C'est la vraie mesure de stagnation d'un pipeline — une opportunite creee
// il y a 6 mois mais passee en "Offre" hier n'est pas stagnante.
const AGE_WATCH_DAYS = 7;
const AGE_STALE_DAYS = 30;

const STAGE_FIELDS = ["name", "code", "sequence", "is_won", "is_lost", "fold"];

// Filtres par defaut : tout ouvert.
function emptyFilters() {
    return {
        transactions: { vente: false, location: false, saisonnier: false },
        agent_id: false,
        city: "",
        min_amount: 0,
        max_days: 0,
    };
}

export class CivoraPipelineScreen extends Component {
    static template = "civora_pipeline.Pipeline";
    static components = { CivoraStatCard, CivoraBadge, OpportunityDrawer };
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.draggedOppId = null;
        this.partnerCache = {};   // { partner_id: {phone, email} }
        this.propertyCache = {};  // { property_id: {city} }
        this.state = useState({
            loading: true,
            view: "kanban",
            search: "",
            drawerOpen: false,
            editingOppId: false, // ouverture du drawer en edition
            columns: [],
            list: [],
            stats: { count: 0, hot: 0, ventes: 0, locations: 0, transfo: 0, won: 0, avgScore: 0, avgDays: 0 },
            // Gestion des etapes
            menuOpenStageId: false,
            editingStageId: false,
            editingStageName: "",
            addingStage: false,
            newStageName: "",
            canManageStages: false,
            deleteModal: null,
            // Filtres avances
            filtersOpen: false,
            filters: emptyFilters(),
            filtersDraft: emptyFilters(),
            agents: [],
            // Colonnes repliees (initialisees depuis stage.fold)
            foldedIds: [],
            // Filtre par segment de la barre de progression : { stageId, bucket }
            ageFilter: null,
            // Celebration a l'entree en Gagne
            celebration: null, // { name, amount }
        });
        useExternalListener(document, "mousedown", (ev) => this.onDocumentMouseDown(ev));
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        this.stages = await this.orm.searchRead(
            "civora.pipeline.stage", [], STAGE_FIELDS,
            { order: "sequence, id" }
        );
        this.opps = await this.orm.searchRead(
            "civora.opportunity", [], OPP_FIELDS, { order: "stage_sequence, priority desc, id desc" }
        );

        // Enrichissement : coordonnees partenaires + ville des biens
        // pour actions rapides et filtre "ville".
        await this.loadEnrichments();
        // Liste des agents pour le filtre.
        this.state.agents = await this.orm.searchRead(
            "res.users", [["share", "=", false]], ["name"], { order: "name" },
        );

        // Droit de gestion des etapes : un agent ne doit pas pouvoir
        // supprimer une colonne du pipeline de l'agence.
        try {
            this.state.canManageStages = await this.orm.call(
                "civora.pipeline.stage", "civora_can_manage_stages", []
            );
        } catch (e) {
            console.error("[CIVORA-PIPELINE] canManageStages", e);
            this.state.canManageStages = false;
        }

        // Replier par defaut les etapes marquees fold (typiquement « Perdu »).
        // Le champ existait deja dans le modele mais n'etait pas exploite.
        if (!this.foldInit) {
            this.state.foldedIds = this.stages.filter((s) => s.fold).map((s) => s.id);
            this.foldInit = true;
        }

        this.computeStats();
        this.rebuild();
        this.state.loading = false;
    }

    async loadEnrichments() {
        const partnerIds = [...new Set(this.opps.filter(o => o.partner_id).map(o => o.partner_id[0]))];
        const propertyIds = [...new Set(this.opps.filter(o => o.property_id).map(o => o.property_id[0]))];
        this.partnerCache = {};
        this.propertyCache = {};
        if (partnerIds.length) {
            const rows = await this.orm.read("res.partner", partnerIds, ["phone", "email"]);
            for (const r of rows) this.partnerCache[r.id] = r;
        }
        if (propertyIds.length) {
            const rows = await this.orm.read("civora.property", propertyIds, ["city"]);
            for (const r of rows) this.propertyCache[r.id] = r;
        }
    }

    computeStats() {
        let ventes = 0, locations = 0, won = 0, hot = 0, scoreTot = 0, daysTot = 0, active = 0;
        for (const o of this.opps) {
            if ((o.score || 0) >= 80) hot++;
            scoreTot += o.score || 0;
            daysTot += this.daysOld(o);
            if (o.is_won) { won++; }
            if (o.is_lost) continue;
            active++;
            if (o.transaction === "vente") ventes += o.expected_amount || 0;
            else if (o.transaction === "location" || o.transaction === "saisonnier") locations += o.expected_amount || 0;
        }
        const total = this.opps.length;
        this.state.stats = {
            count: active,
            hot,
            ventes,
            locations,
            transfo: total ? Math.round((won / total) * 100) : 0,
            won,
            avgScore: total ? Math.round(scoreTot / total) : 0,
            avgDays: total ? Math.round(daysTot / total) : 0,
        };
    }

    rebuild() {
        const q = (this.state.search || "").trim().toLowerCase();
        const f = this.state.filters;
        const activeTx = Object.entries(f.transactions).filter(([, v]) => v).map(([k]) => k);
        const hasTx = activeTx.length > 0;
        const cityQ = (f.city || "").trim().toLowerCase();
        const minAmt = Number(f.min_amount) || 0;
        const maxDays = Number(f.max_days) || 0;

        const match = (o) => {
            // Recherche libre
            if (q) {
                const hay = [o.name, o.partner_id && o.partner_id[1], o.property_id && o.property_id[1]]
                    .filter(Boolean).join(" ").toLowerCase();
                if (!hay.includes(q)) return false;
            }
            // Type de transaction
            if (hasTx && !activeTx.includes(o.transaction)) return false;
            // Agent
            if (f.agent_id && (!o.agent_id || o.agent_id[0] !== f.agent_id)) return false;
            // Valeur min
            if (minAmt > 0 && (o.expected_amount || 0) < minAmt) return false;
            // Anciennete max (jours)
            if (maxDays > 0 && this.daysOld(o) > maxDays) return false;
            // Ville (property.city)
            if (cityQ) {
                const pid = o.property_id ? o.property_id[0] : false;
                const city = pid && this.propertyCache[pid] ? (this.propertyCache[pid].city || "") : "";
                if (!city.toLowerCase().includes(cityQ)) return false;
            }
            return true;
        };
        const opps = this.opps.filter(match);

        const byStage = {};
        for (const s of this.stages) byStage[s.id] = [];
        for (const o of opps) {
            const sid = o.stage_id ? o.stage_id[0] : false;
            if (sid && byStage[sid]) byStage[sid].push(o);
        }
        const af = this.state.ageFilter;
        this.state.columns = this.stages.map((s, idx) => {
            const all = byStage[s.id] || [];

            // Repartition par anciennete dans l'etape.
            const seg = { recent: 0, watch: 0, stale: 0 };
            for (const o of all) seg[this.ageBucket(o)]++;
            const n = all.length || 1;

            // Un clic sur un segment restreint l'affichage de CETTE colonne.
            const cards = af && af.stageId === s.id
                ? all.filter((o) => this.ageBucket(o) === af.bucket)
                : all;

            // Chevron d'entonnoir : forme selon la position, intensite selon
            // l'avancement (repris du front CIVORA : 8% + idx*6% d'accent).
            const nStages = this.stages.length;
            const chev = "civora-pl-chev lvl-" + Math.min(idx, 9)
                + (idx === 0 ? " is-first" : "")
                + (idx === nStages - 1 ? " is-last" : "");

            return {
                stage: s,
                cards,
                chev,
                allCount: all.length,
                folded: this.state.foldedIds.includes(s.id),
                seg,
                segPct: {
                    stale: (seg.stale / n) * 100,
                    watch: (seg.watch / n) * 100,
                    recent: (seg.recent / n) * 100,
                },
                activeBucket: af && af.stageId === s.id ? af.bucket : "",
                total: cards.reduce((a, c) => a + (c.expected_amount || 0), 0),
                canLeft: idx > 0,
                canRight: idx < this.stages.length - 1,
            };
        });
        this.state.list = opps;
    }

    // --- Filtres avances ----------------------------------------------
    get activeFilterCount() {
        const f = this.state.filters;
        let n = 0;
        n += Object.values(f.transactions).filter(Boolean).length;
        if (f.agent_id) n++;
        if ((f.city || "").trim()) n++;
        if (Number(f.min_amount) > 0) n++;
        if (Number(f.max_days) > 0) n++;
        return n;
    }
    openFilters() {
        // Copie profonde des filtres actuels dans le draft.
        this.state.filtersDraft = {
            transactions: { ...this.state.filters.transactions },
            agent_id: this.state.filters.agent_id,
            city: this.state.filters.city,
            min_amount: this.state.filters.min_amount,
            max_days: this.state.filters.max_days,
        };
        this.state.filtersOpen = true;
    }
    closeFilters() { this.state.filtersOpen = false; }
    toggleFilterTx(tx) {
        this.state.filtersDraft.transactions[tx] = !this.state.filtersDraft.transactions[tx];
    }
    setFilterField(field, ev) {
        this.state.filtersDraft[field] = ev.target.value;
    }
    setFilterNumber(field, ev) {
        this.state.filtersDraft[field] = Number(ev.target.value) || 0;
    }
    setFilterAgent(ev) {
        this.state.filtersDraft.agent_id = ev.target.value ? parseInt(ev.target.value) : false;
    }
    applyFilters() {
        this.state.filters = {
            transactions: { ...this.state.filtersDraft.transactions },
            agent_id: this.state.filtersDraft.agent_id,
            city: this.state.filtersDraft.city,
            min_amount: this.state.filtersDraft.min_amount,
            max_days: this.state.filtersDraft.max_days,
        };
        this.state.filtersOpen = false;
        this.rebuild();
    }
    resetFilters() {
        this.state.filtersDraft = emptyFilters();
    }
    clearFilters() {
        this.state.filters = emptyFilters();
        this.rebuild();
    }

    // --- Toolbar -------------------------------------------------------
    setView(v) { this.state.view = v; }
    onSearchInput(ev) { this.state.search = ev.target.value; this.rebuild(); }
    openCreate() { this.state.drawerOpen = true; }
    async closeDrawer(saved) {
        this.state.drawerOpen = false;
        if (saved) await this.load();
    }
    goLeads() {
        this.action.doAction({ type: "ir.actions.client", tag: "civora.leads", target: "current" });
    }

    // --- Drag & drop des opportunites ---------------------------------
    onOppDragStart(opp, ev) {
        this.draggedOppId = opp.id;
        // Signale a la couche navigateur que c'est un deplacement d'opportunite.
        if (ev.dataTransfer) ev.dataTransfer.effectAllowed = "move";
    }
    onDragOver(ev) { ev.preventDefault(); }
    async onDrop(col) {
        const id = this.draggedOppId;
        this.draggedOppId = null;
        if (!id) return;
        const current = this.opps.find((x) => x.id === id);
        if (!current || (current.stage_id && current.stage_id[0] === col.stage.id)) return;
        // Detection : passage d'une etape non-gagnee vers une etape gagnee.
        const wasWon = !!current.is_won;
        const nowWon = !!col.stage.is_won;
        await this.orm.write("civora.opportunity", [id], { stage_id: col.stage.id });
        if (!wasWon && nowWon) {
            this.triggerCelebration(current);
        }
        await this.load();
    }

    triggerCelebration(opp) {
        const name = opp.partner_id ? opp.partner_id[1] : opp.name;
        const amount = this.fmtMoney(opp.expected_amount) + " FCFA";
        this.state.celebration = { name, amount };
        // Auto-dismiss apres 3.5 secondes.
        setTimeout(() => {
            this.state.celebration = null;
        }, 3500);
    }
    dismissCelebration() { this.state.celebration = null; }

    // --- Quick actions sur cartes -------------------------------------
    partnerContact(opp) {
        if (!opp.partner_id) return {};
        return this.partnerCache[opp.partner_id[0]] || {};
    }
    hasPhone(opp) { return !!this.partnerContact(opp).phone; }
    hasEmail(opp) { return !!this.partnerContact(opp).email; }
    hasWhatsApp(opp) { return !!this.partnerContact(opp).phone; }
    callHref(opp) {
        const c = this.partnerContact(opp);
        return "tel:" + (c.phone || "").replace(/\s/g, "");
    }
    mailHref(opp) {
        return "mailto:" + (this.partnerContact(opp).email || "");
    }
    waHref(opp) {
        const c = this.partnerContact(opp);
        const num = (c.phone || "").replace(/[^0-9+]/g, "").replace(/^\+/, "");
        return "https://wa.me/" + num;
    }
    quickAction(ev, href) {
        // Empeche l'ouverture de la fiche 360.
        if (ev) ev.stopPropagation();
        if (href) window.open(href, "_blank", "noopener");
    }

    openOpp(opp) {
        this.action.doAction({
            type: "ir.actions.client", tag: "civora.opportunity_360",
            params: { opportunityId: opp.id, origin: { tag: "civora.pipeline", label: "Pipeline" } },
            target: "current",
        });
    }

    // --- Gestion des etapes -------------------------------------------
    onDocumentMouseDown(ev) {
        // Ferme le menu kebab si clic hors d'un menu ouvert.
        if (!this.state.menuOpenStageId) return;
        const target = ev.target;
        if (target && target.closest && target.closest(".civora-pl-colmenu-wrap")) return;
        this.state.menuOpenStageId = false;
    }

    toggleMenu(stageId, ev) {
        if (ev) ev.stopPropagation();
        this.state.menuOpenStageId = this.state.menuOpenStageId === stageId ? false : stageId;
    }

    startRename(col, ev) {
        if (ev) ev.stopPropagation();
        this.state.menuOpenStageId = false;
        this.state.editingStageId = col.stage.id;
        this.state.editingStageName = col.stage.name;
    }
    onRenameInput(ev) { this.state.editingStageName = ev.target.value; }
    onRenameKey(ev) {
        if (ev.key === "Enter") { ev.preventDefault(); this.confirmRename(); }
        else if (ev.key === "Escape") { this.cancelRename(); }
    }
    cancelRename() {
        this.state.editingStageId = false;
        this.state.editingStageName = "";
    }
    async confirmRename() {
        const stageId = this.state.editingStageId;
        const newName = (this.state.editingStageName || "").trim();
        if (!stageId) return;
        if (!newName) { this.cancelRename(); return; }
        const stage = this.stages.find((s) => s.id === stageId);
        if (stage && stage.name === newName) { this.cancelRename(); return; }
        try {
            await this.orm.write("civora.pipeline.stage", [stageId], { name: newName });
            this.cancelRename();
            await this.load();
            this.notification.add("Etape renommee.", { type: "success" });
        } catch (e) {
            this.notification.add("Renommage impossible.", { type: "danger" });
        }
    }

    async moveLeft(col, ev) {
        if (ev) ev.stopPropagation();
        this.state.menuOpenStageId = false;
        if (!col.canLeft) return;
        try {
            await this.orm.call("civora.pipeline.stage", "action_move_up", [[col.stage.id]]);
            await this.load();
        } catch (e) {
            this.notification.add("Deplacement impossible.", { type: "danger" });
        }
    }
    async moveRight(col, ev) {
        if (ev) ev.stopPropagation();
        this.state.menuOpenStageId = false;
        if (!col.canRight) return;
        try {
            await this.orm.call("civora.pipeline.stage", "action_move_down", [[col.stage.id]]);
            await this.load();
        } catch (e) {
            this.notification.add("Deplacement impossible.", { type: "danger" });
        }
    }

    canDelete(col) {
        // Interdit de supprimer la derniere etape gagnee ou la derniere perdue.
        if (col.stage.is_won) {
            const wonCount = this.stages.filter((s) => s.is_won).length;
            if (wonCount <= 1) return false;
        }
        if (col.stage.is_lost) {
            const lostCount = this.stages.filter((s) => s.is_lost).length;
            if (lostCount <= 1) return false;
        }
        return true;
    }

    askDelete(col, ev) {
        if (ev) ev.stopPropagation();
        this.state.menuOpenStageId = false;
        if (!this.canDelete(col)) {
            this.notification.add(
                "Cette etape ne peut pas etre supprimee : elle est la derniere etape " +
                (col.stage.is_won ? "« Gagnée »" : "« Perdue »") + " de la societe.",
                { type: "warning" },
            );
            return;
        }
        // Cible par defaut : premiere etape differente de la meme societe.
        const others = this.stages.filter((s) => s.id !== col.stage.id);
        const defaultTarget = others.length ? others[0].id : false;
        this.state.deleteModal = {
            stageId: col.stage.id,
            stageName: col.stage.name,
            opportunityCount: col.cards.length,
            targetStageId: defaultTarget,
        };
    }
    onDeleteTargetChange(ev) {
        if (!this.state.deleteModal) return;
        this.state.deleteModal.targetStageId = ev.target.value ? parseInt(ev.target.value) : false;
    }
    closeDeleteModal() { this.state.deleteModal = null; }
    get deleteTargetOptions() {
        if (!this.state.deleteModal) return [];
        return this.stages.filter((s) => s.id !== this.state.deleteModal.stageId);
    }
    async confirmDelete() {
        const m = this.state.deleteModal;
        if (!m) return;
        if (m.opportunityCount > 0 && !m.targetStageId) {
            this.notification.add("Choisissez une etape cible pour les opportunites.", { type: "warning" });
            return;
        }
        try {
            await this.orm.call(
                "civora.pipeline.stage", "action_delete_with_reassign",
                [[m.stageId], m.targetStageId || false],
            );
            this.state.deleteModal = null;
            await this.load();
            this.notification.add("Etape supprimee.", { type: "success" });
        } catch (e) {
            const msg = (e && e.data && e.data.message) || "Suppression impossible.";
            this.notification.add(msg, { type: "danger" });
        }
    }

    // --- Ajout d'une etape --------------------------------------------
    startAddStage() {
        this.state.addingStage = true;
        this.state.newStageName = "";
    }
    cancelAddStage() {
        this.state.addingStage = false;
        this.state.newStageName = "";
    }
    onAddStageInput(ev) { this.state.newStageName = ev.target.value; }
    onAddStageKey(ev) {
        if (ev.key === "Enter") { ev.preventDefault(); this.confirmAddStage(); }
        else if (ev.key === "Escape") { this.cancelAddStage(); }
    }
    async confirmAddStage() {
        const name = (this.state.newStageName || "").trim();
        if (!name) { this.cancelAddStage(); return; }
        const maxSeq = this.stages.reduce((m, s) => Math.max(m, s.sequence || 0), 0);
        try {
            await this.orm.create("civora.pipeline.stage", [{
                name,
                sequence: maxSeq + 10,
            }]);
            this.cancelAddStage();
            await this.load();
            this.notification.add("Etape ajoutee.", { type: "success" });
        } catch (e) {
            const msg = (e && e.data && e.data.message) || "Ajout impossible.";
            this.notification.add(msg, { type: "danger" });
        }
    }

    // --- Helpers -------------------------------------------------------
    // --- Anciennete dans l'etape (barre de progression) ----------------

    /** Jours passes dans l'etape courante. Retombe sur create_date si
     *  date_stage_updated n'est pas renseignee (donnees anterieures). */
    daysInStage(o) {
        const ref = o.date_stage_updated || o.create_date;
        if (!ref) return 0;
        const start = new Date(ref.replace(" ", "T")).getTime();
        const end = o.date_won || o.date_lost
            ? new Date((o.date_won || o.date_lost).replace(" ", "T")).getTime()
            : Date.now();
        return Math.max(0, Math.floor((end - start) / 86400000));
    }

    ageBucket(o) {
        const d = this.daysInStage(o);
        if (d > AGE_STALE_DAYS) return "stale";
        if (d >= AGE_WATCH_DAYS) return "watch";
        return "recent";
    }

    segTitle(col, bucket) {
        const labels = {
            stale: "stagnantes depuis plus de " + AGE_STALE_DAYS + " jours",
            watch: "à surveiller (" + AGE_WATCH_DAYS + " à " + AGE_STALE_DAYS + " jours)",
            recent: "récentes (moins de " + AGE_WATCH_DAYS + " jours)",
        };
        return col.seg[bucket] + " opportunité(s) " + labels[bucket];
    }

    /** Clic sur un segment : filtre la colonne, re-clic annule. */
    toggleAgeFilter(col, bucket, ev) {
        if (ev) ev.stopPropagation();
        if (!col.seg[bucket]) return;
        const af = this.state.ageFilter;
        this.state.ageFilter =
            af && af.stageId === col.stage.id && af.bucket === bucket
                ? null
                : { stageId: col.stage.id, bucket };
        this.rebuild();
    }

    // --- Repli des colonnes --------------------------------------------
    toggleFold(col, ev) {
        if (ev) ev.stopPropagation();
        const ids = this.state.foldedIds;
        this.state.foldedIds = ids.includes(col.stage.id)
            ? ids.filter((i) => i !== col.stage.id)
            : [...ids, col.stage.id];
        this.rebuild();
    }

    colClass(col) {
        let c = "civora-pl-col";
        if (col.stage.is_won) c += " is-won";
        if (col.stage.is_lost) c += " is-lost";
        if (col.folded) c += " is-folded";
        return c;
    }
    stageLabel(o) { return o.stage_id ? o.stage_id[1] : "—"; }
    partnerLabel(o) { return o.partner_id ? o.partner_id[1] : o.name; }
    propertyLabel(o) { return o.property_id ? o.property_id[1] : "—"; }
    agentLabel(o) { return o.agent_id ? o.agent_id[1] : "—"; }
    txLabel(o) { return TRANSACTION_LABEL[o.transaction] || ""; }
    isRental(o) { return o.transaction === "location" || o.transaction === "saisonnier"; }
    scoreTone(score) { return score >= 80 ? "success" : score >= 60 ? "warning" : "danger"; }
    fmtMoney(n) {
        n = Number(n || 0);
        if (n >= 1e9) return (n / 1e9).toFixed(1).replace(".", ",") + " Md";
        if (n >= 1e6) return (n / 1e6).toFixed(n % 1e6 ? 1 : 0).replace(".", ",") + " M";
        if (n >= 1e3) return Math.round(n / 1e3) + " k";
        return "" + n;
    }
    kpiMoney(n) { return this.fmtMoney(n) + " FCFA"; }
    amountLabel(o) {
        return this.fmtMoney(o.expected_amount) + (this.isRental(o) ? "/m" : "") + " FCFA";
    }
    daysOld(o) {
        if (!o.create_date) return 0;
        const start = new Date(o.create_date.replace(" ", "T")).getTime();
        let end = Date.now();
        const closeDate = o.date_won || o.date_lost;
        if (closeDate) {
            end = new Date(closeDate.replace(" ", "T")).getTime();
        }
        return Math.max(0, Math.floor((end - start) / (24 * 3600 * 1000)));
    }
    stageLockLabel(col) {
        // Petit tooltip explicite sur les etapes verrouillees.
        if (col.stage.is_won) return "Etape « Gagnée » — protegee";
        if (col.stage.is_lost) return "Etape « Perdue » — protegee";
        return "";
    }
}

registry.category("actions").add("civora.pipeline", CivoraPipelineScreen);
