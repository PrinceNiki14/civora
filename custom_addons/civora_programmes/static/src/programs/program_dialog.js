import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CivoraDrawer } from "@civora_core/components/civora_drawer";

const PROGRAM_FIELDS = [
    "name", "program_type", "status", "developer", "city", "district", "street",
    "architect", "contractor", "description",
    "building_count", "total_lots", "sold_lots", "reserved_lots",
    "land_surface", "built_surface", "avg_price_sqm", "total_value", "signed_revenue",
    "start_date", "delivery_date", "works_progress",
    "building_permit", "notary_office", "gfa_reference", "amenity_ids",
];

const TYPE_CARDS = [
    { id: "neuf", icon: "fa-building-o", label: "Neuf", hint: "Logement neuf livré, prêt à commercialiser." },
    { id: "vefa", icon: "fa-wrench", label: "VEFA", hint: "Vente en l'état futur d'achèvement." },
    { id: "lotissement", icon: "fa-map-o", label: "Lotissement", hint: "Découpage foncier en îlots & parcelles." },
];

const STATUSES = [
    { id: "etude", label: "Étude" },
    { id: "commercialisation", label: "Commercialisation" },
    { id: "travaux", label: "Travaux" },
    { id: "livre", label: "Livré" },
];

const DEFAULT_CONTACTS = [
    { role: "Responsable programme", name: "", phone: "" },
    { role: "Chef de chantier", name: "", phone: "" },
    { role: "Responsable commercialisation", name: "", phone: "" },
];

const STEP_TITLES = [
    "Type & identité",
    "Composition & finances",
    "Calendrier & administratif",
    "Prestations & contacts",
];

/**
 * Assistant de creation / modification d'un programme, en 4 etapes.
 * Reprend a l'identique le parcours du front CIVORA.
 */
export class ProgramDialog extends Component {
    static template = "civora_programmes.ProgramDialog";
    static components = { CivoraDrawer };
    static props = {
        programId: { type: [Number, Boolean], optional: true },
        onClose: Function,
        onSaved: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.typeCards = TYPE_CARDS;
        this.statuses = STATUSES;
        this.stepTitles = STEP_TITLES;

        this.state = useState({
            step: 1,
            saving: false,
            amenities: [],
            selectedAmenities: [],
            contacts: DEFAULT_CONTACTS.map((c) => ({ ...c })),
            values: {
                name: "", program_type: "vefa", status: "etude",
                developer: "", city: "Abidjan", district: "", street: "",
                architect: "", contractor: "", description: "",
                building_count: 1, total_lots: 0, sold_lots: 0, reserved_lots: 0,
                land_surface: 0, built_surface: 0, avg_price_sqm: 0,
                total_value: 0, signed_revenue: 0,
                start_date: "", delivery_date: "", works_progress: 0,
                building_permit: "", notary_office: "", gfa_reference: "",
            },
        });

        onWillStart(async () => {
            this.state.amenities = await this.orm.searchRead(
                "civora.program.amenity", [], ["name"], { order: "sequence, name" }
            );
            if (this.props.programId) {
                await this.loadProgram(this.props.programId);
            }
        });
    }

    get isEdit() {
        return !!this.props.programId;
    }
    get title() {
        return this.isEdit ? "Modifier le programme" : "Nouveau programme";
    }
    get subtitle() {
        return `Étape ${this.state.step}/4 · ${STEP_TITLES[this.state.step - 1]}`;
    }
    get recap() {
        const v = this.state.values;
        const type = (TYPE_CARDS.find((t) => t.id === v.program_type) || {}).label || "";
        const bits = [
            v.city ? "à " + v.city : "",
            v.building_count ? v.building_count + " bâtiment(s)" : "",
            v.total_lots ? v.total_lots + " lots" : "",
            v.delivery_date ? "livraison " + String(v.delivery_date).slice(0, 7) : "",
        ].filter(Boolean);
        return { type, name: v.name || "—", bits: bits.join(" · ") };
    }

    async loadProgram(id) {
        const [rec] = await this.orm.read("civora.program", [id], PROGRAM_FIELDS);
        if (!rec) return;
        const v = this.state.values;
        for (const key of Object.keys(v)) {
            if (rec[key] !== undefined && rec[key] !== false) {
                v[key] = rec[key];
            } else if (rec[key] === false && typeof v[key] === "string") {
                v[key] = "";
            }
        }
        this.state.selectedAmenities = (rec.amenity_ids || []).slice();
        const contacts = await this.orm.searchRead(
            "civora.program.stakeholder", [["program_id", "=", id]],
            ["role", "name", "phone"], { order: "sequence, id" }
        );
        if (contacts.length) {
            this.state.contacts = contacts.map((c) => ({
                id: c.id,
                role: c.role || "",
                name: c.name || "",
                phone: c.phone || "",
            }));
        }
    }

    // --- Saisie --------------------------------------------------------
    setField(key, ev) {
        const el = ev.target;
        let val = el.value;
        if (el.type === "number") {
            val = val === "" ? 0 : Number(val);
        }
        this.state.values[key] = val;
    }
    setType(id) {
        this.state.values.program_type = id;
    }
    isAmenityOn(a) {
        return this.state.selectedAmenities.includes(a.id);
    }
    toggleAmenity(a) {
        const list = this.state.selectedAmenities;
        const idx = list.indexOf(a.id);
        if (idx >= 0) {
            list.splice(idx, 1);
        } else {
            list.push(a.id);
        }
    }
    addContact() {
        this.state.contacts.push({ role: "", name: "", phone: "" });
    }
    removeContact(index) {
        this.state.contacts.splice(index, 1);
    }
    setContact(index, key, ev) {
        this.state.contacts[index][key] = ev.target.value;
    }

    // --- Navigation ----------------------------------------------------
    get canContinue() {
        const v = this.state.values;
        if (this.state.step === 1) {
            return !!(v.name && v.developer && v.city && v.district);
        }
        return true;
    }
    next() {
        if (this.state.step === 1 && !this.canContinue) {
            this.notification.add(
                "Renseignez le nom, le promoteur, la ville et le quartier.",
                { type: "warning" }
            );
            return;
        }
        this.state.step = Math.min(4, this.state.step + 1);
    }
    prev() {
        this.state.step = Math.max(1, this.state.step - 1);
    }

    // --- Enregistrement -------------------------------------------------
    async save() {
        if (this.state.saving) return;
        const v = this.state.values;
        if (!v.name || !v.developer || !v.city || !v.district) {
            this.state.step = 1;
            this.notification.add(
                "Renseignez le nom, le promoteur, la ville et le quartier.",
                { type: "warning" }
            );
            return;
        }
        this.state.saving = true;
        try {
            const vals = { ...v };
            vals.start_date = v.start_date || false;
            vals.delivery_date = v.delivery_date || false;
            vals.amenity_ids = [[6, 0, this.state.selectedAmenities]];

            let programId = this.props.programId;
            if (programId) {
                await this.orm.write("civora.program", [programId], vals);
            } else {
                programId = await this.orm.create("civora.program", [vals]);
                programId = Array.isArray(programId) ? programId[0] : programId;
            }

            // Contacts projet : on resynchronise la liste complete.
            const existing = await this.orm.search(
                "civora.program.stakeholder", [["program_id", "=", programId]]
            );
            if (existing.length) {
                await this.orm.unlink("civora.program.stakeholder", existing);
            }
            const rows = this.state.contacts
                .filter((c) => (c.role || "").trim())
                .map((c, i) => ({
                    program_id: programId,
                    sequence: (i + 1) * 10,
                    role: c.role.trim(),
                    name: c.name || false,
                    phone: c.phone || false,
                }));
            if (rows.length) {
                await this.orm.create("civora.program.stakeholder", rows);
            }

            this.notification.add(
                this.isEdit ? "Programme mis à jour" : "Programme créé",
                { type: "success" }
            );
            this.props.onSaved(programId);
        } catch (e) {
            this.notification.add("Enregistrement impossible : " + (e.message || e), { type: "danger" });
            throw e;
        } finally {
            this.state.saving = false;
        }
    }
}
