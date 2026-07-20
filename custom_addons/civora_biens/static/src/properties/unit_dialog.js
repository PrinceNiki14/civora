import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CivoraDrawer } from "@civora_core/components/civora_drawer";

const TRANSACTIONS = [
    { value: "location", label: "Location" },
    { value: "vente", label: "Vente" },
    { value: "saisonnier", label: "Saisonnier" },
];

/**
 * Modale "Ajouter une unite" a un immeuble.
 * L'unite herite automatiquement (cote serveur, create_unit) de la
 * localisation et du proprietaire/agent de l'immeuble parent.
 */
export class UnitDialog extends Component {
    static template = "civora_biens.UnitDialog";
    static components = { CivoraDrawer };
    static props = {
        building: { type: Object },
        onClose: Function,
        onSaved: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.transactions = TRANSACTIONS;
        this.state = useState({
            saving: false,
            error: "",
            form: {
                unit_number: "",
                floor: 0,
                bedrooms: 2,
                bathrooms: 1,
                surface: 60,
                price: 0,
                monthly_revenue: 0,
                transaction: "location",
                description: "",
            },
        });
    }

    setField(field, ev) {
        this.state.form[field] = ev.target.value;
    }
    setNumber(field, ev) {
        this.state.form[field] = ev.target.value === "" ? 0 : Number(ev.target.value);
    }

    validate() {
        const f = this.state.form;
        if (!f.unit_number || !f.unit_number.trim()) return "Le numéro d'unité est requis.";
        if (Number(f.surface) < 0 || Number(f.price) < 0 || Number(f.monthly_revenue) < 0) {
            return "Les montants ne peuvent pas être négatifs.";
        }
        return "";
    }

    async save() {
        const err = this.validate();
        if (err) {
            this.state.error = err;
            return;
        }
        this.state.error = "";
        this.state.saving = true;
        try {
            const f = this.state.form;
            await this.orm.call("civora.property", "create_unit", [
                this.props.building.id,
                {
                    unit_number: f.unit_number.trim(),
                    floor: Number(f.floor) || 0,
                    bedrooms: Number(f.bedrooms) || 0,
                    bathrooms: Number(f.bathrooms) || 0,
                    surface: Number(f.surface) || 0,
                    price: Number(f.price) || 0,
                    monthly_revenue: Number(f.monthly_revenue) || 0,
                    transaction: f.transaction || false,
                    description: f.description || false,
                },
            ]);
            this.state.saving = false;
            this.props.onSaved();
        } catch (e) {
            this.state.saving = false;
            this.state.error = "Erreur lors de la création de l'unité.";
            throw e;
        }
    }
}
