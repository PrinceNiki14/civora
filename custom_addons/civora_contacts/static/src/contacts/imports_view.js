/* @odoo-module */
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CivoraBadge } from "@civora_core/components/civora_kit";

/**
 * Onglet "Imports & API" de l'écran Contacts.
 * Workflow :
 * 1. Utilisateur dépose un CSV/Excel via drag & drop ou parcourt un fichier
 * 2. Backend parse et renvoie preview + mapping automatique proposé
 * 3. Utilisateur ajuste le mapping si besoin (drag & drop de colonnes → champs)
 * 4. Import lancé avec option "Ignorer les doublons"
 * 5. Résumé (créés / doublons / erreurs) + entrée dans l'historique
 */
export class ContactsImportsView extends Component {
    static template = "civora_contacts.ImportsView";
    static components = { CivoraBadge };
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            // Workflow : 'idle' | 'previewing' | 'preview_ready' | 'importing' | 'done'
            step: "idle",
            // Fichier
            fileName: "",
            fileB64: "",
            fileSize: 0,
            // Preview
            headers: [],
            preview: [],
            totalRows: 0,
            availableFields: [],
            // Mapping : { "col_index": "champ_civora" }
            mapping: {},
            // Options
            skipDuplicates: true,
            // Résumé
            summary: null,
            // Historique
            history: [],
            historyLoading: false,
            // Erreurs
            error: "",
            dragActive: false,
        });

        onWillStart(() => this.loadHistory());
    }

    async loadHistory() {
        this.state.historyLoading = true;
        try {
            this.state.history = await this.orm.call(
                "res.partner", "civora_get_import_history",
                [], { limit: 10 }
            );
        } catch (e) {
            console.error("[CIVORA-IMPORT] history", e);
        } finally {
            this.state.historyLoading = false;
        }
    }

    // ---- Télécharger le modèle CSV ----
    async downloadTemplate() {
        try {
            const res = await this.orm.call(
                "res.partner", "civora_import_template", []
            );
            if (!res || !res.content) {
                this.notification.add("Impossible de générer le modèle.", { type: "danger" });
                return;
            }
            const link = document.createElement("a");
            link.href = "data:text/csv;charset=utf-8;base64," + res.content;
            link.download = res.filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            this.notification.add("Modèle téléchargé. Remplissez-le puis déposez-le dans la zone.",
                { type: "success", sticky: false });
        } catch (e) {
            console.error("[CIVORA-IMPORT] template", e);
            this.notification.add("Erreur lors du téléchargement du modèle.", { type: "danger" });
        }
    }

    // ---- File input ----
    onDragEnter(ev) { ev.preventDefault(); this.state.dragActive = true; }
    onDragLeave(ev) { ev.preventDefault(); this.state.dragActive = false; }
    onDragOver(ev) { ev.preventDefault(); }
    onDrop(ev) {
        ev.preventDefault();
        this.state.dragActive = false;
        const files = ev.dataTransfer && ev.dataTransfer.files;
        if (files && files.length) this._handleFile(files[0]);
    }
    onFileChange(ev) {
        const files = ev.target.files;
        if (files && files.length) this._handleFile(files[0]);
    }
    async _handleFile(file) {
        this.state.error = "";
        this.state.fileName = file.name;
        this.state.fileSize = file.size;
        this.state.step = "previewing";
        // Lire en base64
        try {
            const b64 = await this._fileToB64(file);
            this.state.fileB64 = b64;
            const res = await this.orm.call(
                "res.partner", "civora_import_preview",
                [], { file_base64: b64, filename: file.name }
            );
            if (!res.success) {
                this.state.error = res.error || "Erreur inconnue.";
                this.state.step = "idle";
                return;
            }
            this.state.headers = res.headers;
            this.state.preview = res.preview;
            this.state.totalRows = res.total_rows;
            this.state.availableFields = res.available_fields;
            this.state.mapping = res.mapping || {};
            this.state.step = "preview_ready";
        } catch (e) {
            console.error("[CIVORA-IMPORT] preview", e);
            this.state.error = "Erreur de traitement du fichier.";
            this.state.step = "idle";
        }
    }
    _fileToB64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => {
                const s = reader.result;
                const idx = s.indexOf(",");
                resolve(idx >= 0 ? s.slice(idx + 1) : s);
            };
            reader.onerror = () => reject(reader.error);
            reader.readAsDataURL(file);
        });
    }

    // ---- Mapping ----
    setMapping(colIdx, ev) {
        const field = ev.target.value;
        if (field) {
            this.state.mapping[String(colIdx)] = field;
        } else {
            delete this.state.mapping[String(colIdx)];
        }
    }
    getMapping(colIdx) {
        return this.state.mapping[String(colIdx)] || "";
    }

    toggleSkipDuplicates(ev) {
        this.state.skipDuplicates = ev.target.checked;
    }

    hasNameMapping() {
        return Object.values(this.state.mapping).includes("name");
    }

    // ---- Import ----
    async runImport() {
        if (!this.hasNameMapping()) {
            this.state.error = "Vous devez mapper au moins la colonne 'Nom'.";
            return;
        }
        this.state.step = "importing";
        this.state.error = "";
        try {
            const res = await this.orm.call(
                "res.partner", "civora_import_run",
                [], {
                    file_base64: this.state.fileB64,
                    filename: this.state.fileName,
                    mapping: this.state.mapping,
                    skip_duplicates: this.state.skipDuplicates,
                }
            );
            if (!res.success) {
                this.state.error = res.error || "Erreur inconnue.";
                this.state.step = "preview_ready";
                return;
            }
            this.state.summary = res;
            this.state.step = "done";
            this.notification.add(
                `Import terminé : ${res.imported} créés, ${res.duplicates} doublons ignorés, ${res.errors} erreur(s).`,
                { type: res.errors > 0 ? "warning" : "success", sticky: true }
            );
            await this.loadHistory();
        } catch (e) {
            console.error("[CIVORA-IMPORT] run", e);
            this.state.error = "Erreur lors de l'import.";
            this.state.step = "preview_ready";
        }
    }

    reset() {
        this.state.step = "idle";
        this.state.fileName = "";
        this.state.fileB64 = "";
        this.state.fileSize = 0;
        this.state.headers = [];
        this.state.preview = [];
        this.state.totalRows = 0;
        this.state.mapping = {};
        this.state.summary = null;
        this.state.error = "";
    }

    // ---- Helpers ----
    fmtSize(bytes) {
        if (!bytes) return "";
        if (bytes < 1024) return bytes + " B";
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " Ko";
        return (bytes / (1024 * 1024)).toFixed(1) + " Mo";
    }
    fmtDate(s) {
        if (!s) return "";
        const d = new Date(s);
        if (isNaN(d)) return s;
        return d.toLocaleDateString("fr-FR") + " " +
               String(d.getHours()).padStart(2, "0") + ":" +
               String(d.getMinutes()).padStart(2, "0");
    }
    stateLabel(s) {
        const M = {
            draft: "Brouillon", preview: "Aperçu", running: "En cours",
            done: "Terminé", error: "Erreur",
        };
        return M[s] || s;
    }
    stateVariant(s) {
        const M = {
            draft: "neutral", preview: "info", running: "warning",
            done: "success", error: "danger",
        };
        return M[s] || "neutral";
    }
    colHeader(idx) {
        return this.state.headers[idx] || `Colonne ${idx + 1}`;
    }
}
