import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CivoraDrawer } from "@civora_core/components/civora_drawer";

/**
 * Modale "Duplication en masse" : genere N unites a partir d'une unite modele
 * existante (meme surface / chambres / prix), en numerotant automatiquement.
 */
export class DuplicateUnitsDialog extends Component {
    static template = "civora_biens.DuplicateUnitsDialog";
    static components = { CivoraDrawer };
    static props = {
        building: { type: Object },
        units: { type: Array },
        onClose: Function,
        onSaved: Function,
    };

    setup() {
        this.orm = useService("orm");
        const first = this.props.units[0];
        this.state = useState({
            saving: false,
            error: "",
            templateId: first ? first.id : false,
            count: 5,
            startNumber: 101,
            increment: 1,
            perFloor: false,
        });
    }

    setTemplate(ev) {
        this.state.templateId = ev.target.value ? parseInt(ev.target.value) : false;
    }
    setNumber(field, ev) {
        this.state[field] = ev.target.value === "" ? 0 : Number(ev.target.value);
    }
    setPerFloor(ev) {
        this.state.perFloor = ev.target.checked;
    }

    unitOption(u) {
        const bits = [];
        if (u.unit_number) bits.push("Apt " + u.unit_number);
        if (u.bedrooms) bits.push(u.bedrooms + " ch");
        if (u.surface) bits.push(Math.round(u.surface) + " m²");
        return bits.join(" · ") || u.name;
    }

    get preview() {
        const n = Number(this.state.count) || 0;
        if (n <= 0) return [];
        const out = [];
        const start = Number(this.state.startNumber) || 101;
        const inc = Number(this.state.increment) || 1;
        for (let i = 0; i < Math.min(n, 6); i++) {
            out.push(start + i * inc);
        }
        return out;
    }

    async save() {
        if (!this.state.templateId) {
            this.state.error = "Créez d'abord une unité modèle via « Ajouter une unité ».";
            return;
        }
        const count = Number(this.state.count) || 0;
        if (count <= 0 || count > 100) {
            this.state.error = "Le nombre d'unités doit être compris entre 1 et 100.";
            return;
        }
        this.state.error = "";
        this.state.saving = true;
        try {
            await this.orm.call("civora.property", "duplicate_units", [
                this.props.building.id,
                this.state.templateId,
                {
                    count,
                    start_number: Number(this.state.startNumber) || 101,
                    increment: Number(this.state.increment) || 1,
                    per_floor: this.state.perFloor ? 1 : 0,
                },
            ]);
            this.state.saving = false;
            this.props.onSaved();
        } catch (e) {
            this.state.saving = false;
            this.state.error = "Erreur lors de la duplication.";
            throw e;
        }
    }
}
