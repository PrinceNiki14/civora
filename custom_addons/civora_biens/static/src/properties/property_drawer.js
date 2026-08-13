import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CivoraDrawer } from "@civora_core/components/civora_drawer";
import { CivoraMap } from "@civora_biens/components/civora_map";

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

// Extraction lat/lng depuis une URL Google Maps ou OSM.
// Patterns supportes :
//   https://www.google.com/maps/@LAT,LNG,ZOOMz
//   https://www.google.com/maps/place/.../@LAT,LNG,ZOOMz
//   https://maps.google.com/?q=LAT,LNG
//   https://www.google.com/maps?q=LAT,LNG
//   https://www.openstreetmap.org/?mlat=LAT&mlon=LNG
//   https://www.openstreetmap.org/#map=ZOOM/LAT/LNG
// Non supportes : liens raccourcis goo.gl / maps.app.goo.gl (redirect requis).
export function parseMapsUrl(url) {
    if (!url || typeof url !== "string") return null;
    const patterns = [
        /@(-?\d{1,3}\.\d+),(-?\d{1,3}\.\d+)/,             // @LAT,LNG
        /[?&]q=(-?\d{1,3}\.\d+),(-?\d{1,3}\.\d+)/,        // ?q=LAT,LNG
        /[?&]mlat=(-?\d{1,3}\.\d+)&mlon=(-?\d{1,3}\.\d+)/,// OSM ?mlat&mlon
        /#map=\d+(?:\.\d+)?\/(-?\d{1,3}\.\d+)\/(-?\d{1,3}\.\d+)/, // OSM #map
    ];
    for (const rx of patterns) {
        const m = url.match(rx);
        if (m) {
            const lat = parseFloat(m[1]);
            const lng = parseFloat(m[2]);
            if (Number.isFinite(lat) && Number.isFinite(lng)
                && Math.abs(lat) <= 90 && Math.abs(lng) <= 180) {
                return { lat, lng };
            }
        }
    }
    return null;
}

function emptyForm() {
    return {
        name: "", ref: "", property_type_id: false, status: "disponible",
        transaction: false, mandate_type: false,
        city: "", neighborhood: "", street: "",
        latitude: 0, longitude: 0, maps_url: "",
        surface: 0, rooms: 0, bedrooms: 0, bathrooms: 0, year_built: 0,
        price: 0, monthly_revenue: 0,
        owner_id: false, agent_id: false, tenant_id: false, description: "", note: "",
        rental_deposit: "", rental_charges: "", rental_min_stay: "", rental_advance: "", rental_agency_fees: "",
        sale_negotiable: "", sale_notary: "", sale_payment: "", sale_handover: "",
        sale_doc_ids: [],
        is_building: false, floors_count: 0, total_units: 0, parent_id: false, floor: 0, unit_number: "",
    };
}

/**
 * Modale de creation / edition d'un bien (variante "modal" du CivoraDrawer).
 * Gere une galerie multi-photos (civora.property.image) ; la 1ere = couverture.
 */
export class PropertyDrawer extends Component {
    static template = "civora_biens.PropertyDrawer";
    static components = { CivoraDrawer, CivoraMap };
    static props = {
        mode: String,                                    // "create" | "edit"
        propertyId: { type: [Number, Boolean], optional: true },
        onClose: Function,
        onSaved: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.statuses = STATUSES;
        this.transactions = TRANSACTIONS;
        this.mandates = MANDATES;
        this.types = [];
        this.saleDocTypes = [];
        this.owners = [];
        this.users = [];
        this.buildings = [];
        this._tmp = 0;
        this._deleteTimer = null;
        this._mapsUrlDebounce = null;

        this.state = useState({
            loading: true,
            saving: false,
            error: "",
            form: emptyForm(),
            galleryExisting: [],   // [{id, name}]
            galleryNew: [],        // [{tmp, name, image, dataUrl}]
            galleryRemoved: [],    // [id]
            // Suppression 2-clic + archivage
            confirmingDelete: false,
            deleting: false,
            deleteBlock: null,     // { reason, blocking } quand suppression refusee
            // Geolocalisation navigateur
            locating: false,
            // Feedback parsing d'URL Maps
            mapsUrlHint: "",
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
        this.saleDocTypes = await this.orm.call(
            "civora.sale.doc.type", "civora_doc_types", []
        );
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
            "city", "neighborhood", "street", "latitude", "longitude", "maps_url",
            "surface", "rooms", "bedrooms", "bathrooms", "year_built",
            "price", "monthly_revenue", "owner_id", "agent_id", "tenant_id", "description", "note",
            "rental_deposit", "rental_charges", "rental_min_stay", "rental_advance", "rental_agency_fees",
            "sale_negotiable", "sale_notary", "sale_payment", "sale_handover",
            "is_building", "floors_count", "total_units", "parent_id", "floor", "unit_number",
            "sale_doc_ids",
        ];
        const [rec] = await this.orm.read("civora.property", [id], fields);
        const m2o = (v) => (v ? v[0] : false);
        this.state.form = {
            name: rec.name || "",
            ref: rec.ref || "",
            sale_doc_ids: rec.sale_doc_ids || [],
            property_type_id: m2o(rec.property_type_id),
            transaction: rec.transaction || false,
            mandate_type: rec.mandate_type || false,
            status: rec.status || "disponible",
            city: rec.city || "",
            neighborhood: rec.neighborhood || "",
            street: rec.street || "",
            latitude: rec.latitude || 0,
            longitude: rec.longitude || 0,
            maps_url: rec.maps_url || "",
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
    // ── Documents juridiques de vente ───────────────────────────────
    toggleSaleDoc(docId) {
        const cur = this.state.form.sale_doc_ids || [];
        this.state.form.sale_doc_ids = cur.includes(docId)
            ? cur.filter((i) => i !== docId)
            : [...cur, docId];
    }

    hasSaleDoc(docId) {
        return (this.state.form.sale_doc_ids || []).includes(docId);
    }

    get saleDocCount() {
        return (this.state.form.sale_doc_ids || []).length;
    }

    /**
     * Un dossier est jugé suffisant s'il comporte au moins deux pièces
     * DONT une pièce maîtresse (ACD, Titre Foncier, Certificat de
     * propriété). Deux pièces secondaires ne prouvent rien sur la
     * propriété du bien.
     */
    get saleDocsOk() {
        const ids = this.state.form.sale_doc_ids || [];
        if (ids.length < 2) return false;
        return this.saleDocTypes.some((d) => d.is_essential && ids.includes(d.id));
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
        // Le nom n'est plus saisi : il est composé automatiquement. On
        // contrôle en revanche le type, qui détermine à la fois le titre et
        // le préfixe de la référence.
        if (!f.property_type_id) {
            return "Le type du bien est requis : il compose le nom et la référence.";
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
            // 'name' n'est plus transmis : c'est un champ calculé côté serveur
            // (type + pièces + quartier). L'envoyer déclencherait une erreur
            // d'écriture sur un champ en lecture seule.
            ref: f.ref || false,
            sale_doc_ids: [[6, 0, f.sale_doc_ids || []]],
            property_type_id: f.property_type_id || false,
            transaction: f.transaction || false,
            mandate_type: f.mandate_type || false,
            status: f.status,
            city: f.city || false,
            neighborhood: f.neighborhood || false,
            street: f.street || false,
            latitude: Number(f.latitude) || 0,
            longitude: Number(f.longitude) || 0,
            maps_url: f.maps_url || false,
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

    /**
     * Aperçu du titre, recomposé côté client pendant la saisie.
     *
     * Le titre définitif est calculé par le serveur (_compute_name) : ce
     * getter reproduit la même règle pour que l'agent voie le résultat
     * immédiatement, sans attendre l'enregistrement.
     */
    get autoName() {
        const f = this.state.form;
        const parts = [];
        const t = this.types.find((x) => x.id === f.property_type_id);
        if (t) parts.push(t.name);
        const rooms = parseInt(f.rooms, 10);
        if (rooms) parts.push(rooms + (rooms > 1 ? " pièces" : " pièce"));
        const unit = (f.unit_number || "").trim();
        if (f.parent_id && unit) {
            parts.push("Apt " + unit);
        } else {
            const place = (f.neighborhood || "").trim() || (f.city || "").trim();
            if (place) parts.push(place);
        }
        return parts.filter(Boolean).join(" ");
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

    // ------------------------------------------------------------------
    // Position sur carte : lien Maps, clic carte, geoloc navigateur, effacer
    // ------------------------------------------------------------------
    onMapPositionChange(lat, lng) {
        // Callback du composant CivoraMap : clic ou drag du marqueur.
        this.state.form.latitude = Number(lat.toFixed(7));
        this.state.form.longitude = Number(lng.toFixed(7));
    }

    onMapsUrlInput(ev) {
        const url = ev.target.value || "";
        this.state.form.maps_url = url;
        // Debounce court pour eviter de parser a chaque frappe.
        if (this._mapsUrlDebounce) clearTimeout(this._mapsUrlDebounce);
        this._mapsUrlDebounce = setTimeout(() => this.tryParseMapsUrl(url), 300);
    }

    tryParseMapsUrl(url) {
        if (!url || !url.trim()) {
            this.state.mapsUrlHint = "";
            return;
        }
        const trimmed = url.trim();
        // Detection des liens raccourcis qu'on ne peut pas resoudre cote client.
        if (/^https?:\/\/(goo\.gl|maps\.app\.goo\.gl)/i.test(trimmed)) {
            this.state.mapsUrlHint = "Lien raccourci non pris en charge. Ouvrez le lien puis copiez l'URL complete, ou cliquez sur la carte.";
            return;
        }
        const pos = parseMapsUrl(trimmed);
        if (pos) {
            this.state.form.latitude = Number(pos.lat.toFixed(7));
            this.state.form.longitude = Number(pos.lng.toFixed(7));
            this.state.mapsUrlHint = `Position détectée : ${pos.lat.toFixed(5)}, ${pos.lng.toFixed(5)}`;
        } else {
            this.state.mapsUrlHint = "Position introuvable dans ce lien.";
        }
    }

    async useMyLocation() {
        if (this.state.locating) return;
        if (!navigator.geolocation) {
            this.notification.add("Géolocalisation indisponible sur ce navigateur.", { type: "warning" });
            return;
        }
        this.state.locating = true;
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                this.state.form.latitude = Number(pos.coords.latitude.toFixed(7));
                this.state.form.longitude = Number(pos.coords.longitude.toFixed(7));
                this.state.form.maps_url = "";
                this.state.mapsUrlHint = "";
                this.state.locating = false;
                this.notification.add("Position actuelle capturée.", { type: "success" });
            },
            (err) => {
                this.state.locating = false;
                const msg = err.code === 1
                    ? "Autorisation refusee dans le navigateur."
                    : "Impossible de recuperer la position.";
                this.notification.add(msg, { type: "warning" });
            },
            { enableHighAccuracy: true, timeout: 10000 },
        );
    }

    clearPosition() {
        this.state.form.latitude = 0;
        this.state.form.longitude = 0;
        this.state.form.maps_url = "";
        this.state.mapsUrlHint = "";
    }

    get hasPosition() {
        const la = Number(this.state.form.latitude);
        const lo = Number(this.state.form.longitude);
        return Number.isFinite(la) && Number.isFinite(lo) && (la !== 0 || lo !== 0);
    }

    get googleMapsLink() {
        if (!this.hasPosition) return "";
        return `https://www.google.com/maps/?q=${this.state.form.latitude},${this.state.form.longitude}`;
    }

    // ------------------------------------------------------------------
    // Suppression 2-clic (avec blocage baux/opps/unites et proposition archivage)
    // ------------------------------------------------------------------
    async onDeleteClick() {
        if (!this.props.propertyId || this.props.mode !== "edit") return;
        if (this.state.deleteBlock) {
            // Deuxieme clic sur "Archiver a la place" dans le bandeau blocage.
            return;
        }
        if (!this.state.confirmingDelete) {
            // Verifie prealablement les bloquants pour donner un feedback net.
            let report;
            try {
                report = await this.orm.call(
                    "civora.property", "action_delete_check",
                    [[this.props.propertyId]],
                );
            } catch (e) {
                this.notification.add("Verification impossible.", { type: "danger" });
                return;
            }
            if (!report.deletable) {
                this.state.deleteBlock = { reason: report.reason, blocking: report.blocking };
                return;
            }
            this.state.confirmingDelete = true;
            if (this._deleteTimer) clearTimeout(this._deleteTimer);
            this._deleteTimer = setTimeout(() => {
                this.state.confirmingDelete = false;
            }, 4000);
            return;
        }
        // 2e clic : suppression effective.
        this.state.deleting = true;
        if (this._deleteTimer) clearTimeout(this._deleteTimer);
        try {
            await this.orm.unlink("civora.property", [this.props.propertyId]);
            this.notification.add("Bien supprime.", { type: "success" });
            this.props.onSaved();
        } catch (e) {
            this.state.deleting = false;
            this.state.confirmingDelete = false;
            this.notification.add("Suppression impossible.", { type: "danger" });
        }
    }

    async archiveInstead() {
        if (!this.props.propertyId) return;
        try {
            await this.orm.call(
                "civora.property", "action_archive_property",
                [[this.props.propertyId]],
            );
            this.notification.add("Bien archive. Il reste consultable via l'option « Voir les archives ».", { type: "success" });
            this.state.deleteBlock = null;
            this.props.onSaved();
        } catch (e) {
            this.notification.add("Archivage impossible.", { type: "danger" });
        }
    }

    cancelDeleteBlock() { this.state.deleteBlock = null; }
}
