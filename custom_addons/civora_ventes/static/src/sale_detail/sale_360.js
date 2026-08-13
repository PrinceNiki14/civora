/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";
import { SaleDrawer } from "@civora_ventes/sales/sale_drawer";

function fmtMoney(v) {
    if (!v && v !== 0) return "0";
    return Number(v).toLocaleString("fr-FR");
}

const STATE_LABELS = {
    mandat: "Mandat signé",
    commercialisation: "En commercialisation",
    offre: "Offre reçue",
    compromis: "Compromis signé",
    acte: "Acte en cours",
    cloture: "Clôturée",
    annule: "Annulée",
};

const OFFER_LABELS = {
    pending: "En attente",
    accepted: "Acceptée",
    refused: "Refusée",
    withdrawn: "Retirée",
};

class CivoraSale360 extends Component {
    static template = "civora_ventes.Sale360";
    static components = { CivoraStatCard, SaleDrawer };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.saleId = this.props.action.params?.sale_id;
        this.state = useState({
            sale: null,
            offers: [],
            activeTab: "overview",
            editing: false,
        });
        onWillStart(() => this.load());
    }

    async load() {
        // Sans identifiant (URL de l'action ouverte directement, favori peri-
        // me...), l'ecran restait bloque sur « Chargement... » indefiniment.
        // On renvoie a la liste : c'est la seule issue utile.
        if (!this.saleId) {
            this.goBack();
            return;
        }
        const [sale] = await this.orm.read("civora.sale", [this.saleId], [
            "name", "property_id", "seller_id", "buyer_id", "agent_id",
            "state", "mandate_type", "mandate_date", "mandate_end_date",
            "asking_price", "sale_amount", "commission_rate", "commission_amount",
            "notary_name", "notary_phone", "compromis_date", "conditions_text",
            "acte_date", "estimated_acte_date", "notes",
            "amount_paid", "payment_progress",
        ]);
        const offers = await this.orm.searchRead("civora.sale.offer", [
            ["sale_id", "=", this.saleId],
        ], [
            "buyer_id", "amount", "date", "validity_date", "state", "notes",
        ], { order: "date desc" });
        this.state.sale = sale;
        this.state.offers = offers;
    }

    goBack() {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.ventes",
        });
    }

    setTab(t) { this.state.activeTab = t; }

    // Le drawer sait deja editer un dossier (mode "edit"), mais aucun ecran
    // ne l'ouvrait dans ce mode : la fiche etait consultable et pas modifiable.
    openEdit() { this.state.editing = true; }
    closeEdit() { this.state.editing = false; }
    async onEdited() {
        this.state.editing = false;
        await this.load();
    }

    // Reste a encaisser : l'information que reclame un gestionnaire devant
    // une vente en cours, et qui n'apparaissait nulle part sur la fiche.
    get remaining() {
        const rec = this.state.sale;
        if (!rec || !rec.sale_amount) return 0;
        return Math.max(0, rec.sale_amount - (rec.amount_paid || 0));
    }

    stateLabel(s) { return STATE_LABELS[s] || s; }
    stateClass(s) {
        const m = {
            mandat: "muted",
            commercialisation: "info",
            offre: "warning",
            compromis: "violet",
            acte: "primary",
            cloture: "success",
            annule: "danger",
        };
        return m[s] || "";
    }
    offerStateLabel(s) { return OFFER_LABELS[s] || s; }
    offerStateClass(s) {
        const m = { pending: "warning", accepted: "success", refused: "danger", withdrawn: "muted" };
        return m[s] || "";
    }
    mandateLabel(s) {
        const m = { exclusif: "Exclusif", simple: "Simple", delegue: "Délégué" };
        return m[s] || s;
    }
    fmtMoney(v) { return fmtMoney(v); }

    async doAction(method) {
        await this.orm.call("civora.sale", method, [[this.saleId]]);
        await this.load();
    }

    async acceptOffer(offerId) {
        await this.orm.call("civora.sale.offer", "action_accept", [[offerId]]);
        await this.load();
    }
    async refuseOffer(offerId) {
        await this.orm.call("civora.sale.offer", "action_refuse", [[offerId]]);
        await this.load();
    }
}

registry.category("actions").add("civora.sale_360", CivoraSale360);
