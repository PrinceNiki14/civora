/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";

function fmtMoney(v) {
    if (!v && v !== 0) return "0";
    return Number(v).toLocaleString("fr-FR");
}

const STATE_LABELS = {
    mandat: "Mandat signe",
    commercialisation: "En commercialisation",
    offre: "Offre recue",
    compromis: "Compromis signé",
    acte: "Acte en cours",
    cloture: "Cloturee",
    annule: "Annulée",
};

const OFFER_LABELS = {
    pending: "En attente",
    accepted: "Acceptée",
    refused: "Refusee",
    withdrawn: "Retiree",
};

class CivoraSale360 extends Component {
    static template = "civora_ventes.Sale360";
    static components = { CivoraStatCard };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.saleId = this.props.action.params?.sale_id;
        this.state = useState({
            sale: null,
            offers: [],
            activeTab: "overview",
        });
        onWillStart(() => this.load());
    }

    async load() {
        if (!this.saleId) return;
        const [sale] = await this.orm.read("civora.sale", [this.saleId], [
            "name", "property_id", "seller_id", "buyer_id", "agent_id",
            "state", "mandate_type", "mandate_date", "mandate_end_date",
            "asking_price", "sale_amount", "commission_rate", "commission_amount",
            "notary_name", "notary_phone", "compromis_date", "conditions_text",
            "acte_date", "estimated_acte_date", "notes",
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
        const m = { exclusif: "Exclusif", simple: "Simple", delegue: "Delegue" };
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
