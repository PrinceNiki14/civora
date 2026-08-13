/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CivoraDrawer } from "@civora_core/components/civora_drawer";

export class ReservationDrawer extends Component {
    static template = "civora_saisonnier.ReservationDrawer";
    static components = { CivoraDrawer };
    static props = {
        mode: { type: String },
        recordId: { type: [Number, Boolean], optional: true },
        onSaved: { type: Function },
        onClose: { type: Function },
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            form: this.emptyForm(),
            properties: [],
            contacts: [],
            saving: false,
        });
        onWillStart(() => this.loadData());
    }

    emptyForm() {
        return {
            property_id: null,
            guest_id: null,
            checkin_date: "",
            checkout_date: "",
            num_guests: 1,
            tariff_night: 0,
            deposit_amount: 0,
            source: "direct",
            notes: "",
            access_instructions: "",
        };
    }

    async loadData() {
        const [properties, contacts] = await Promise.all([
            this.orm.searchRead("civora.property", [
                ["transaction", "=", "saisonnier"],
            ], ["id", "name", "ref", "default_tariff_night"], { limit: 500 }),
            this.orm.searchRead("res.partner", [
                ["civora_is_contact", "=", true],
            ], ["id", "name"], { limit: 500 }),
        ]);
        this.state.properties = properties;
        this.state.contacts = contacts;

        if (this.props.mode === "edit" && this.props.recordId) {
            const [rec] = await this.orm.read("civora.reservation",
                [this.props.recordId],
                ["property_id", "guest_id", "checkin_date", "checkout_date",
                 "num_guests", "tariff_night", "deposit_amount", "source",
                 "notes", "access_instructions"]);
            this.state.form = {
                property_id: rec.property_id ? rec.property_id[0] : null,
                guest_id: rec.guest_id ? rec.guest_id[0] : null,
                checkin_date: rec.checkin_date || "",
                checkout_date: rec.checkout_date || "",
                num_guests: rec.num_guests || 1,
                tariff_night: rec.tariff_night || 0,
                deposit_amount: rec.deposit_amount || 0,
                source: rec.source || "direct",
                notes: rec.notes || "",
                access_instructions: rec.access_instructions || "",
            };
        }
    }

    setField(field, ev) {
        this.state.form[field] = ev.target.value;
    }

    setNumber(field, ev) {
        this.state.form[field] = parseInt(ev.target.value) || 0;
    }

    setSelect(field, ev) {
        this.state.form[field] = ev.target.value === "" ? null : parseInt(ev.target.value) || ev.target.value;
    }

    onPropertyChange(ev) {
        const pid = parseInt(ev.target.value) || null;
        this.state.form.property_id = pid;
        if (pid) {
            const prop = this.state.properties.find(p => p.id === pid);
            if (prop && prop.default_tariff_night) {
                this.state.form.tariff_night = prop.default_tariff_night;
            }
        }
    }

    validate() {
        const f = this.state.form;
        if (!f.property_id) return "Veuillez sélectionner un bien.";
        if (!f.guest_id) return "Veuillez sélectionner un voyageur.";
        if (!f.checkin_date) return "Veuillez indiquer la date d'arrivée.";
        if (!f.checkout_date) return "Veuillez indiquer la date de départ.";
        if (f.checkout_date <= f.checkin_date) return "La date de départ doit être après l'arrivée.";
        if (!f.tariff_night || f.tariff_night <= 0) return "Veuillez indiquer un tarif par nuit.";
        return null;
    }

    async save() {
        const err = this.validate();
        if (err) {
            this.notification.add(err, { type: "warning" });
            return;
        }
        this.state.saving = true;
        try {
            const vals = {
                property_id: this.state.form.property_id,
                guest_id: this.state.form.guest_id,
                checkin_date: this.state.form.checkin_date,
                checkout_date: this.state.form.checkout_date,
                num_guests: this.state.form.num_guests,
                tariff_night: this.state.form.tariff_night,
                deposit_amount: this.state.form.deposit_amount,
                source: this.state.form.source,
                notes: this.state.form.notes || false,
                access_instructions: this.state.form.access_instructions || false,
            };
            if (this.props.mode === "edit" && this.props.recordId) {
                await this.orm.write("civora.reservation", [this.props.recordId], vals);
            } else {
                await this.orm.create("civora.reservation", [vals]);
            }
            this.props.onSaved();
        } catch (e) {
            this.notification.add(e.message || "Erreur lors de l'enregistrement", { type: "danger" });
        } finally {
            this.state.saving = false;
        }
    }
}
