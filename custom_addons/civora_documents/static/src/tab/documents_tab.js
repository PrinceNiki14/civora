import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CivoraBadge } from "@civora_core/components/civora_kit";
import {
    DOC_TYPE_META, STATE_META, fmtSize, fmtDate, fileIcon,
} from "@civora_documents/shared/constants";
import { DocumentDrawer } from "@civora_documents/detail/document_drawer";

/**
 * Onglet Documents générique pour les 360° métier (Bail, Contact, Bien).
 * Utilise get_documents_for_entity avec include_related=true par défaut pour
 * inclure la navigation contextuelle propriétaire ↔ biens ↔ locataires.
 *
 * Props :
 *   resModel        : ex 'civora.lease', 'res.partner', 'civora.property'
 *   resId           : id
 *   includeRelated  : bool (défaut true)
 */
export class DocumentsTab extends Component {
    static template = "civora_documents.DocumentsTab";
    static components = { CivoraBadge, DocumentDrawer };
    static props = {
        resModel: String,
        resId: { type: [Number, Boolean] },
        includeRelated: { type: Boolean, optional: true },
    };
    static defaultProps = { includeRelated: true };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            documents: [],
            total: 0,
            uploadDrawer: false,
        });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        try {
            const res = await this.orm.call(
                "civora.document", "get_documents_for_entity",
                [this.props.resModel, this.props.resId, this.props.includeRelated]
            );
            console.log("[CIVORA-DOC-TAB] load", {
                model: this.props.resModel,
                id: this.props.resId,
                includeRelated: this.props.includeRelated,
                total: res && res.total,
                docs: res && res.documents && res.documents.length,
            });
            this.state.documents = (res && res.documents) || [];
            this.state.total = (res && res.total) || 0;
        } catch (e) {
            console.error("[CIVORA-DOC-TAB] load ERROR", e);
            this.state.documents = [];
            this.state.total = 0;
        }
        this.state.loading = false;
    }

    // ---- Helpers ----
    docTypeMeta(t) { return DOC_TYPE_META[t] || { label: "—", variant: "neutral" }; }
    stateMeta(s) { return STATE_META[s] || { label: "—", variant: "neutral" }; }
    docIcon(d) { return fileIcon(d.file_extension); }
    fmtSize(n) { return fmtSize(n); }
    fmtDate(d) { return fmtDate(d); }

    // ---- Actions ----
    openUpload() { this.state.uploadDrawer = true; }
    closeUpload() { this.state.uploadDrawer = false; }
    async onUploadSaved() {
        this.state.uploadDrawer = false;
        await this.load();
    }
    openDoc(doc) {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.document_detail",
            params: { documentId: doc.id },
            target: "current",
        });
    }
    async deleteDoc(doc, ev) {
        if (ev) ev.stopPropagation();
        if (!confirm(`Supprimer "${doc.name}" ?`)) return;
        await this.orm.unlink("civora.document", [doc.id]);
        await this.load();
    }
}
