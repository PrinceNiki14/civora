import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CivoraDrawer } from "@civora_core/components/civora_drawer";

const CHANNELS = [
    { value: "email",    label: "Email" },
    { value: "whatsapp", label: "WhatsApp" },
    { value: "sms",      label: "SMS" },
    { value: "phone",    label: "Appel téléphonique" },
    { value: "letter",   label: "Courrier postal" },
];

const SEVERITIES = [
    { value: "soft",     label: "Léger (1-15j)" },
    { value: "moderate", label: "Modéré (15-30j)" },
    { value: "firm",     label: "Ferme (30j+)" },
    { value: "legal",    label: "Mise en demeure" },
];

// Modèles pré-rédigés par sévérité. Les placeholders {periods} et {days}
// sont remplacés par les données de contexte au moment du rendu.
/**
 * Modeles de repli, utilises uniquement si le serveur est injoignable.
 * La source de verite est civora.lease.reminder.civora_get_templates(),
 * qui signe les messages du nom REEL de l'agence : sur un produit en
 * marque blanche, un locataire ne doit jamais lire "CIVORA".
 */
const SUBJECT_TEMPLATES = {
    soft:     "Rappel amiable : loyer {periods} en attente",
    moderate: "Relance : régularisation loyer {periods} — {days} jours de retard",
    firm:     "Relance ferme : loyer {periods} impayé depuis {days} jours",
    legal:    "Mise en demeure : impayé locatif ({periods}, {days} jours de retard)",
};

const BODY_TEMPLATES = {
    soft: "Bonjour,\n\nNous constatons que votre loyer pour la période {periods} " +
          "présente un retard de paiement de {days} jour(s). " +
          "Il s'agit sans doute d'un simple oubli — nous vous invitons à régulariser " +
          "votre situation dès que possible.\n\nCordialement,\nL'équipe CIVORA",
    moderate: "Bonjour,\n\nMalgré notre précédent rappel, votre loyer pour {periods} " +
              "reste impayé ({days} jour(s) de retard). " +
              "Merci de bien vouloir procéder à la régularisation sous 7 jours ou de " +
              "nous contacter pour convenir d'un échéancier.\n\nCordialement,\nL'équipe CIVORA",
    firm: "Bonjour,\n\nVotre situation locative présente un retard significatif " +
          "de {days} jour(s) sur la période {periods}. " +
          "Nous vous demandons de régulariser sans délai sous peine d'ouverture d'une " +
          "procédure formelle.\n\nCordialement,\nL'équipe CIVORA",
    legal: "Objet : MISE EN DEMEURE\n\nMonsieur/Madame,\n\nNous vous mettons formellement " +
           "en demeure de régler la somme due au titre de votre loyer pour la période " +
           "{periods}, en retard de {days} jour(s), dans un délai de " +
           "15 jours à compter de la réception de la présente. À défaut, nous serons " +
           "contraints d'engager les procédures légales prévues.\n\nCordialement,\nL'équipe CIVORA",
};

/**
 * Formate les périodes à insérer dans le message.
 * "janvier 2026" pour 1 période, "janvier 2026, février 2026" pour plusieurs,
 * "janvier 2026 à mars 2026" pour 3+ consécutives.
 */
function formatPeriods(periods) {
    if (!periods || !periods.length) return "en cours";
    if (periods.length === 1) return periods[0].period_label || "en cours";
    if (periods.length <= 3) return periods.map((p) => p.period_label).join(", ");
    return `${periods[0].period_label} à ${periods[periods.length - 1].period_label}`;
}

function maxDays(periods) {
    if (!periods || !periods.length) return 0;
    return Math.max(...periods.map((p) => p.days_overdue || 0));
}

/**
 * Drawer de préparation d'une relance.
 * L'agent choisit canal + sévérité, ajuste sujet et corps (pré-remplis),
 * puis peut soit sauvegarder en brouillon, soit marquer immédiatement comme envoyée.
 */
export class ReminderDrawer extends Component {
    static template = "civora_locations.ReminderDrawer";
    static components = { CivoraDrawer };
    static props = {
        leaseId: { type: [Number, Boolean] },
        preselectedInstallmentIds: { type: Array, optional: true },
        defaultContext: { type: [Object, Boolean, null], optional: true },
        onClose: Function,
        onSaved: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.channels = CHANNELS;
        this.serverTemplates = null;
        this.severities = SEVERITIES;
        // Contexte fourni par le parent (sévérité + périodes concernées).
        // Si absent, on utilise des valeurs neutres.
        const ctx = this.props.defaultContext || {};
        const initialSeverity = ctx.severity || "soft";
        this.periods = ctx.periods || [];
        this.state = useState({
            loading: true,
            saving: false,
            error: "",
            // Prérequis d'envoi email
            emailInfo: { ok: false, company_email: "", tenant_email: "", tenant_name: "", errors: [] },
            // Étape de confirmation avant envoi réel (canal email uniquement)
            confirmSend: false,
            form: {
                channel: "email",
                severity: initialSeverity,
                subject: this._renderTemplate(SUBJECT_TEMPLATES[initialSeverity]),
                body: this._renderTemplate(BODY_TEMPLATES[initialSeverity]),
            },
        });
        onWillStart(async () => {
            try {
                const [emailInfo, templates] = await Promise.all([
                    this.orm.call(
                        "civora.lease.reminder", "check_email_prerequisites",
                        [this.props.leaseId]
                    ),
                    this.orm.call(
                        "civora.lease.reminder", "civora_get_templates",
                        [this.props.leaseId]
                    ),
                ]);
                this.state.emailInfo = emailInfo;
                // Les modeles serveur sont deja rendus (nom d'agence, montant,
                // periodes) : ils remplacent les modeles de repli.
                if (templates && templates[initialSeverity]) {
                    this.serverTemplates = templates;
                    this.state.form.subject = templates[initialSeverity].subject;
                    this.state.form.body = templates[initialSeverity].body;
                }
            } catch (e) {
                this.state.emailInfo = {
                    ok: false, company_email: "", tenant_email: "", tenant_name: "",
                    errors: ["Impossible de vérifier les prérequis d'envoi."],
                };
            }
            this.state.loading = false;
        });
    }

    /**
     * Remplace les placeholders {periods} et {days} dans un template
     * avec les données du contexte fourni.
     */
    _serverTemplate(severity, kind) {
        const t = this.serverTemplates && this.serverTemplates[severity];
        return t ? t[kind] : null;
    }

    _renderTemplate(tpl) {
        if (!tpl) return "";
        const periods = formatPeriods(this.periods);
        const days = maxDays(this.periods);
        return tpl
            .replace(/\{periods\}/g, periods)
            .replace(/\{days\}/g, days || "quelques");
    }

    // ---- Setters ----
    setField(field, ev) {
        this.state.form[field] = ev.target.value;
    }
    onSeverityChange(ev) {
        const v = ev.target.value;
        const oldSeverity = this.state.form.severity;
        this.state.form.severity = v;
        // Templates *rendus* pour l'ancienne sévérité — si le sujet/corps
        // actuel correspond, on considère que l'utilisateur n'a pas personnalisé
        // et on peut swap. Sinon on garde la modification manuelle.
        const oldSubjectRendered =
            this._serverTemplate(oldSeverity, "subject") ||
            this._renderTemplate(SUBJECT_TEMPLATES[oldSeverity]);
        const oldBodyRendered =
            this._serverTemplate(oldSeverity, "body") ||
            this._renderTemplate(BODY_TEMPLATES[oldSeverity]);
        if (this.state.form.subject === oldSubjectRendered) {
            this.state.form.subject =
                this._serverTemplate(v, "subject") ||
                this._renderTemplate(SUBJECT_TEMPLATES[v]);
        }
        if (this.state.form.body === oldBodyRendered) {
            this.state.form.body =
                this._serverTemplate(v, "body") ||
                this._renderTemplate(BODY_TEMPLATES[v]);
        }
    }

    validate() {
        const f = this.state.form;
        if (!f.subject || !f.subject.trim()) return "Le sujet est requis.";
        if (!f.channel) return "Sélectionnez un canal.";
        if (!f.severity) return "Sélectionnez une sévérité.";
        return "";
    }

    // ---- Libellés dynamiques du bouton d'envoi ----
    get isEmail() {
        return this.state.form.channel === "email";
    }
    get canSendEmail() {
        return this.isEmail && this.state.emailInfo.ok;
    }
    get sendButtonLabel() {
        if (this.isEmail) return "Enregistrer et envoyer par email";
        return "Enregistrer et marquer envoyée";
    }
    get sendButtonIcon() {
        if (this.state.saving) return "fa fa-circle-o-notch fa-spin";
        return this.isEmail ? "fa fa-envelope" : "fa fa-paper-plane";
    }

    // ---- Flow de confirmation avant envoi email ----
    openConfirmSend() {
        this.state.error = "";
        const err = this.validate();
        if (err) {
            this.state.error = err;
            return;
        }
        // Pour les canaux non-email : pas de confirmation, envoi direct
        if (!this.isEmail) {
            this.saveAndSend();
            return;
        }
        // Pour email : vérifier prérequis, sinon afficher erreurs
        if (!this.state.emailInfo.ok) {
            this.state.error = this.state.emailInfo.errors.join(" ");
            return;
        }
        this.state.confirmSend = true;
    }
    cancelConfirmSend() {
        this.state.confirmSend = false;
    }
    async confirmAndSend() {
        this.state.confirmSend = false;
        await this.saveAndSend();
    }

    async _createReminder(markAsSent) {
        const err = this.validate();
        if (err) {
            this.state.error = err;
            return;
        }
        this.state.error = "";
        this.state.saving = true;
        try {
            const vals = {
                channel: this.state.form.channel,
                severity: this.state.form.severity,
                subject: this.state.form.subject.trim(),
                body: this.state.form.body || "",
                installment_ids: this.props.preselectedInstallmentIds || [],
            };
            const reminderId = await this.orm.call(
                "civora.lease", "create_reminder",
                [this.props.leaseId, vals]
            );
            if (markAsSent && reminderId) {
                await this.orm.call(
                    "civora.lease.reminder", "action_mark_sent", [[reminderId]]
                );
            }
            this.state.saving = false;
            this.props.onSaved();
        } catch (e) {
            this.state.saving = false;
            this.state.error = "Erreur lors de l'enregistrement de la relance.";
            throw e;
        }
    }

    async saveDraft() {
        await this._createReminder(false);
    }

    async saveAndSend() {
        await this._createReminder(true);
    }

    get drawerTitle() { return "Préparer une relance"; }
    get drawerSubtitle() {
        const n = (this.props.preselectedInstallmentIds || []).length;
        if (n > 0) return n + " échéance(s) associée(s) à cette relance";
        return "Communiquer avec le locataire au sujet des impayés";
    }
}
