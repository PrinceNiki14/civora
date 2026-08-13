import { Component, onWillStart, useRef, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CivoraDrawer } from "@civora_core/components/civora_drawer";

export const LOT_TYPES = [
    { id: "studio", label: "Studio" },
    { id: "t1", label: "T1" },
    { id: "t2", label: "T2" },
    { id: "t3", label: "T3" },
    { id: "t4", label: "T4" },
    { id: "t5", label: "T5" },
    { id: "duplex", label: "Duplex" },
    { id: "villa", label: "Villa" },
    { id: "local", label: "Local" },
];

export const LOT_STATUSES = [
    { id: "disponible", label: "Disponible", variant: "info" },
    { id: "optionne", label: "Optionné", variant: "warning" },
    { id: "reserve", label: "Réservé", variant: "accent" },
    { id: "vendu", label: "Vendu", variant: "success" },
    { id: "bloque", label: "Bloqué", variant: "danger" },
];

export const LOT_ORIENTATIONS = [
    { id: "", label: "—" },
    { id: "nord", label: "Nord" },
    { id: "ne", label: "N-E" },
    { id: "est", label: "Est" },
    { id: "se", label: "S-E" },
    { id: "sud", label: "Sud" },
    { id: "so", label: "S-O" },
    { id: "ouest", label: "Ouest" },
    { id: "no", label: "N-O" },
];

const LOT_FIELDS = [
    "name", "building", "floor", "lot_type", "status", "price",
    "surface", "rooms", "bathrooms", "balcony", "terrace", "parking",
    "orientation", "exposure", "view", "features", "photo_urls", "notes",
];

/** Modale de creation / edition d'un lot de programme. */
export class LotDialog extends Component {
    static template = "civora_programmes.LotDialog";
    static components = { CivoraDrawer };
    static props = {
        programId: Number,
        lotId: { type: [Number, Boolean], optional: true },
        onClose: Function,
        onSaved: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        // Refs sur les champs de saisie des listes : t-att-value ne suffit pas
        // a re-vider un input deja modifie par l'utilisateur.
        this.featureInput = useRef("featureInput");
        this.photoInput = useRef("photoInput");
        this.types = LOT_TYPES;
        this.statuses = LOT_STATUSES;
        this.orientations = LOT_ORIENTATIONS;

        this.state = useState({
            saving: false,
            featureDraft: "",
            photoDraft: "",
            features: [],
            photos: [],
            values: {
                name: "", building: "A", floor: 0, lot_type: "t3", status: "disponible",
                price: 0, surface: 0, rooms: 0, bathrooms: 0,
                balcony: 0, terrace: 0, parking: 0,
                orientation: "", exposure: "", view: "", notes: "",
            },
        });

        onWillStart(async () => {
            if (this.props.lotId) {
                await this.loadLot(this.props.lotId);
            }
        });
    }

    get isEdit() {
        return !!this.props.lotId;
    }
    get title() {
        return this.isEdit ? "Modifier le lot" : "Nouveau lot";
    }

    async loadLot(id) {
        const [rec] = await this.orm.read("civora.program.lot", [id], LOT_FIELDS);
        if (!rec) return;
        const v = this.state.values;
        for (const key of Object.keys(v)) {
            if (rec[key] !== undefined) {
                v[key] = rec[key] === false ? (typeof v[key] === "number" ? 0 : "") : rec[key];
            }
        }
        this.state.features = (rec.features || "").split("\n").filter(Boolean);
        this.state.photos = (rec.photo_urls || "").split("\n").filter(Boolean);
    }

    setField(key, ev) {
        const el = ev.target;
        this.state.values[key] = el.type === "number"
            ? (el.value === "" ? 0 : Number(el.value))
            : el.value;
    }

    addFeature() {
        const v = (this.state.featureDraft || "").trim();
        if (!v) return;
        this.state.features.push(v);
        this.state.featureDraft = "";
        if (this.featureInput.el) {
            this.featureInput.el.value = "";
            this.featureInput.el.focus();
        }
    }
    removeFeature(i) {
        this.state.features.splice(i, 1);
    }
    onFeatureInput(ev) {
        this.state.featureDraft = ev.target.value;
    }
    onFeatureKey(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this.addFeature();
        }
    }

    addPhoto() {
        const v = (this.state.photoDraft || "").trim();
        if (!v) return;
        this.state.photos.push(v);
        this.state.photoDraft = "";
        if (this.photoInput.el) {
            this.photoInput.el.value = "";
            this.photoInput.el.focus();
        }
    }
    removePhoto(i) {
        this.state.photos.splice(i, 1);
    }
    onPhotoInput(ev) {
        this.state.photoDraft = ev.target.value;
    }

    async save() {
        if (this.state.saving) return;
        const v = this.state.values;
        if (!(v.name || "").trim()) {
            this.notification.add("Le numéro de lot est obligatoire.", { type: "warning" });
            return;
        }
        this.state.saving = true;
        try {
            const vals = {
                ...v,
                name: v.name.trim(),
                orientation: v.orientation || false,
                features: this.state.features.join("\n") || false,
                photo_urls: this.state.photos.join("\n") || false,
                program_id: this.props.programId,
            };
            if (this.props.lotId) {
                await this.orm.write("civora.program.lot", [this.props.lotId], vals);
            } else {
                await this.orm.create("civora.program.lot", [vals]);
            }
            this.notification.add(this.isEdit ? "Lot mis à jour" : "Lot ajouté", { type: "success" });
            this.props.onSaved();
        } catch (e) {
            this.notification.add("Enregistrement impossible : " + (e.message || e), { type: "danger" });
            throw e;
        } finally {
            this.state.saving = false;
        }
    }
}
