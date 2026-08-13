import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { CivoraBadge } from "@civora_core/components/civora_kit";
import {
    DOC_TYPE_META, STATE_META, FOLDER_META,
    fmtSize, fmtDate, fileIcon,
} from "@civora_documents/shared/constants";
import { DocumentDrawer } from "@civora_documents/detail/document_drawer";

/**
 * Écran d'un dossier canonique (baux_contrats, factures, etc.).
 * Affiche le fil d'ariane + carte du dossier + recherche + liste des documents.
 */
export class FolderView extends Component {
    static template = "civora_documents.FolderView";
    static components = { CivoraBadge, DocumentDrawer };
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        const params = (this.props.action && this.props.action.params) || {};
        this.folderSlug = params.folder || "baux_contrats";
        this.initialSearch = params.search || "";
        // Groupements possibles selon le dossier — défaut : groupement activé
        this.groupOptions = this._buildGroupOptions(this.folderSlug);
        this.state = useState({
            loading: true,
            search: this.initialSearch,
            docs: [],
            allDocs: [],
            total: 0,
            uploadDrawer: false,
            viewMode: "grid",
            groupBy: this.groupOptions[0] ? this.groupOptions[0].value : "none",
            groupData: null,
            expandedGroups: {},  // { groupId: bool }
            expandedSubgroups: {},  // pour owner_property
        });
        onWillStart(() => this.load());
    }

    _buildGroupOptions(folder) {
        // Groupements recommandés par dossier
        const map = {
            baux_contrats: [
                { value: "property", label: "Par bien" },
                { value: "tenant", label: "Par locataire" },
                { value: "none", label: "Aucun" },
            ],
            factures: [
                { value: "owner", label: "Par propriétaire" },
                { value: "month", label: "Par mois" },
                { value: "none", label: "Aucun" },
            ],
            documents_proprietaires: [
                { value: "owner", label: "Par propriétaire" },
                { value: "none", label: "Aucun" },
            ],
            documents_locataires: [
                { value: "tenant", label: "Par locataire" },
                { value: "property", label: "Par bien" },
                { value: "none", label: "Aucun" },
            ],
            documents_biens: [
                { value: "property", label: "Par bien" },
                { value: "owner_property", label: "Par propriétaire → bien" },
                { value: "none", label: "Aucun" },
            ],
            medias_photos: [
                { value: "property", label: "Par bien" },
                { value: "none", label: "Aucun" },
            ],
        };
        return map[folder] || [{ value: "none", label: "Aucun" }];
    }

    async load() {
        this.state.loading = true;
        try {
            if (this.state.groupBy && this.state.groupBy !== "none") {
                const res = await this.orm.call(
                    "civora.document", "get_folder_documents_grouped",
                    [this.folderSlug, this.state.groupBy]
                );
                this.state.groupData = res || { groups: [], ungrouped: [], total: 0 };
                this.state.total = this.state.groupData.total || 0;
                // Auto-expand tous les groupes par défaut (moins de clics)
                const exp = {};
                for (const g of this.state.groupData.groups) exp[g.id] = true;
                this.state.expandedGroups = exp;
                const subexp = {};
                for (const g of this.state.groupData.groups) {
                    for (const sg of (g.subgroups || [])) subexp[sg.id] = true;
                }
                this.state.expandedSubgroups = subexp;
                // Aussi remplir allDocs pour la recherche
                const allDocs = [];
                for (const g of this.state.groupData.groups) {
                    for (const sg of (g.subgroups || [])) {
                        for (const d of sg.documents) allDocs.push(d);
                    }
                    for (const d of g.documents) allDocs.push(d);
                }
                for (const d of this.state.groupData.ungrouped) allDocs.push(d);
                this.state.allDocs = allDocs;
                this.state.docs = allDocs;  // pour compat avec les autres méthodes
            } else {
                const res = await this.orm.call(
                    "civora.document", "get_folder_documents", [this.folderSlug]
                );
                this.state.allDocs = res.documents || [];
                this.state.total = res.total || 0;
                this.state.groupData = null;
                this.applyFilter();
            }
        } catch (e) {
            console.error("[CIVORA-FOLDER] load ERROR", e);
            this.state.allDocs = [];
            this.state.docs = [];
            this.state.groupData = null;
        }
        this.state.loading = false;
    }

    // ---- Groupement ----
    async onGroupByChange(ev) {
        this.state.groupBy = ev.target.value;
        await this.load();
    }
    toggleGroup(groupId) {
        this.state.expandedGroups[groupId] = !this.state.expandedGroups[groupId];
    }
    toggleSubgroup(subgroupId) {
        this.state.expandedSubgroups[subgroupId] = !this.state.expandedSubgroups[subgroupId];
    }
    isGroupExpanded(groupId) {
        return this.state.expandedGroups[groupId] !== false;
    }
    isSubgroupExpanded(subgroupId) {
        return this.state.expandedSubgroups[subgroupId] !== false;
    }
    openGroupEntity(group, ev) {
        if (ev) ev.stopPropagation();
        if (!group || !group.entity_id) return;
        if (group.entity_type === "property") {
            this.action.doAction({
                type: "ir.actions.client", tag: "civora.property_360",
                params: { propertyId: group.entity_id }, target: "current",
            });
        } else if (group.entity_type === "partner") {
            this.action.doAction({
                type: "ir.actions.client", tag: "civora.contact_360",
                params: { contactId: group.entity_id }, target: "current",
            });
        }
    }
    groupIcon(entityType) {
        return entityType === "property" ? "fa fa-building-o"
            : entityType === "partner" ? "fa fa-user-circle-o"
            : entityType === "month" ? "fa fa-calendar"
            : "fa fa-folder-o";
    }

    // ---- Recherche dans un contexte groupé ----
    filterGroupDocs(docs) {
        const q = (this.state.search || "").trim().toLowerCase();
        if (!q) return docs;
        return docs.filter((d) =>
            (d.name || "").toLowerCase().includes(q) ||
            (d.reference || "").toLowerCase().includes(q) ||
            (d.res_display || "").toLowerCase().includes(q) ||
            (d.linked_property_name || "").toLowerCase().includes(q) ||
            (d.linked_contact_name || "").toLowerCase().includes(q) ||
            (d.property_owner_name || "").toLowerCase().includes(q) ||
            (d.tag_ids || []).some((t) => (t.name || "").toLowerCase().includes(q))
        );
    }

    onSearchInput(ev) {
        this.state.search = ev.target.value;
        if (!this.state.groupData) {
            this.applyFilter();
        }
        // En mode groupé, le filtrage est appliqué à l'affichage via filterGroupDocs()
    }
    setViewMode(mode) {
        this.state.viewMode = mode;
    }
    applyFilter() {
        const q = (this.state.search || "").trim().toLowerCase();
        if (!q) {
            this.state.docs = this.state.allDocs.slice();
            return;
        }
        this.state.docs = this.state.allDocs.filter((d) =>
            (d.name || "").toLowerCase().includes(q) ||
            (d.reference || "").toLowerCase().includes(q) ||
            (d.res_display || "").toLowerCase().includes(q) ||
            (d.linked_property_name || "").toLowerCase().includes(q) ||
            (d.linked_contact_name || "").toLowerCase().includes(q) ||
            (d.property_owner_name || "").toLowerCase().includes(q) ||
            (d.tag_ids || []).some((t) => (t.name || "").toLowerCase().includes(q))
        );
    }

    // ---- Actions ----
    openHome() {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.documents_home",
            target: "current",
        });
    }
    openDocument(doc) {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.document_detail",
            params: { documentId: doc.id, from: this.folderSlug },
            target: "current",
        });
    }
    openUploadDrawer() {
        this.state.uploadDrawer = true;
    }
    closeUploadDrawer() {
        this.state.uploadDrawer = false;
    }
    async onUploadSaved() {
        this.state.uploadDrawer = false;
        await this.load();
    }

    // ---- Helpers ----
    get folderMeta() {
        return FOLDER_META[this.folderSlug] || {
            name: this.folderSlug, icon: "fa-folder", color: "neutral", description: "",
        };
    }
    docTypeMeta(t) {
        return DOC_TYPE_META[t] || { label: "—", variant: "neutral", icon: "fa-file-o" };
    }
    stateMeta(s) {
        return STATE_META[s] || { label: "—", variant: "neutral" };
    }
    docIcon(d) { return fileIcon(d.file_extension); }
    fmtSize(n) { return fmtSize(n); }
    fmtDate(d) { return fmtDate(d); }
}

registry.category("actions").add("civora.documents_folder", FolderView);
