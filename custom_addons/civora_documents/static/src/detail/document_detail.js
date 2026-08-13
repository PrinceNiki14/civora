import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";
import { CivoraBadge, CivoraAvatar } from "@civora_core/components/civora_kit";
import {
    DOC_TYPE_META, STATE_META, CONFIDENTIALITY_META, FOLDER_META,
    fmtSize, fmtDate, fmtDateTime, fileIcon, downloadUrl,
} from "@civora_documents/shared/constants";
import { DocumentPreview } from "./document_preview";
import { DocumentDrawer } from "./document_drawer";

/**
 * Fiche 360° d'un document CIVORA.
 * 4 onglets alignés front CIVORA : Vue d'ensemble / Versions / Signatures / Audit.
 */
export class DocumentDetail extends Component {
    static template = "civora_documents.DocumentDetail";
    static components = {
        CivoraStatCard, CivoraBadge, CivoraAvatar,
        DocumentPreview, DocumentDrawer,
    };
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        const params = (this.props.action && this.props.action.params) || {};
        this.documentId = params.documentId;
        this.fromFolder = params.from || null;
        this.state = useState({
            loading: true,
            activeTab: "overview",
            doc: null,
            versions: [],
            signers: [],
            auditEvents: [],
            editDrawer: false,
            newVersionMode: false,
            newSignerForm: { name: "", email: "", role: "locataire" },
            addSignerOpen: false,
        });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        try {
            const [docRes, versions, signers, audit] = await Promise.all([
                this.orm.call("civora.document", "search_documents",
                    [[["id", "=", this.documentId]]], { limit: 1 }),
                this.orm.call("civora.document", "get_versions", [this.documentId]),
                this.orm.call("civora.document", "get_signers", [this.documentId]),
                this.orm.call("civora.document", "get_audit_events", [this.documentId]),
            ]);
            this.state.doc = (docRes.documents && docRes.documents[0]) || null;
            this.state.versions = versions || [];
            this.state.signers = signers || [];
            this.state.auditEvents = audit || [];
            // Log consultation (fire and forget)
            if (this.state.doc) {
                this.orm.call("civora.document", "log_view", [this.documentId]).catch(() => {});
            }
        } catch (e) {
            this.state.doc = null;
        }
        this.state.loading = false;
    }

    // ---- Navigation ----
    goHome() {
        this.action.doAction({
            type: "ir.actions.client", tag: "civora.documents_home", target: "current",
        });
    }
    goFolder() {
        if (!this.fromFolder) return this.goHome();
        this.action.doAction({
            type: "ir.actions.client", tag: "civora.documents_folder",
            params: { folder: this.fromFolder }, target: "current",
        });
    }
    setTab(id) {
        this.state.activeTab = id;
    }
    openEntity() {
        const doc = this.state.doc;
        if (!doc) return;
        if (doc.linked_property_id) {
            this.action.doAction({
                type: "ir.actions.client", tag: "civora.property_360",
                params: { propertyId: doc.linked_property_id }, target: "current",
            });
        } else if (doc.linked_contact_id) {
            this.action.doAction({
                type: "ir.actions.client", tag: "civora.contact_360",
                params: { contactId: doc.linked_contact_id }, target: "current",
            });
        } else if (doc.res_model === "civora.lease" && doc.res_id) {
            this.action.doAction({
                type: "ir.actions.client", tag: "civora.lease_360",
                params: { leaseId: doc.res_id }, target: "current",
            });
        }
    }
    openOwner() {
        if (!this.state.doc || !this.state.doc.property_owner_id) return;
        this.action.doAction({
            type: "ir.actions.client", tag: "civora.contact_360",
            params: { contactId: this.state.doc.property_owner_id }, target: "current",
        });
    }
    openTenant() {
        if (!this.state.doc || !this.state.doc.property_tenant_id) return;
        this.action.doAction({
            type: "ir.actions.client", tag: "civora.contact_360",
            params: { contactId: this.state.doc.property_tenant_id }, target: "current",
        });
    }

    // ---- Actions ----
    openEdit() { this.state.editDrawer = true; }
    async onEditSaved() {
        this.state.editDrawer = false;
        await this.load();
    }
    async validate() {
        await this.orm.call("civora.document", "action_validate", [[this.documentId]]);
        await this.load();
    }
    async archive() {
        if (!confirm("Archiver ce document ?")) return;
        await this.orm.call("civora.document", "action_archive", [[this.documentId]]);
        await this.load();
    }
    async delete_() {
        if (!confirm(`Supprimer définitivement "${this.state.doc.name}" ?`)) return;
        await this.orm.unlink("civora.document", [this.documentId]);
        this.goHome();
    }
    onDownload() {
        this.orm.call("civora.document", "log_download", [this.documentId]).catch(() => {});
    }
    openNewVersion() { this.state.newVersionMode = true; }
    closeNewVersion() { this.state.newVersionMode = false; }
    async onNewVersionSaved() {
        this.state.newVersionMode = false;
        await this.load();
    }

    // ---- Signataires ----
    openAddSigner() {
        this.state.addSignerOpen = true;
        this.state.newSignerForm = { name: "", email: "", role: "locataire" };
    }
    closeAddSigner() { this.state.addSignerOpen = false; }
    setSignerField(field, ev) {
        this.state.newSignerForm[field] = ev.target.value;
    }
    async submitAddSigner() {
        const f = this.state.newSignerForm;
        if (!f.name.trim()) return;
        await this.orm.call("civora.document", "add_signer", [this.documentId, {
            name: f.name.trim(),
            email: f.email.trim(),
            role: f.role,
        }]);
        this.state.addSignerOpen = false;
        await this.load();
    }
    async markSigned(signerId) {
        await this.orm.call("civora.document.signer", "action_mark_signed", [[signerId]]);
        await this.load();
    }

    // ---- Helpers ----
    docTypeMeta() {
        return DOC_TYPE_META[this.state.doc.document_type] || { label: "—", variant: "neutral", icon: "fa-file-o" };
    }
    stateMeta() {
        return STATE_META[this.state.doc.state] || { label: "—", variant: "neutral" };
    }
    confMeta() {
        return CONFIDENTIALITY_META[this.state.doc.confidentiality] || { label: "—", variant: "neutral" };
    }
    folderMeta() {
        return FOLDER_META[this.state.doc.folder] || { name: this.state.doc.folder, icon: "fa-folder", color: "neutral" };
    }
    docIcon() { return fileIcon(this.state.doc.file_extension); }
    signerStateVariant(state) {
        return { signed: "success", pending: "warning", refused: "danger", expired: "neutral" }[state] || "neutral";
    }
    auditToneClass(action) {
        const map = {
            create: "info", view: "info", download: "accent",
            share: "info", new_version: "info",
            state_change: "info", sign_request: "warning",
            sign_done: "success", sign_refused: "danger",
        };
        return "civora-docdet-audit-tone-" + (map[action] || "neutral");
    }
    fmtSize(n) { return fmtSize(n); }
    fmtDate(d) { return fmtDate(d); }
    fmtDateTime(d) { return fmtDateTime(d); }
    downloadUrl() { return downloadUrl(this.state.doc && this.state.doc.attachment_id); }

    get tabList() {
        return [
            { id: "overview", label: "Vue d'ensemble" },
            { id: "versions", label: "Versions", count: this.state.versions.length },
            { id: "signatures", label: "Signatures", count: this.state.signers.length },
            { id: "audit", label: "Audit" },
        ];
    }

    get canBeSigned() {
        const t = this.state.doc && this.state.doc.document_type;
        return t === "bail" || t === "mandat" || t === "contrat";
    }

    // Compte signés / en attente
    get signedCount() {
        return this.state.signers.filter((s) => s.state === "signed").length;
    }
    get pendingCount() {
        return this.state.signers.length - this.signedCount;
    }
    get signedRatio() {
        if (!this.state.signers.length) return "0%";
        return Math.round(this.signedCount / this.state.signers.length * 100) + "%";
    }
}

registry.category("actions").add("civora.document_detail", DocumentDetail);
