import { Component, onWillStart, useRef, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CivoraDrawer } from "@civora_core/components/civora_drawer";
import { fmtSize } from "@civora_documents/shared/constants";

const DOC_TYPES = [
    { value: "bail",           label: "Bail" },
    { value: "mandat",         label: "Mandat" },
    { value: "contrat",        label: "Contrat" },
    { value: "edl",            label: "État des lieux" },
    { value: "facture",        label: "Facture" },
    { value: "quittance",      label: "Quittance" },
    { value: "reporting",      label: "Reporting" },
    { value: "diagnostic",     label: "Diagnostic" },
    { value: "acd",            label: "ACD (Attestation Concession Définitive)" },
    { value: "titre_foncier",  label: "Titre foncier" },
    { value: "plan_cadastral", label: "Plan cadastral / architectural" },
    { value: "cert_propriete", label: "Certificat de propriété" },
    { value: "photo",          label: "Photo" },
    { value: "media",          label: "Média" },
    { value: "autre",          label: "Autre" },
];

const FOLDERS = [
    { value: "baux_contrats",           label: "Baux & contrats" },
    { value: "factures",                label: "Factures" },
    { value: "documents_proprietaires", label: "Documents propriétaires" },
    { value: "documents_locataires",    label: "Documents locataires" },
    { value: "documents_biens",         label: "Documents biens" },
    { value: "medias_photos",           label: "Médias & photos" },
];

const CONFIDENTIALITIES = [
    { value: "publique",       label: "Publique" },
    { value: "interne",        label: "Interne" },
    { value: "confidentielle", label: "Confidentielle" },
    { value: "restreinte",     label: "Restreinte" },
];

const RES_MODELS = [
    { value: "civora.lease",    label: "Bail" },
    { value: "res.partner",     label: "Contact" },
    { value: "civora.property", label: "Bien" },
];

/**
 * Drawer d'upload / édition de documents CIVORA (v2).
 * 3 modes :
 *   1) upload : plusieurs fichiers en drag & drop
 *   2) edit : édition des métadonnées d'un document existant
 *   3) new version : remplacer le fichier d'un document existant
 */
export class DocumentDrawer extends Component {
    static template = "civora_documents.DocumentDrawer";
    static components = { CivoraDrawer };
    static props = {
        doc: { type: [Object, null], optional: true },
        defaultResModel: { type: String, optional: true },
        defaultResId: { type: [Number, Boolean], optional: true },
        defaultFolder: { type: String, optional: true },
        newVersionForDoc: { type: [Number, Boolean], optional: true },
        onClose: Function,
        onSaved: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.docTypes = DOC_TYPES;
        this.folders = FOLDERS;
        this.confidentialities = CONFIDENTIALITIES;
        this.resModels = RES_MODELS;
        this.fileInputRef = useRef("fileInput");
        // Init _defaultEntity SYNCHRONE dès le setup — le label sera résolu
        // dans onWillStart et mis à jour ensuite. Ça garantit que même un
        // drag & drop très rapide propage bien res_model / res_id.
        this._defaultEntity = null;
        if (this.props.defaultResModel && this.props.defaultResId) {
            this._defaultEntity = {
                res_model: this.props.defaultResModel,
                res_id: this.props.defaultResId,
                res_display: "",
            };
        }
        this.state = useState({
            loading: true,
            saving: false,
            error: "",
            allTags: [],
            entityChoices: [],
            files: [],
            form: {
                name: "",
                document_type: "autre",
                folder: this.props.defaultFolder || "",
                confidentiality: "interne",
                res_model: "",
                res_id: false,
                res_display: "",
                linked_property_id: false,
                linked_property_name: "",
                linked_contact_id: false,
                linked_contact_name: "",
                tag_ids: [],
                description: "",
                author: "",
                amount: 0,
            },
            newVersionFile: null,
            newVersionNote: "",
        });
        onWillStart(async () => {
            this.state.allTags = await this.orm.call("civora.document", "get_tags", []);
            if (this.props.doc) {
                const d = this.props.doc;
                this.state.form = {
                    name: d.name || "",
                    document_type: d.document_type || "autre",
                    folder: d.folder || "",
                    confidentiality: d.confidentiality || "interne",
                    res_model: d.res_model || "",
                    res_id: d.res_id || false,
                    res_display: d.res_display || "",
                    linked_property_id: d.linked_property_id || false,
                    linked_property_name: d.linked_property_name || "",
                    linked_contact_id: d.linked_contact_id || false,
                    linked_contact_name: d.linked_contact_name || "",
                    tag_ids: (d.tag_ids || []).map((t) => t.id),
                    description: d.description || "",
                    author: d.author || "",
                    amount: d.amount || 0,
                };
            } else if (this._defaultEntity) {
                // _defaultEntity est déjà initialisé dans setup, on résout juste le label
                const resDisplay = await this._resolveEntityLabel(
                    this._defaultEntity.res_model, this._defaultEntity.res_id
                );
                this._defaultEntity.res_display = resDisplay;
            }
            this.state.loading = false;
        });
    }

    async _resolveEntityLabel(model, id) {
        try {
            const rows = await this.orm.read(model, [id], ["display_name"]);
            return rows && rows[0] ? rows[0].display_name : "";
        } catch (e) { return ""; }
    }

    // ---- Mode helpers ----
    get isEdit() { return !!this.props.doc; }
    get isNewVersion() { return !!this.props.newVersionForDoc; }
    get isUpload() { return !this.isEdit && !this.isNewVersion; }
    get drawerTitle() {
        if (this.isNewVersion) return "Nouvelle version";
        return this.isEdit ? "Éditer le document" : "Ajouter des documents";
    }
    get drawerSubtitle() {
        if (this.isNewVersion) return "Remplacer le fichier — l'ancien restera accessible dans l'historique.";
        return this.isEdit
            ? "Modifier les métadonnées du document"
            : "Glissez vos fichiers ci-dessous ou cliquez pour parcourir.";
    }

    // ---- Files upload ----
    onFileInputChange(ev) {
        this._addFiles(ev.target.files);
        ev.target.value = "";
    }
    openFilePicker() {
        if (this.fileInputRef.el) this.fileInputRef.el.click();
    }
    onDrop(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this._addFiles(ev.dataTransfer.files);
    }
    onDragOver(ev) {
        ev.preventDefault();
        ev.stopPropagation();
    }
    async _addFiles(fileList) {
        const files = Array.from(fileList || []);
        for (const f of files) {
            if (f.size > 25 * 1024 * 1024) {
                this.state.error = `Fichier "${f.name}" trop volumineux (max 25 Mo).`;
                continue;
            }
            const data = await this._readAsBase64(f);
            if (this.isNewVersion) {
                this.state.newVersionFile = {
                    name: f.name, size: f.size,
                    mimetype: f.type || "application/octet-stream", data,
                };
                break;
            }
            this.state.files.push({
                name: f.name,
                size: f.size,
                mimetype: f.type || "application/octet-stream",
                data,
                document_type: this._guessTypeFromName(f.name),
                folder: this.props.defaultFolder || "",
                tag_ids: [],
                res_model: this._defaultEntity ? this._defaultEntity.res_model : "",
                res_id: this._defaultEntity ? this._defaultEntity.res_id : false,
                res_display: this._defaultEntity ? this._defaultEntity.res_display : "",
                description: "",
            });
        }
    }
    _readAsBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve((reader.result || "").split(",")[1] || "");
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }
    _guessTypeFromName(name) {
        const n = (name || "").toLowerCase();
        // Documents biens (spécifiques)
        if (n.includes("acd") || n.includes("attestation") && n.includes("concession")) return "acd";
        if (n.includes("titre") && n.includes("foncier")) return "titre_foncier";
        if (n.includes("cadastr") || (n.includes("plan") && !n.includes("planning"))) return "plan_cadastral";
        if (n.includes("certificat") && (n.includes("proprie") || n.includes("propr"))) return "cert_propriete";
        // Autres
        if (n.includes("bail")) return "bail";
        if (n.includes("mandat")) return "mandat";
        if (n.includes("contrat")) return "contrat";
        if (n.includes("etat") || n.includes("état") || n.includes("edl")) return "edl";
        if (n.includes("facture")) return "facture";
        if (n.includes("quittance")) return "quittance";
        if (n.includes("reporting") || n.includes("rapport")) return "reporting";
        if (n.includes("diagnostic")) return "diagnostic";
        if (n.match(/\.(jpg|jpeg|png|gif|webp)$/)) return "photo";
        if (n.match(/\.(mp4|mov|avi|mkv)$/)) return "media";
        return "autre";
    }
    removeFile(idx) { this.state.files.splice(idx, 1); }
    setFileField(idx, field, ev) { this.state.files[idx][field] = ev.target.value; }
    setFormField(field, ev) { this.state.form[field] = ev.target.value; }
    setNewVersionNote(ev) { this.state.newVersionNote = ev.target.value; }

    // ---- Tags ----
    toggleTagOnForm(tagId) {
        const idx = this.state.form.tag_ids.indexOf(tagId);
        if (idx >= 0) this.state.form.tag_ids.splice(idx, 1);
        else this.state.form.tag_ids.push(tagId);
    }
    toggleTagOnFile(fileIdx, tagId) {
        const arr = this.state.files[fileIdx].tag_ids;
        const idx = arr.indexOf(tagId);
        if (idx >= 0) arr.splice(idx, 1);
        else arr.push(tagId);
    }
    isTagSelectedForm(tagId) {
        return this.state.form.tag_ids.includes(tagId);
    }
    isTagSelectedFile(fileIdx, tagId) {
        return this.state.files[fileIdx].tag_ids.includes(tagId);
    }

    // ---- Entité liée ----
    onSelectResModelForFile(fileIdx, ev) {
        this.state.files[fileIdx].res_model = ev.target.value;
        this.state.files[fileIdx].res_id = false;
        this.state.files[fileIdx].res_display = "";
    }
    onSelectResModelForForm(ev) {
        this.state.form.res_model = ev.target.value;
        this.state.form.res_id = false;
        this.state.form.res_display = "";
    }
    async searchEntities(model, query) {
        if (!model) return [];
        try {
            const domain = query && query.trim() ? [["name", "ilike", query.trim()]] : [];
            const rows = await this.orm.searchRead(model, domain, ["name"], { limit: 15, order: "name" });
            return rows.map((r) => ({ id: r.id, label: r.name || `#${r.id}` }));
        } catch (e) { return []; }
    }
    async onEntityQueryInputForm(ev) {
        this.state.entityChoices = await this.searchEntities(this.state.form.res_model, ev.target.value);
    }
    async onEntityQueryInputFile(fileIdx, ev) {
        this.state.entityChoices = await this.searchEntities(this.state.files[fileIdx].res_model, ev.target.value);
    }
    pickEntityForm(choice) {
        this.state.form.res_id = choice.id;
        this.state.form.res_display = choice.label;
        this.state.entityChoices = [];
    }
    pickEntityFile(fileIdx, choice) {
        this.state.files[fileIdx].res_id = choice.id;
        this.state.files[fileIdx].res_display = choice.label;
        this.state.entityChoices = [];
    }
    clearEntityForm() {
        this.state.form.res_id = false;
        this.state.form.res_display = "";
    }
    clearEntityFile(fileIdx) {
        this.state.files[fileIdx].res_id = false;
        this.state.files[fileIdx].res_display = "";
    }

    // ---- Save ----
    async save() {
        this.state.error = "";
        if (this.isEdit) return this._saveEdit();
        if (this.isNewVersion) return this._saveNewVersion();
        return this._saveUpload();
    }
    async _saveUpload() {
        if (!this.state.files.length) {
            this.state.error = "Ajoutez au moins un fichier.";
            return;
        }
        this.state.saving = true;
        try {
            console.log("[CIVORA-DOC-DRAWER] upload with _defaultEntity:", this._defaultEntity);
            for (const f of this.state.files) {
                const payload = {
                    name: f.name,
                    file_data: f.data,
                    mimetype: f.mimetype,
                    document_type: f.document_type,
                    res_model: f.res_model || false,
                    res_id: f.res_id || false,
                    tag_ids: f.tag_ids,
                    description: f.description,
                };
                if (f.folder) payload.folder = f.folder;
                console.log("[CIVORA-DOC-DRAWER] upload file", {
                    name: f.name, res_model: payload.res_model, res_id: payload.res_id,
                });
                await this.orm.call("civora.document", "upload_document", [payload]);
            }
            this.state.saving = false;
            this.props.onSaved();
        } catch (e) {
            this.state.saving = false;
            this.state.error = "Erreur lors de l'upload.";
            console.error("[CIVORA-DOC-DRAWER] upload ERROR", e);
            throw e;
        }
    }
    async _saveEdit() {
        this.state.saving = true;
        try {
            const vals = {
                name: this.state.form.name,
                document_type: this.state.form.document_type,
                folder: this.state.form.folder,
                confidentiality: this.state.form.confidentiality,
                tag_ids: [(6, 0, this.state.form.tag_ids)],
                description: this.state.form.description,
                author: this.state.form.author,
            };
            if (this.state.form.amount) vals.amount = Number(this.state.form.amount);
            if (this.state.form.res_model && this.state.form.res_id) {
                vals.res_model = this.state.form.res_model;
                vals.res_id = this.state.form.res_id;
            } else {
                vals.res_model = false;
                vals.res_id = 0;
            }
            await this.orm.write("civora.document", [this.props.doc.id], vals);
            this.state.saving = false;
            this.props.onSaved();
        } catch (e) {
            this.state.saving = false;
            this.state.error = "Erreur à l'enregistrement.";
            throw e;
        }
    }
    async _saveNewVersion() {
        if (!this.state.newVersionFile) {
            this.state.error = "Sélectionnez un fichier pour la nouvelle version.";
            return;
        }
        this.state.saving = true;
        try {
            await this.orm.call("civora.document", "upload_new_version", [
                this.props.newVersionForDoc,
                {
                    name: this.state.newVersionFile.name,
                    file_data: this.state.newVersionFile.data,
                    mimetype: this.state.newVersionFile.mimetype,
                    change_note: this.state.newVersionNote,
                },
            ]);
            this.state.saving = false;
            this.props.onSaved();
        } catch (e) {
            this.state.saving = false;
            this.state.error = "Erreur à l'upload de la nouvelle version.";
            throw e;
        }
    }

    fmtSize(n) { return fmtSize(n); }
}
