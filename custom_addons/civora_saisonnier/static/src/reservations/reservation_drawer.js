/** @odoo-module **/
import { Component, useState, onWillStart, useRef } from "@odoo/owl";
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
        // t-att-value ne repositionne que l'ATTRIBUT : des que l'utilisateur
        // a saisi une valeur, l'input est "dirty" et n'affiche plus l'attribut.
        // Le tarif etant pre-rempli depuis le bien, on force la propriete DOM.
        this.tariffRef = useRef("tariff");
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
                if (this.tariffRef.el) {
                    this.tariffRef.el.value = prop.default_tariff_night;
                }
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


/**
 * Creation / edition d'une tache de menage ou de maintenance.
 *
 * Le bouton « Nouvelle tache » de l'onglet Menage ouvrait jusqu'ici le
 * formulaire de reservation : le libelle promettait une chose et l'ecran en
 * faisait une autre. Ce composant existe pour tenir la promesse du bouton.
 */
export class CleaningTaskDialog extends Component {
    static template = "civora_saisonnier.CleaningTaskDialog";
    static components = { CivoraDrawer };
    static props = {
        taskId: { type: [Number, Boolean], optional: true },
        onSaved: Function,
        onClose: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.types = [
            { id: "menage", label: "Ménage" },
            { id: "maintenance", label: "Maintenance" },
            { id: "inspection", label: "Inspection" },
        ];
        this.slots = [
            { id: "matin", label: "Matin (8h-12h)" },
            { id: "apres_midi", label: "Après-midi (13h-17h)" },
        ];
        this.priorities = [
            { id: "basse", label: "Basse" },
            { id: "moyenne", label: "Moyenne" },
            { id: "haute", label: "Haute" },
        ];
        this.state = useState({
            saving: false,
            error: "",
            properties: [],
            staff: [],
            values: {
                property_id: "",
                staff_id: "",
                date: new Date().toISOString().slice(0, 10),
                time_slot: "matin",
                task_type: "menage",
                priority: "moyenne",
                notes: "",
            },
        });
        onWillStart(() => this.load());
    }

    async load() {
        const [properties, staff] = await Promise.all([
            this.orm.searchRead("civora.property", [["transaction", "=", "saisonnier"]],
                ["id", "name"], { limit: 200 }),
            this.orm.searchRead("civora.cleaning.staff", [], ["id", "name", "speciality"],
                { order: "sequence, name" }),
        ]);
        this.state.properties = properties;
        this.state.staff = staff;
        if (properties.length) this.state.values.property_id = `${properties[0].id}`;

        if (this.props.taskId) {
            const [rec] = await this.orm.read("civora.cleaning.task", [this.props.taskId], [
                "property_id", "staff_id", "date", "time_slot",
                "task_type", "priority", "notes",
            ]);
            if (rec) {
                this.state.values = {
                    property_id: rec.property_id ? `${rec.property_id[0]}` : "",
                    staff_id: rec.staff_id ? `${rec.staff_id[0]}` : "",
                    date: rec.date || "",
                    time_slot: rec.time_slot || "matin",
                    task_type: rec.task_type || "menage",
                    priority: rec.priority || "moyenne",
                    notes: rec.notes || "",
                };
            }
        }
    }

    get isEdit() { return !!this.props.taskId; }
    get dialogTitle() { return this.isEdit ? "Modifier la tâche" : "Nouvelle tâche"; }

    /* OWL n'expose ni Number ni String dans les templates : on compare en chaine. */
    isValue(field, v) { return `${this.state.values[field]}` === `${v}`; }

    update(field, ev) { this.state.values[field] = ev.target.value; }

    async save() {
        const v = this.state.values;
        this.state.error = "";
        if (!v.property_id) {
            this.state.error = "Sélectionnez le bien concerné.";
            return;
        }
        if (!v.date) {
            this.state.error = "Indiquez la date d'intervention.";
            return;
        }
        this.state.saving = true;
        try {
            const vals = {
                property_id: parseInt(v.property_id, 10),
                staff_id: v.staff_id ? parseInt(v.staff_id, 10) : false,
                date: v.date,
                time_slot: v.time_slot,
                task_type: v.task_type,
                priority: v.priority,
                notes: v.notes || false,
                // Une tache sans intervenant reste a planifier : c'est
                // l'assignation qui la fait passer au planning.
                state: v.staff_id ? "planifie" : "a_planifier",
            };
            if (this.isEdit) {
                await this.orm.write("civora.cleaning.task", [this.props.taskId], vals);
            } else {
                await this.orm.create("civora.cleaning.task", [vals]);
            }
            this.notification.add(
                this.isEdit ? "Tâche mise à jour." : "Tâche planifiée.", { type: "success" });
            this.props.onSaved();
        } catch (e) {
            this.state.error = (e && e.data && e.data.message) || "Enregistrement impossible.";
            this.state.saving = false;
        }
    }
}
