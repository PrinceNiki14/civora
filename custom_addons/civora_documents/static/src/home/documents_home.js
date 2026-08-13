import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";
import { CivoraBadge } from "@civora_core/components/civora_kit";
import {
    DOC_TYPE_META, STATE_META, FOLDER_META,
    fmtSize, fmtDate, fileIcon,
} from "@civora_documents/shared/constants";
import { DocumentDrawer } from "@civora_documents/detail/document_drawer";

/**
 * Écran d'accueil Documents (aligné front CIVORA).
 *
 * Reproduit la page /documents du référentiel React :
 * - 4 KPI cards
 * - Barre de recherche
 * - 6 dossiers canoniques (folders)
 * - Section "Documents récents"
 */
export class DocumentsHome extends Component {
    static template = "civora_documents.DocumentsHome";
    static components = { CivoraStatCard, CivoraBadge, DocumentDrawer };
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        // Ordre des 6 dossiers canoniques — aligné front
        this.folderSlugs = [
            "baux_contrats", "factures",
            "documents_proprietaires", "documents_locataires",
            "documents_biens", "medias_photos",
        ];
        this.state = useState({
            loading: true,
            search: "",
            kpis: {
                total: 0, this_month: 0, classified_pct: 0,
                pending_signatures: 0, total_size_fmt: "0 o",
            },
            folders: [],
            recentDocs: [],
            uploadDrawer: false,
            viewMode: "grid",  // défaut Grille pour docs récents
        });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        try {
            const [kpis, foldersSummary, recent] = await Promise.all([
                this.orm.call("civora.document", "get_library_kpis", []),
                this.orm.call("civora.document", "get_folders_summary", []),
                this.orm.call("civora.document", "search_documents", [[]], { limit: 6 }),
            ]);
            this.state.kpis = kpis || this.state.kpis;
            this.state.folders = foldersSummary || [];
            this.state.recentDocs = recent.documents || [];
        } catch (e) {
            // silent — l'utilisateur verra des zéros
        }
        this.state.loading = false;
    }

    // ---- Actions ----
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
    openFolder(slug) {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.documents_folder",
            params: { folder: slug },
            target: "current",
        });
    }
    openDocument(doc) {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.document_detail",
            params: { documentId: doc.id },
            target: "current",
        });
    }
    onSearchInput(ev) {
        this.state.search = ev.target.value;
    }
    setViewMode(mode) {
        this.state.viewMode = mode;
    }
    onSearchSubmit(ev) {
        if (ev.key === "Enter" && this.state.search.trim()) {
            // Navigation vers un dossier "recherche" — pour l'instant on va vers baux
            // Idéalement on aurait un écran de résultats de recherche global
            this.action.doAction({
                type: "ir.actions.client",
                tag: "civora.documents_folder",
                params: { folder: "baux_contrats", search: this.state.search },
                target: "current",
            });
        }
    }

    // ---- Helpers ----
    folderMeta(slug) {
        return FOLDER_META[slug] || { name: slug, icon: "fa-folder", color: "neutral", description: "" };
    }
    docTypeMeta(t) {
        return DOC_TYPE_META[t] || { label: "—", variant: "neutral", icon: "fa-file-o" };
    }
    stateMeta(s) {
        return STATE_META[s] || { label: "—", variant: "neutral" };
    }
    docIcon(d) {
        return fileIcon(d.file_extension);
    }
    fmtSize(n) { return fmtSize(n); }
    fmtDate(d) { return fmtDate(d); }
}

registry.category("actions").add("civora.documents_home", DocumentsHome);
