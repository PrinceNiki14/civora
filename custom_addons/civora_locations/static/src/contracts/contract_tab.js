/** @odoo-module **/
import { Component, onWillStart, useState, useRef, onMounted, markup } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

// ─────────────────────────────────────────────────────────────────────────────
// ContractTab — onglet "Contrat" dans la fiche Bail 360°
// Responsabilités :
//   - charger / créer le contrat lié au bail
//   - afficher aperçu HTML des clauses (avec interpolation serveur)
//   - permettre au bailleur de signer (canvas)
//   - déclencher l'envoi au locataire (inc. E)
// ─────────────────────────────────────────────────────────────────────────────

const STATE_META = {
    draft:          { label: "Brouillon",               variant: "neutral" },
    pending_lessor: { label: "En attente signature",    variant: "warning" },
    signed_lessor:  { label: "Envoyé au locataire",     variant: "info"    },
    signed_tenant:  { label: "Signé des deux parties",  variant: "success" },
    expired:        { label: "Expiré",                  variant: "warning" },
    terminated:     { label: "Rompu",                   variant: "danger"  },
    cancelled:      { label: "Annulé",                  variant: "danger"  },
};

const TERMINATION_REASONS = [
    { key: "mutual_agreement", label: "Accord mutuel des parties" },
    { key: "tenant_notice",    label: "Congé donné par le locataire" },
    { key: "lessor_notice",    label: "Congé donné par le bailleur" },
    { key: "non_payment",      label: "Non-paiement (clause résolutoire)" },
    { key: "breach",           label: "Manquement grave aux obligations" },
    { key: "property_sale",    label: "Vente du bien" },
    { key: "force_majeure",    label: "Force majeure" },
    { key: "other",            label: "Autre motif" },
];

const CONTRACT_FIELDS = [
    "id", "name", "state", "lease_id", "date_issued",
    "signed_at_lessor", "signed_by_lessor", "signed_at_tenant",
    "note", "token",
    "clause_ids", "date_start", "date_end", "is_expired",
    "date_terminated", "termination_reason", "termination_note", "terminated_by",
];

export class ContractTab extends Component {
    static template = "civora_locations.ContractTab";
    static props = {
        leaseId:    { type: Number },
        leaseType:  { type: String },
        tenantName: { type: String, optional: true },
    };

    setup() {
        this.orm         = useService("orm");
        this.action      = useService("action");
        this.notification = useService("notification");
        this.canvasRef   = useRef("signCanvas");

        this.state = useState({
            loading:        true,
            contract:       null,
            clauses:        [],      // [{numero, name, body}] interpolé depuis serveur
            creating:       false,
            signing:        false,   // pad de signature ouvert
            saving:         false,
            sendingEmail:   false,
            isDrawing:      false,
            hasSignature:   false,
            previewMode:    "clauses",  // "clauses" | "financial"
            cancelConfirm:  false,
            // Aperçu façon PDF
            previewOpen:    false,
            previewData:    null,
            previewLoading: false,
            // Historique des contrats précédents
            history:        [],
            historyOpen:    false,
            // Édition des dates du contrat
            editDatesOpen:  false,
            editDatesForm:  { date_start: "", date_end: "" },
            editDatesSaving: false,
            // Rupture de contrat
            terminateOpen:  false,
            terminateForm:  { date_terminated: "", reason: "", note: "" },
            terminateSaving: false,
            terminateReasons: TERMINATION_REASONS,
            // Remarques du locataire
            remarks:        [],
            remarksOpen:    0,
            answering:      0,      // id de la remarque en cours de traitement
            answerText:     "",
            answerSaving:   false,
            // Canaux d'envoi du lien de signature
            channels:       null,
            sending:        "",     // "email" | "sms"
        });

        this._ctx2d    = null;
        this._lastPos  = null;

        onWillStart(() => this.load());
    }

    // ── Chargement ────────────────────────────────────────────────────
    // ── Envoi du lien de signature ──────────────────────────────────
    async _loadChannels() {
        if (!this.state.contract) return;
        try {
            this.state.channels = await this.orm.call(
                "civora.lease.contract", "civora_link_channels",
                [this.state.contract.id]
            );
        } catch (e) {
            console.error("[CIVORA-CONTRACT] channels", e);
            this.state.channels = null;
        }
    }

    channelInfo(kind) {
        return (this.state.channels && this.state.channels[kind])
            || { ok: false, reason: "Vérification en cours…", target: "" };
    }

    channelTitle(kind) {
        const c = this.channelInfo(kind);
        if (!c.ok) return c.reason;
        return kind === "email"
            ? "Envoyer le lien à " + c.target
            : "Envoyer le lien par SMS au " + c.target;
    }

    async sendLink(kind) {
        const info = this.channelInfo(kind);
        if (!info.ok) {
            this.notification.add(info.reason, { type: "warning" });
            return;
        }
        if (this.state.sending) return;
        this.state.sending = kind;
        try {
            const method = kind === "email"
                ? "civora_send_link_email"
                : "civora_send_link_sms";
            const res = await this.orm.call(
                "civora.lease.contract", method, [this.state.contract.id]
            );
            if (res.success) {
                this.notification.add(
                    kind === "email"
                        ? "Lien envoyé par email à " + res.target + "."
                        : "SMS envoyé au " + res.target +
                          " (" + (res.segments || 1) + " segment(s)).",
                    { type: "success" }
                );
            } else {
                this.notification.add(res.error, { type: "danger", sticky: true });
            }
        } catch (e) {
            console.error("[CIVORA-CONTRACT] sendLink", e);
            this.notification.add("Envoi impossible.", { type: "danger" });
        } finally {
            this.state.sending = "";
        }
    }

    // ── Remarques du locataire ──────────────────────────────────────
    async _loadRemarks() {
        if (!this.state.contract) return;
        try {
            const res = await this.orm.call(
                "civora.contract.remark", "civora_get_remarks",
                [this.state.contract.id]
            );
            this.state.remarks = res.rows || [];
            this.state.remarksOpen = res.open || 0;
        } catch (e) {
            console.error("[CIVORA-CONTRACT] remarks", e);
            this.state.remarks = [];
            this.state.remarksOpen = 0;
        }
    }

    startAnswer(remark) {
        this.state.answering = remark.id;
        this.state.answerText = "";
    }
    cancelAnswer() {
        this.state.answering = 0;
        this.state.answerText = "";
    }
    setAnswerText(ev) {
        this.state.answerText = ev.target.value;
    }

    /**
     * Accepte ou refuse une remarque. Une réponse écrite est obligatoire :
     * le locataire doit comprendre la décision, sinon il redéposera la même
     * remarque et la signature restera bloquée.
     */
    async answerRemark(remark, decision) {
        if (this.state.answerSaving) return;
        this.state.answerSaving = true;
        try {
            const res = await this.orm.call(
                "civora.contract.remark", "civora_answer_remark",
                [remark.id, decision, this.state.answerText]
            );
            if (!res.success) {
                this.notification.add(res.error, { type: "warning" });
                return;
            }
            this.state.remarks = res.remarks.rows || [];
            this.state.remarksOpen = res.remarks.open || 0;
            this.cancelAnswer();
            this.notification.add(
                decision === "accepted" ? "Remarque acceptée." : "Remarque refusée.",
                { type: "success" }
            );
        } catch (e) {
            console.error("[CIVORA-CONTRACT] answerRemark", e);
            this.notification.add("Traitement impossible.", { type: "danger" });
        } finally {
            this.state.answerSaving = false;
        }
    }

    async reopenRemark(remark) {
        try {
            const res = await this.orm.call(
                "civora.contract.remark", "civora_reopen_remark", [remark.id]
            );
            if (res.success) {
                this.state.remarks = res.remarks.rows || [];
                this.state.remarksOpen = res.remarks.open || 0;
            }
        } catch (e) {
            console.error("[CIVORA-CONTRACT] reopenRemark", e);
        }
    }

    remarkVariant(state) {
        if (state === "accepted") return "success";
        if (state === "rejected") return "danger";
        return "warning";
    }

    async load() {
        this.state.loading = true;
        // On cherche le contrat le plus récent NON annulé en priorité,
        // sinon le plus récent tout état confondu.
        const active = await this.orm.searchRead(
            "civora.lease.contract",
            [["lease_id", "=", this.props.leaseId], ["state", "!=", "cancelled"]],
            CONTRACT_FIELDS,
            { order: "id desc", limit: 1 }
        );
        if (active.length) {
            this.state.contract = active[0];
            await this._loadClausePreview();
            await this._loadSignatures();
            await this._loadRemarks();
            await this._loadChannels();
        } else {
            // Chercher même un annulé pour l'afficher (avec bouton "Nouveau contrat")
            const any = await this.orm.searchRead(
                "civora.lease.contract",
                [["lease_id", "=", this.props.leaseId]],
                CONTRACT_FIELDS,
                { order: "id desc", limit: 1 }
            );
            this.state.contract = any.length ? any[0] : null;
            if (this.state.contract) {
                await this._loadClausePreview();
                await this._loadSignatures();
            }
        }
        // Charger l'historique des contrats précédents
        await this._loadHistory();
        this.state.loading = false;
    }

    async _loadSignatures() {
        if (!this.state.contract) return;
        try {
            const sigs = await this.orm.call(
                "civora.lease.contract",
                "get_signatures",
                [[this.state.contract.id]]
            );
            // Injecter dans state.contract pour que les templates y accèdent
            this.state.contract.sign_lessor = sigs.sign_lessor || false;
            this.state.contract.sign_tenant = sigs.sign_tenant || false;
        } catch (_) {
            this.state.contract.sign_lessor = false;
            this.state.contract.sign_tenant = false;
        }
    }

    async _loadHistory() {
        try {
            const history = await this.orm.call(
                "civora.lease.contract",
                "get_lease_contracts_history",
                [this.props.leaseId]
            );
            this.state.history = history || [];
        } catch (_) {
            this.state.history = [];
        }
    }

    async _loadClausePreview() {
        if (!this.state.contract) return;
        // Appel RPC vers méthode PUBLIQUE (les _xxx sont bloquées par sécurité Odoo)
        try {
            const rendered = await this.orm.call(
                "civora.lease.contract",
                "render_clauses",
                [[this.state.contract.id]]
            );
            // Marquer les bodies HTML comme sûrs pour que OWL les rende (t-out échappe par défaut)
            this.state.clauses = (rendered || []).map(c => ({
                ...c,
                body: markup(c.body || ""),
            }));
        } catch (_) {
            this.state.clauses = [];
        }
    }

    // ── Créer un nouveau contrat (CTA initial — pas de contrat) ──────
    async createContract() {
        await this._doCreateContract();
    }

    // ── Créer un nouveau contrat (depuis un contrat annulé) ──────────
    async createNewContract() {
        await this._doCreateContract();
    }

    async _doCreateContract() {
        this.state.creating = true;
        try {
            const [lease] = await this.orm.read(
                "civora.lease",
                [this.props.leaseId],
                ["name", "lease_type", "company_id"]
            );
            await this.orm.create("civora.lease.contract", [{
                lease_id:   this.props.leaseId,
                lease_type: lease.lease_type,
                company_id: lease.company_id[0],
            }]);
            await this.load();
            this.notification.add(
                "Contrat créé. Les clauses ont été pré-remplies automatiquement.",
                { type: "success" }
            );
        } catch (e) {
            this.notification.add("Erreur création : " + (e.message || e), { type: "danger" });
        }
        this.state.creating = false;
    }

    // ── Recharger les clauses manuellement ───────────────────────────
    async reloadClauses() {
        if (!this.state.contract) return;
        try {
            await this.orm.call(
                "civora.lease.contract",
                "reload_clauses",
                [[this.state.contract.id]]
            );
            await this.load();
            this.notification.add("Clauses rechargées.", { type: "success" });
        } catch (e) {
            this.notification.add("Erreur : " + (e.message || e), { type: "danger" });
        }
    }

    // ── Soumettre à la signature bailleur ─────────────────────────────
    async submitForSignature() {
        if (!this.state.contract) return;
        try {
            await this.orm.call(
                "civora.lease.contract",
                "action_send_for_lessor_signature",
                [[this.state.contract.id]]
            );
            await this.load();
            this.notification.add("Contrat soumis — veuillez apposer votre signature.", { type: "success" });
        } catch (e) {
            this.notification.add(e.message || "Erreur", { type: "danger" });
        }
    }

    // ── Pad de signature ──────────────────────────────────────────────
    openSignPad() {
        this.state.signing     = true;
        this.state.hasSignature = false;
        // Init canvas au prochain tick (après rendu)
        setTimeout(() => this._initCanvas(), 50);
    }

    _initCanvas() {
        const canvas = this.canvasRef.el;
        if (!canvas) return;
        canvas.width  = canvas.offsetWidth;
        canvas.height = canvas.offsetHeight;
        this._ctx2d = canvas.getContext("2d");
        this._ctx2d.strokeStyle = "#091a36";
        this._ctx2d.lineWidth   = 2.5;
        this._ctx2d.lineCap     = "round";
        this._ctx2d.lineJoin    = "round";
    }

    _getPos(e, canvas) {
        const rect = canvas.getBoundingClientRect();
        const src  = e.touches ? e.touches[0] : e;
        return {
            x: src.clientX - rect.left,
            y: src.clientY - rect.top,
        };
    }

    onPointerDown(e) {
        e.preventDefault();
        this.state.isDrawing = true;
        const canvas = this.canvasRef.el;
        this._lastPos = this._getPos(e, canvas);
        this._ctx2d.beginPath();
        this._ctx2d.moveTo(this._lastPos.x, this._lastPos.y);
    }

    onPointerMove(e) {
        if (!this.state.isDrawing) return;
        e.preventDefault();
        const canvas = this.canvasRef.el;
        const pos    = this._getPos(e, canvas);
        this._ctx2d.lineTo(pos.x, pos.y);
        this._ctx2d.stroke();
        this._lastPos = pos;
        this.state.hasSignature = true;
    }

    onPointerUp(e) {
        this.state.isDrawing = false;
    }

    clearCanvas() {
        const canvas = this.canvasRef.el;
        if (!canvas) return;
        this._ctx2d.clearRect(0, 0, canvas.width, canvas.height);
        this.state.hasSignature = false;
    }

    closeSignPad() {
        this.state.signing = false;
    }

    async saveSignature() {
        if (!this.state.hasSignature) {
            this.notification.add("Veuillez apposer votre signature avant de valider.", { type: "warning" });
            return;
        }
        const canvas  = this.canvasRef.el;
        // Extraire le base64 sans le préfixe data URI
        const dataUrl = canvas.toDataURL("image/png");
        const b64     = dataUrl.split(",")[1];

        this.state.saving = true;
        try {
            await this.orm.call(
                "civora.lease.contract",
                "action_lessor_signed",
                [[this.state.contract.id], b64]
            );
            this.state.signing = false;
            await this.load();
            this.notification.add(
                "Signature enregistrée. Le contrat est prêt à être envoyé au locataire.",
                { type: "success" }
            );
        } catch (e) {
            this.notification.add("Erreur signature : " + (e.message || e), { type: "danger" });
        }
        this.state.saving = false;
    }

    // ── Impression PDF ────────────────────────────────────────────────
    async printContract() {
        if (!this.state.contract) return;
        await this.action.doAction({
            type: "ir.actions.report",
            report_name: "civora_locations.report_lease_contract",
            report_type: "qweb-pdf",
            context: {
                active_ids:  [this.state.contract.id],
                active_model: "civora.lease.contract",
            },
        });
    }

    // ── Copier le lien de signature locataire ─────────────────────────
    async copySignLink() {
        if (!this.state.contract || !this.state.contract.token) return;
        const url = window.location.origin + "/civora/contract/" + this.state.contract.token;
        try {
            await navigator.clipboard.writeText(url);
            this.notification.add("Lien copié dans le presse-papier.", { type: "success" });
        } catch (_) {
            this.notification.add("Lien : " + url, { type: "info" });
        }
    }

    async openWhatsapp() {
        if (!this.state.contract) return;
        const url  = window.location.origin + "/civora/contract/" + this.state.contract.token;
        const msg  = encodeURIComponent(
            "Bonjour " + (this.props.tenantName || "") + ",\n\n" +
            "Votre contrat de bail est prêt à être signé. " +
            "Cliquez sur le lien ci-dessous pour consulter et signer votre contrat :\n\n" +
            url + "\n\nCordialement."
        );
        window.open("https://wa.me/?text=" + msg, "_blank");
    }

    // ── Annulation ────────────────────────────────────────────────────
    requestCancel() { this.state.cancelConfirm = true; }
    cancelConfirmCancel() { this.state.cancelConfirm = false; }

    async confirmCancel() {
        try {
            await this.orm.call(
                "civora.lease.contract", "action_cancel", [[this.state.contract.id]]
            );
            await this.load();
            this.state.cancelConfirm = false;
        } catch (e) {
            this.notification.add(e.message || "Erreur", { type: "danger" });
        }
    }

    async resetDraft() {
        try {
            await this.orm.call(
                "civora.lease.contract", "action_reset_draft", [[this.state.contract.id]]
            );
            await this.load();
        } catch (e) {
            this.notification.add(e.message || "Erreur", { type: "danger" });
        }
    }

    // ── Aperçu façon PDF (modale HTML) ────────────────────────────────
    async openPreview() {
        if (!this.state.contract) return;
        this.state.previewLoading = true;
        this.state.previewOpen = true;
        try {
            const data = await this.orm.call(
                "civora.lease.contract",
                "render_html_preview",
                [[this.state.contract.id]]
            );
            // Marquer les bodies HTML comme sûrs pour que OWL les rende
            if (data && data.clauses) {
                data.clauses = data.clauses.map(c => ({
                    ...c,
                    body: markup(c.body || ""),
                }));
            }
            this.state.previewData = data;
        } catch (e) {
            this.notification.add("Erreur chargement aperçu : " + (e.message || e), { type: "danger" });
            this.state.previewOpen = false;
        }
        this.state.previewLoading = false;
    }

    closePreview() {
        this.state.previewOpen = false;
        this.state.previewData = null;
    }

    // ── Historique ────────────────────────────────────────────────────
    toggleHistory() {
        this.state.historyOpen = !this.state.historyOpen;
    }

    stateLabel(stateCode) {
        return (STATE_META[stateCode] || STATE_META.draft).label;
    }

    stateVariant(stateCode) {
        return (STATE_META[stateCode] || STATE_META.draft).variant;
    }

    // ── Renouvellement (nouveau contrat après expiration) ────────────
    async renewContract() {
        await this._doCreateContract();
    }

    // ── Édition des dates du contrat ─────────────────────────────────
    openEditDates() {
        // Récupérer les dates actuelles depuis le contrat ou depuis le bail
        this.state.editDatesForm = {
            date_start: this.state.contract.date_start || "",
            date_end:   this.state.contract.date_end || "",
        };
        this.state.editDatesOpen = true;
    }

    closeEditDates() {
        this.state.editDatesOpen = false;
    }

    async saveDates() {
        const f = this.state.editDatesForm;
        if (!f.date_start) {
            this.notification.add("La date de début est requise.", { type: "warning" });
            return;
        }
        this.state.editDatesSaving = true;
        try {
            await this.orm.call(
                "civora.lease.contract",
                "action_update_dates",
                [[this.state.contract.id], f.date_start, f.date_end || false]
            );
            await this.load();
            this.state.editDatesOpen = false;
            this.notification.add("Dates du contrat mises à jour.", { type: "success" });
        } catch (e) {
            this.notification.add(e.message || "Erreur", { type: "danger" });
        }
        this.state.editDatesSaving = false;
    }

    get canEditDates() {
        if (!this.state.contract) return false;
        return ["draft", "pending_lessor", "signed_lessor"].includes(this.state.contract.state);
    }

    // ── Rupture de contrat ────────────────────────────────────────────
    get canTerminate() {
        if (!this.state.contract) return false;
        return ["signed_lessor", "signed_tenant"].includes(this.state.contract.state);
    }

    openTerminate() {
        const today = new Date().toISOString().split("T")[0];
        this.state.terminateForm = {
            date_terminated: today,
            reason: "",
            note: "",
        };
        this.state.terminateOpen = true;
    }

    closeTerminate() {
        this.state.terminateOpen = false;
    }

    async saveTerminate() {
        const f = this.state.terminateForm;
        if (!f.date_terminated) {
            this.notification.add("La date de rupture est requise.", { type: "warning" });
            return;
        }
        if (!f.reason) {
            this.notification.add("Le motif de rupture est requis.", { type: "warning" });
            return;
        }
        this.state.terminateSaving = true;
        try {
            await this.orm.call(
                "civora.lease.contract",
                "action_terminate_contract",
                [[this.state.contract.id], f.date_terminated, f.reason, f.note || ""]
            );
            await this.load();
            this.state.terminateOpen = false;
            this.notification.add("Contrat marqué comme rompu.", { type: "success" });
        } catch (e) {
            this.notification.add(e.message || "Erreur", { type: "danger" });
        }
        this.state.terminateSaving = false;
    }

    terminationReasonLabel(key) {
        const r = TERMINATION_REASONS.find(x => x.key === key);
        return r ? r.label : (key || "");
    }

    // ── Getters ───────────────────────────────────────────────────────
    get stateMeta() {
        return STATE_META[this.state.contract?.state] || STATE_META.draft;
    }

    get canSign() {
        return this.state.contract?.state === "pending_lessor";
    }

    get canSend() {
        return this.state.contract?.state === "signed_lessor";
    }

    get contractToken() {
        return this.state.contract?.token || "";
    }

    get signUrl() {
        if (!this.contractToken) return "";
        return window.location.origin + "/civora/contract/" + this.contractToken;
    }
}
