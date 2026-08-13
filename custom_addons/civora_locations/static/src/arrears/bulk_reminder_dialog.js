import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CivoraDrawer } from "@civora_core/components/civora_drawer";

const CHANNELS = [
    { value: "email", label: "Email", icon: "fa-envelope" },
    { value: "sms", label: "SMS", icon: "fa-mobile" },
];

const SEVERITIES = [
    { value: "", label: "Automatique (selon l'ancienneté de chaque retard)" },
    { value: "soft", label: "Léger — rappel amiable" },
    { value: "moderate", label: "Modéré — régularisation sous 7 jours" },
    { value: "firm", label: "Ferme — avant procédure" },
];

/**
 * Relance groupee.
 *
 * Trois garde-fous, tous deliberes :
 * 1. Le previsualisation est calculee cote SERVEUR avant tout envoi, pour
 *    que le gestionnaire voie exactement qui est exclu et pourquoi.
 * 2. La severite est "Automatique" par defaut : relancer un retard de
 *    5 jours du meme ton qu'un retard de 90 jours abime la relation dans
 *    un cas et la credibilite de l'agence dans l'autre.
 * 3. Confirmation en 2 clics avec temporisation, comme toute action
 *    irreversible de CIVORA. Un email parti ne se rattrape pas.
 */
export class BulkReminderDialog extends Component {
    static template = "civora_locations.BulkReminderDialog";
    static components = { CivoraDrawer };
    static props = {
        leaseIds: { type: Array },
        onClose: Function,
        onDone: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.channels = CHANNELS;
        this.severities = SEVERITIES;
        this.confirmTimer = null;

        this.state = useState({
            loading: true,
            sending: false,
            error: "",
            channel: "email",
            severity: "",
            preview: null,
            showExcluded: false,
            confirming: false,
        });

        onWillStart(async () => {
            await this.loadPreview();
        });
    }

    willUnmount() {
        if (this.confirmTimer) clearTimeout(this.confirmTimer);
    }

    async loadPreview() {
        this.state.loading = true;
        this.state.error = "";
        this._cancelConfirm();
        try {
            this.state.preview = await this.orm.call(
                "civora.lease.reminder",
                "civora_bulk_preview",
                [this.props.leaseIds, this.state.channel]
            );
        } catch (e) {
            console.error("[CIVORA-BULK] preview", e);
            this.state.error = "Impossible de préparer l'envoi groupé.";
            this.state.preview = null;
        }
        this.state.loading = false;
    }

    async setChannel(v) {
        if (this.state.channel === v) return;
        this.state.channel = v;
        // Les exclusions dependent du canal : sans email n'exclut pas du SMS.
        await this.loadPreview();
    }

    setSeverity(ev) {
        this.state.severity = ev.target.value;
    }

    toggleExcluded() {
        this.state.showExcluded = !this.state.showExcluded;
    }

    // ── Formatage ──────────────────────────────────────────────────────
    fmtMoney(v) {
        const n = Math.round(v || 0);
        return n.toLocaleString("fr-FR").replace(/\u202f|\u00a0/g, " ") + " F";
    }

    get canSend() {
        const p = this.state.preview;
        return !!(p && p.channel_ready && p.eligible_count > 0 && !this.state.sending);
    }

    // ── Confirmation 2 clics ───────────────────────────────────────────
    _cancelConfirm() {
        this.state.confirming = false;
        if (this.confirmTimer) {
            clearTimeout(this.confirmTimer);
            this.confirmTimer = null;
        }
    }

    async onSendClick() {
        if (!this.canSend) return;
        if (!this.state.confirming) {
            this.state.confirming = true;
            this.confirmTimer = setTimeout(() => this._cancelConfirm(), 5000);
            return;
        }
        this._cancelConfirm();
        await this.send();
    }

    async send() {
        this.state.sending = true;
        this.state.error = "";
        try {
            const ids = this.state.preview.eligible.map((r) => r.lease_id);
            const res = await this.orm.call(
                "civora.lease.reminder",
                "civora_bulk_send",
                [ids, this.state.channel, this.state.severity || null]
            );
            if (!res || !res.success) {
                this.state.error = (res && res.error) || "L'envoi groupé a échoué.";
                this.state.sending = false;
                return;
            }
            this.props.onDone(res);
        } catch (e) {
            console.error("[CIVORA-BULK] send", e);
            this.state.error = "Erreur lors de l'envoi groupé.";
            this.state.sending = false;
        }
    }
}
