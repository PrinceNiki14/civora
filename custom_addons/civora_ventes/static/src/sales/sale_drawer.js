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
        this.state = useState({
            form: {
                property_id: null,
                seller_id: null,
                mandate_type: "simple",
                mandate_date: "",
                mandate_end_date: "",
                asking_price: "",
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
                "property_id", "seller_id", "mandate_type", "mandate_date",
                "mandate_end_date", "asking_price", "commission_rate",
                "notary_name", "notary_phone", "notes",
            ]);
            if (rec) {
                this.state.form = {
                    property_id: rec.property_id ? rec.property_id[0] : null,
                    seller_id: rec.seller_id ? rec.seller_id[0] : null,
                    mandate_type: rec.mandate_type || "simple",
                    mandate_date: rec.mandate_date || "",
                    mandate_end_date: rec.mandate_end_date || "",
                    asking_price: rec.asking_price || "",
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

    async save() {
        if (this.state.saving) return;
        this.state.saving = true;
        try {
            const f = this.state.form;
            const vals = {
                property_id: f.property_id || false,
                seller_id: f.seller_id || false,
                mandate_type: f.mandate_type,
                mandate_date: f.mandate_date || false,
                mandate_end_date: f.mandate_end_date || false,
                asking_price: parseInt(f.asking_price) || 0,
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
            this.props.onSaved();
        } finally {
            this.state.saving = false;
        }
    }
}
