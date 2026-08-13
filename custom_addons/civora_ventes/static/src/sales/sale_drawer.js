/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CivoraDrawer } from "@civora_core/components/civora_drawer";

export class SaleDrawer extends Component {
    static template = "civora_ventes.SaleDrawer";
    static components = { CivoraDrawer };
    static props = {
        mode: { type: String, optional: true },
        recordId: { optional: true },
        onSaved: Function,
        onClose: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            error: "",
            form: {
                property_id: null,
                seller_id: null,
                buyer_id: null,
                mandate_type: "simple",
                mandate_date: "",
                mandate_end_date: "",
                asking_price: "",
                sale_amount: "",
                amount_paid: "",
                commission_rate: "5",
                notary_name: "",
                notary_phone: "",
                notes: "",
            },
            properties: [],
            contacts: [],
            saving: false,
        });
        onWillStart(() => this.loadData());
    }

    async loadData() {
        const [properties, contacts] = await Promise.all([
            this.orm.searchRead("civora.property", [["transaction", "=", "vente"]], [
                "name", "ref", "price", "city", "neighborhood",
            ], { order: "name asc", limit: 500 }),
            this.orm.searchRead("res.partner", [["civora_is_contact", "=", true]], [
                "name", "city",
            ], { order: "name asc", limit: 500 }),
        ]);
        this.state.properties = properties;
        this.state.contacts = contacts;

        if (this.props.mode === "edit" && this.props.recordId) {
            const [rec] = await this.orm.read("civora.sale", [this.props.recordId], [
                "property_id", "seller_id", "buyer_id", "mandate_type", "mandate_date",
                "mandate_end_date", "asking_price", "sale_amount", "amount_paid",
                "commission_rate", "notary_name", "notary_phone", "notes",
            ]);
            if (rec) {
                this.state.form = {
                    property_id: rec.property_id ? rec.property_id[0] : null,
                    seller_id: rec.seller_id ? rec.seller_id[0] : null,
                    buyer_id: rec.buyer_id ? rec.buyer_id[0] : null,
                    mandate_type: rec.mandate_type || "simple",
                    mandate_date: rec.mandate_date || "",
                    mandate_end_date: rec.mandate_end_date || "",
                    asking_price: rec.asking_price || "",
                    sale_amount: rec.sale_amount || "",
                    amount_paid: rec.amount_paid || "",
                    commission_rate: rec.commission_rate || "5",
                    notary_name: rec.notary_name || "",
                    notary_phone: rec.notary_phone || "",
                    notes: rec.notes || "",
                };
            }
        }
    }

    onFieldChange(field, ev) {
        this.state.form[field] = ev.target.value;
    }

    onSelectChange(field, ev) {
        this.state.form[field] = ev.target.value ? parseInt(ev.target.value) : null;
    }

    onPropertyChange(ev) {
        const propId = ev.target.value ? parseInt(ev.target.value) : null;
        this.state.form.property_id = propId;
        if (propId) {
            const prop = this.state.properties.find(p => p.id === propId);
            if (prop && prop.price) {
                this.state.form.asking_price = prop.price;
            }
        }
    }

    /**
     * Controles cote client : le modele impose deja un bien et refuse les
     * dates de mandat incoherentes, mais laisser remonter l'erreur serveur
     * affiche un « Oops! » brut a l'utilisateur. On explique avant.
     */
    validate() {
        const f = this.state.form;
        if (!f.property_id) return "Sélectionnez le bien concerné par le mandat.";
        if (f.mandate_date && f.mandate_end_date && f.mandate_end_date <= f.mandate_date) {
            return "La fin du mandat doit être postérieure à sa date de signature.";
        }
        const rate = parseFloat(f.commission_rate);
        if (isNaN(rate) || rate < 0 || rate > 100) {
            return "Le taux de commission doit être compris entre 0 et 100 %.";
        }
        const price = parseInt(f.sale_amount, 10) || 0;
        const paid = parseInt(f.amount_paid, 10) || 0;
        if (price && paid > price) {
            return "Le montant encaissé ne peut pas dépasser le prix de vente.";
        }
        return "";
    }

    async save() {
        if (this.state.saving) return;
        const err = this.validate();
        if (err) {
            this.state.error = err;
            return;
        }
        this.state.error = "";
        this.state.saving = true;
        try {
            const f = this.state.form;
            const vals = {
                property_id: f.property_id || false,
                seller_id: f.seller_id || false,
                buyer_id: f.buyer_id || false,
                mandate_type: f.mandate_type,
                mandate_date: f.mandate_date || false,
                mandate_end_date: f.mandate_end_date || false,
                asking_price: parseInt(f.asking_price, 10) || 0,
                sale_amount: parseInt(f.sale_amount, 10) || 0,
                amount_paid: parseInt(f.amount_paid, 10) || 0,
                commission_rate: parseFloat(f.commission_rate) || 5,
                notary_name: f.notary_name || false,
                notary_phone: f.notary_phone || false,
                notes: f.notes || false,
            };
            if (this.props.mode === "edit" && this.props.recordId) {
                await this.orm.write("civora.sale", [this.props.recordId], vals);
            } else {
                await this.orm.create("civora.sale", [vals]);
            }
            this.notification.add(
                this.props.mode === "edit" ? "Dossier mis à jour." : "Dossier de vente créé.",
                { type: "success" });
            this.props.onSaved();
        } catch (e) {
            this.state.error =
                (e && e.data && e.data.message) || "Enregistrement impossible.";
            this.state.saving = false;
            return;
        }
        this.state.saving = false;
    }
}
