import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CivoraDrawer } from "@civora_core/components/civora_drawer";

const STATUSES = [
    { value: "disponible", label: "Disponible" },
    { value: "loue", label: "Loué" },
    { value: "saisonnier", label: "Saisonnier" },
];
const TRANSACTIONS = [
    { value: "", label: "—" },
    { value: "vente", label: "À vendre" },
    { value: "location", label: "À louer" },
    { value: "saisonnier", label: "Location saisonnière" },
];
const MANDATES = [
    { value: "", label: "—" },
    { value: "exclusif", label: "Exclusif" },
    { value: "simple", label: "Simple" },
    { value: "delegue", label: "Délégué" },
];

function emptyForm() {
    return {
        name: "", ref: "", property_type_id: false, status: "disponible",
        transaction: false, mandate_type: false,
        city: "", neighborhood: "", street: "", latitude: 0, longitude: 0,
        surface: 0, rooms: 0, bedrooms: 0, bathrooms: 0, year_built: 0,
        price: 0, monthly_revenue: 0,
        owner_id: false, agent_id: false, tenant_id: false, description: "", note: "",
        rental_deposit: "", rental_charges: "", rental_min_stay: "", rental_advance: "", rental_agency_fees: "",
        sale_negotiable: "", sale_notary: "", sale_payment: "", sale_handover: "",
        is_building: false, floors_count: 0, total_units: 0, parent_id: false, floor: 0, unit_number: "",
    };
}

/**
 * Modale de creation / edition d'un bien (variante "modal" du CivoraDrawer).
 * Gere une galerie multi-photos (civora.property.image) ; la 1ere = couverture.
 */
export class PropertyDrawer extends Component {
    static template = "civora_biens.PropertyDrawer";
    static components = { CivoraDrawer };
    static props = {
        mode: String,                                    // "create" | "edit"
        propertyId: { type: [Number, Boolean], optional: true },
        onClose: Function,
        onSaved: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.statuses = STATUSES;
        this.transactions = TRANSACTIONS;
        this.mandates = MANDATES;
        this.types = [];
        this.owners = [];
        this.users = [];
        this.buildings = [];
        this._tmp = 0;

        this.state = useState({
            loading: true,
            saving: false,
            error: "",
            form: emptyForm(),
            galleryExisting: [],   // [{id, name}]
            galleryNew: [],        // [{tmp, name, image, dataUrl}]
            galleryRemoved: [],    // [id]
        });

        onWillStart(async () => {
            await this.loadRefData();
            if (this.props.propertyId) {
                await this.loadProperty(this.props.propertyId);
            }
            this.state.loading = false;
        });
    }

    async loadRefData() {
        this.types = await this.orm.searchRead(
            "civora.property.type", [], ["name"], { order: "sequence, name" }
        );
        this.owners = await this.orm.searchRead(
            "res.partner", [["civora_is_contact", "=", true]], ["name"], { limit: 500, order: "name" }
        );
        this.users = await this.orm.searchRead(
            "res.users", [["share", "=", false]], ["name"], { order: "name" }
        );
        this.buildings = await this.orm.searchRead(
            "civora.property", [["is_building", "=", true]], ["name"], { order: "name" }
        );
    }

    async loadProperty(id) {
        const fields = [
            "name", "ref", "property_type_id", "transaction", "mandate_type", "status",
            "city", "neighborhood", "street", "latitude", "longitude",
            "surface", "rooms", "bedrooms", "bathrooms", "year_built",
            "price", "monthly_revenue", "owner_id", "agent_id", "tenant_id", "description", "note",
            "rental_deposit", "rental_charges", "rental_min_stay", "rental_advance", "rental_agency_fees",
            "sale_negotiable", "sale_notary", "sale_payment", "sale_handover",
            "is_building", "floors_count", "total_units", "parent_id", "floor", "unit_number",
        ];
        const [rec] = await this.orm.read("civora.property", [id], fields);
        const m2o = (v) => (v ? v[0] : false);
        this.state.form = {
            name: rec.name || "",
            ref: rec.ref || "",
            property_type_id: m2o(rec.property_type_id),
            transaction: rec.transaction || false,
            mandate_type: rec.mandate_type || false,
            status: rec.status || "disponible",
            city: rec.city || "",
            neighborhood: rec.neighborhood || "",
            street: rec.street || "",
            latitude: rec.latitude || 0,
            longitude: rec.longitude || 0,
            surface: rec.surface || 0,
            rooms: rec.rooms || 0,
            bedrooms: rec.bedrooms || 0,
            bathrooms: rec.bathrooms || 0,
            year_built: rec.year_built || 0,
            price: rec.price || 0,
            monthly_revenue: rec.monthly_revenue || 0,
            owner_id: m2o(rec.owner_id),
            agent_id: m2o(rec.agent_id),
            tenant_id: m2o(rec.tenant_id),
            description: rec.description || "",
            note: rec.note || "",
            rental_deposit: rec.rental_deposit || "",
            rental_charges: rec.rental_charges || "",
            rental_min_stay: rec.rental_min_stay || "",
            rental_advance: rec.rental_advance || "",
            rental_agency_fees: rec.rental_agency_fees || "",
            sale_negotiable: rec.sale_negotiable || "",
            sale_notary: rec.sale_notary || "",
            sale_payment: rec.sale_payment || "",
            sale_handover: rec.sale_handover || "",
            is_building: !!rec.is_building,
            floors_count: rec.floors_count || 0,
            total_units: rec.total_units || 0,
            parent_id: m2o(rec.parent_id),
            floor: rec.floor || 0,
            unit_number: rec.unit_number || "",
        };
        const imgs = await this.orm.searchRead(
            "civora.property.image", [["property_id", "=", id]], ["name"], { order: "sequence, id" }
        );
        this.state.galleryExisting = imgs.map((i) => ({ id: i.id, name: i.name || "" }));
    }

    // --- Setters -------------------------------------------------------
    setField(field, ev) {
        this.state.form[field] = ev.target.value;
    }
    setNumber(field, ev) {
        this.state.form[field] = ev.target.value === "" ? 0 : Number(ev.target.value);
    }
    setM2O(field, ev) {
        this.state.form[field] = ev.target.value ? parseInt(ev.target.value) : false;
    }
    setCheckbox(field, ev) {
        this.state.form[field] = ev.target.checked;
    }
    get transactionIsRental() {
        return this.state.form.transaction === "location" || this.state.form.transaction === "saisonnier";
    }
    get transactionIsSale() {
        return this.state.form.transaction === "vente";
    }

    // --- Galerie -------------------------------------------------------
    get galleryDisplay() {
        const removed = this.state.galleryRemoved;
        const existing = this.state.galleryExisting
            .filter((g) => !removed.includes(g.id))
            .map((g) => ({
                key: "e" + g.id,
                kind: "existing",
                id: g.id,
                src: "/web/image/civora.property.image/" + g.id + "/image_128",
            }));
        const added = this.state.galleryNew.map((g) => ({
            key: "n" + g.tmp,
            kind: "new",
            tmp: g.tmp,
            src: g.dataUrl,
        }));
        return [...existing, ...added];
    }
    onGalleryAdd(ev) {
        const files = ev.target.files ? Array.from(ev.target.files) : [];
        for (const file of files) {
            const reader = new FileReader();
            reader.onload = () => {
                const res = String(reader.result || "");
                this.state.galleryNew = [
                    ...this.state.galleryNew,
                    { tmp: ++this._tmp, name: file.name, image: res.split(",")[1] || "", dataUrl: res },
                ];
            };
            reader.readAsDataURL(file);
        }
        ev.target.value = "";   // permet de re-selectionner le meme fichier
    }
    removeImage(g) {
        if (g.kind === "existing") {
            this.state.galleryRemoved = [...this.state.galleryRemoved, g.id];
        } else {
            this.state.galleryNew = this.state.galleryNew.filter((x) => x.tmp !== g.tmp);
        }
    }

    get drawerTitle() {
        return this.props.mode === "edit" ? "Modifier le bien" : "Nouveau bien";
    }
    get drawerSubtitle() {
        return "Caractéristiques, localisation, pricing et photos";
    }

    validate() {
        const f = this.state.form;
        if (!f.name || !f.name.trim()) {
            return "Le nom du bien est requis.";
        }
        if (Number(f.price) < 0) {
            return "Le prix ne peut pas être négatif.";
        }
        if (Number(f.monthly_revenue) < 0) {
            return "Le revenu mensuel ne peut pas être négatif.";
        }
        return "";
    }

    buildVals() {
        const f = this.state.form;
        const vals = {
            name: f.name.trim(),
            ref: f.ref || false,
            property_type_id: f.property_type_id || false,
            transaction: f.transaction || false,
            mandate_type: f.mandate_type || false,
            status: f.status,
            city: f.city || false,
            neighborhood: f.neighborhood || false,
            street: f.street || false,
            latitude: Number(f.latitude) || 0,
            longitude: Number(f.longitude) || 0,
            surface: Number(f.surface) || 0,
            rooms: Number(f.rooms) || 0,
            bedrooms: Number(f.bedrooms) || 0,
            bathrooms: Number(f.bathrooms) || 0,
            year_built: Number(f.year_built) || 0,
            price: Number(f.price) || 0,
            monthly_revenue: Number(f.monthly_revenue) || 0,
            owner_id: f.owner_id || false,
            agent_id: f.agent_id || false,
            tenant_id: f.tenant_id || false,
            description: f.description || false,
            note: f.note || false,
            rental_deposit: f.rental_deposit || false,
            rental_charges: f.rental_charges || false,
            rental_min_stay: f.rental_min_stay || false,
            rental_advance: f.rental_advance || false,
            rental_agency_fees: f.rental_agency_fees || false,
            sale_negotiable: f.sale_negotiable || false,
            sale_notary: f.sale_notary || false,
            sale_payment: f.sale_payment || false,
            sale_handover: f.sale_handover || false,
            is_building: !!f.is_building,
            floors_count: Number(f.floors_count) || 0,
            total_units: Number(f.total_units) || 0,
            parent_id: f.parent_id || false,
            floor: Number(f.floor) || 0,
            unit_number: f.unit_number || false,
        };
        const cmds = [];
        this.state.galleryNew.forEach((g, idx) => {
            cmds.push([0, 0, { name: g.name || false, image: g.image, sequence: 100 + idx }]);
        });
        this.state.galleryRemoved.forEach((id) => cmds.push([2, id]));
        if (cmds.length) {
            vals.image_ids = cmds;
        }
        return vals;
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
            const vals = this.buildVals();
            if (this.props.mode === "edit") {
                await this.orm.write("civora.property", [this.props.propertyId], vals);
            } else {
                await this.orm.create("civora.property", [vals]);
            }
            this.state.saving = false;
            this.props.onSaved();
        } catch (e) {
            this.state.saving = false;
            this.state.error = "Erreur lors de l'enregistrement.";
            throw e;
        }
    }
}
