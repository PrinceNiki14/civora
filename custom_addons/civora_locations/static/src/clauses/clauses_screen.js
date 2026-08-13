/** @odoo-module **/
import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { CivoraBadge } from "@civora_core/components/civora_kit";

const LEASE_TYPE_LABEL = { residentiel: "Résidentiel", commercial: "Commercial" };

export class CivoraClausesScreen extends Component {
    static template = "civora_locations.ClausesScreen";
    static components = { CivoraBadge };
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            tab: "clauses",              // "clauses" | "sets"
            filterType: "residentiel",
            clauses: [],
            sets: [],
            drawerOpen: false,
            drawerMode: "create",        // "create" | "edit"
            drawerTarget: "clause",      // "clause" | "set"
            saving: false,
            deleteConfirm: null,         // id en attente de confirmation
            form: this._emptyClauseForm(),
            setForm: this._emptySetForm(),
        });
        onWillStart(() => this.load());
    }

    _emptyClauseForm() {
        return {
            id: null, name: "", numero: "", sequence: 10,
            lease_type: "residentiel", body: "", active: true,
        };
    }

    _emptySetForm() {
        return {
            id: null, name: "", lease_type: "residentiel",
            description: "", clause_ids: [],
        };
    }

    async load() {
        this.state.loading = true;
        const [clauses, sets] = await Promise.all([
            this.orm.searchRead("civora.lease.clause",
                [["active", "in", [true, false]]],
                ["id", "name", "numero", "sequence", "lease_type", "body", "active"],
                { order: "sequence asc, id asc" }
            ),
            this.orm.searchRead("civora.lease.clause.set",
                [],
                ["id", "name", "lease_type", "description", "clause_count", "clause_ids"],
                { order: "name asc" }
            ),
        ]);
        this.state.clauses = clauses;
        this.state.sets = sets;
        this.state.loading = false;
    }

    get filteredClauses() {
        return this.state.clauses.filter(c => c.lease_type === this.state.filterType);
    }

    get filteredSets() {
        return this.state.sets.filter(s => s.lease_type === this.state.filterType);
    }

    setTab(tab) { this.state.tab = tab; }
    setFilter(type) { this.state.filterType = type; }

    // ── Clause CRUD ──────────────────────────────────────────────────
    openCreateClause() {
        this.state.form = { ...this._emptyClauseForm(), lease_type: this.state.filterType };
        this.state.drawerMode = "create";
        this.state.drawerTarget = "clause";
        this.state.drawerOpen = true;
    }

    openEditClause(clause) {
        this.state.form = {
            id: clause.id, name: clause.name, numero: clause.numero || "",
            sequence: clause.sequence, lease_type: clause.lease_type,
            body: clause.body || "", active: clause.active,
        };
        this.state.drawerMode = "edit";
        this.state.drawerTarget = "clause";
        this.state.drawerOpen = true;
    }

    async saveClause() {
        const f = this.state.form;
        if (!f.name.trim()) {
            this.notification.add("Le titre de la clause est obligatoire.", { type: "warning" });
            return;
        }
        if (!f.body || !f.body.trim()) {
            this.notification.add("Le contenu de la clause est obligatoire.", { type: "warning" });
            return;
        }
        this.state.saving = true;
        try {
            const vals = {
                name: f.name.trim(),
                numero: f.numero.trim(),
                sequence: f.sequence || 10,
                lease_type: f.lease_type,
                body: f.body,
                active: f.active,
            };
            if (f.id) {
                await this.orm.write("civora.lease.clause", [f.id], vals);
            } else {
                await this.orm.create("civora.lease.clause", [vals]);
            }
            await this.load();
            this.state.drawerOpen = false;
            this.notification.add(
                f.id ? "Clause mise à jour." : "Clause créée.",
                { type: "success" }
            );
        } catch (e) {
            this.notification.add("Erreur : " + (e.message || e), { type: "danger" });
        }
        this.state.saving = false;
    }

    async toggleActive(clause) {
        await this.orm.write("civora.lease.clause", [clause.id], { active: !clause.active });
        await this.load();
    }

    requestDelete(id) { this.state.deleteConfirm = id; }
    cancelDelete() { this.state.deleteConfirm = null; }

    async confirmDelete() {
        const id = this.state.deleteConfirm;
        if (!id) return;
        try {
            await this.orm.unlink("civora.lease.clause", [id]);
            await this.load();
            this.state.deleteConfirm = null;
            this.notification.add("Clause supprimée.", { type: "success" });
        } catch (e) {
            this.notification.add("Impossible de supprimer : " + (e.message || e), { type: "danger" });
            this.state.deleteConfirm = null;
        }
    }

    // ── Set CRUD ─────────────────────────────────────────────────────
    openCreateSet() {
        this.state.setForm = { ...this._emptySetForm(), lease_type: this.state.filterType };
        this.state.drawerMode = "create";
        this.state.drawerTarget = "set";
        this.state.drawerOpen = true;
    }

    openEditSet(set) {
        this.state.setForm = {
            id: set.id, name: set.name, lease_type: set.lease_type,
            description: set.description || "", clause_ids: [...(set.clause_ids || [])],
        };
        this.state.drawerMode = "edit";
        this.state.drawerTarget = "set";
        this.state.drawerOpen = true;
    }

    async saveSet() {
        const f = this.state.setForm;
        if (!f.name.trim()) {
            this.notification.add("Le nom du jeu est obligatoire.", { type: "warning" });
            return;
        }
        this.state.saving = true;
        try {
            const vals = {
                name: f.name.trim(),
                lease_type: f.lease_type,
                description: f.description || "",
            };
            if (f.id) {
                await this.orm.write("civora.lease.clause.set", [f.id], vals);
            } else {
                await this.orm.create("civora.lease.clause.set", [vals]);
            }
            await this.load();
            this.state.drawerOpen = false;
            this.notification.add(f.id ? "Jeu mis à jour." : "Jeu créé.", { type: "success" });
        } catch (e) {
            this.notification.add("Erreur : " + (e.message || e), { type: "danger" });
        }
        this.state.saving = false;
    }

    closeDrawer() {
        this.state.drawerOpen = false;
        this.state.deleteConfirm = null;
    }

    typeLabel(type) { return LEASE_TYPE_LABEL[type] || type; }

    /** Extrait le texte brut d'un corps HTML pour l'aperçu liste */
    bodyPreview(html) {
        if (!html) return "";
        const stripped = html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
        return stripped.length > 120 ? stripped.substring(0, 120) + "…" : stripped;
    }
}

registry.category("actions").add("civora.clauses", CivoraClausesScreen);
