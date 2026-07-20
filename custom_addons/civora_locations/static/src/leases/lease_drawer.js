import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CivoraDrawer } from "@civora_core/components/civora_drawer";

const TYPES = [
    { value: "residentiel", label: "Résidentiel" },
    { value: "commercial", label: "Commercial" },
];
const STATES = [
    { value: "draft", label: "Brouillon" },
    { value: "active", label: "Actif" },
    { value: "ended", label: "Résilié" },
];

function emptyForm() {
    const today = new Date().toISOString().slice(0, 10);
    return {
        name: "",              // auto-genere serveur si vide
        property_id: false,
        tenant_id: false,
        lease_type: "residentiel",
        state: "active",
        rent: 0,
        charges: 0,
        deposit: 0,
        date_start: today,
        date_end: "",
        payday: 1,
        indexation: "Annuelle · IRL",
        notice_tenant: "3 mois",
        notice_owner: "6 mois",
        note: "",
    };
}

/**
 * Modale de creation / edition d'un bail (variante "modal" du CivoraDrawer).
 * - Numero de bail auto-genere via ir.sequence si vide (format BL-YYYY-000).
 * - Prefill loyer/charges/depot depuis civora.property.monthly_revenue au choix du bien.
 * - Validation cliente : bien + locataire + loyer requis, dates coherentes.
 * - Prefill via props.defaultPropertyId / defaultTenantId pour la creation depuis
 *   la fiche Bien 360 ou la fiche Locataire 360 (increment suivant).
 */
export class LeaseDrawer extends Component {
    static template = "civora_locations.LeaseDrawer";
    static components = { CivoraDrawer };
    static props = {
        mode: String,                                     // "create" | "edit"
        leaseId: { type: [Number, Boolean], optional: true },
        defaultPropertyId: { type: [Number, Boolean], optional: true },
        defaultTenantId: { type: [Number, Boolean], optional: true },
        onClose: Function,
        onSaved: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.types = TYPES;
        this.states = STATES;
        this.properties = [];
        this.tenants = [];

        this.state = useState({
            loading: true,
            saving: false,
            deleting: false,
            error: "",
            confirmDelete: false,
            form: emptyForm(),
        });

        onWillStart(async () => {
            await this.loadRefData();
            if (this.props.mode === "edit" && this.props.leaseId) {
                await this.loadLease(this.props.leaseId);
            } else if (this.props.defaultPropertyId) {
                this.state.form.property_id = this.props.defaultPropertyId;
                await this.prefillFromProperty(this.props.defaultPropertyId);
            }
            if (this.props.defaultTenantId && this.props.mode === "create") {
                this.state.form.tenant_id = this.props.defaultTenantId;
            }
            this.state.loading = false;
        });
    }

    async loadRefData() {
        // Biens : on privilegie ceux destines a la location ou deja loues.
        // On garde une liste large (l'utilisateur peut avoir un cas particulier).
        this.properties = await this.orm.searchRead(
            "civora.property",
            [["is_building", "=", false]],
            ["name", "ref", "transaction", "status", "monthly_revenue", "city"],
            { limit: 1000, order: "name" }
        );
        this.tenants = await this.orm.searchRead(
            "res.partner",
            [["civora_is_contact", "=", true]],
            ["name", "city"],
            { limit: 1000, order: "name" }
        );
    }

    async loadLease(id) {
        const fields = [
            "name", "property_id", "tenant_id", "lease_type", "state",
            "rent", "charges", "deposit", "date_start", "date_end", "payday",
            "indexation", "notice_tenant", "notice_owner", "note",
        ];
        const [rec] = await this.orm.read("civora.lease", [id], fields);
        const m2o = (v) => (v ? v[0] : false);
        this.state.form = {
            name: rec.name || "",
            property_id: m2o(rec.property_id),
            tenant_id: m2o(rec.tenant_id),
            lease_type: rec.lease_type || "residentiel",
            state: rec.state || "active",
            rent: rec.rent || 0,
            charges: rec.charges || 0,
            deposit: rec.deposit || 0,
            date_start: rec.date_start || "",
            date_end: rec.date_end || "",
            payday: rec.payday || 1,
            indexation: rec.indexation || "",
            notice_tenant: rec.notice_tenant || "",
            notice_owner: rec.notice_owner || "",
            note: rec.note || "",
        };
    }

    async prefillFromProperty(propertyId) {
        if (!propertyId) return;
        const prop = this.properties.find((p) => p.id === propertyId);
        if (prop && prop.monthly_revenue && !this.state.form.rent) {
            // On propose le revenu mensuel comme loyer par defaut,
            // avec une caution egale a 2 mois (usage courant en Cote d'Ivoire).
            this.state.form.rent = prop.monthly_revenue;
            this.state.form.deposit = prop.monthly_revenue * 2;
        }
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
    async onPropertyChange(ev) {
        const id = ev.target.value ? parseInt(ev.target.value) : false;
        this.state.form.property_id = id;
        if (this.props.mode === "create" && id) {
            await this.prefillFromProperty(id);
        }
    }

    // --- UI helpers ----------------------------------------------------
    get drawerTitle() {
        return this.props.mode === "edit" ? "Modifier le bail" : "Nouveau bail";
    }
    get drawerSubtitle() {
        return "Conditions du contrat, période et suivi financier";
    }
    propertyLabel(p) {
        const bits = [p.name];
        if (p.city) bits.push(p.city);
        return bits.join(" · ");
    }
    tenantLabel(t) {
        return t.city ? `${t.name} · ${t.city}` : t.name;
    }

    // --- Validation & save ---------------------------------------------
    validate() {
        const f = this.state.form;
        if (!f.property_id) return "Sélectionnez un bien.";
        if (!f.tenant_id) return "Sélectionnez un locataire.";
        if (!f.date_start) return "La date d'entrée est requise.";
        if (Number(f.rent) <= 0) return "Le loyer doit être supérieur à zéro.";
        if (Number(f.rent) < 0 || Number(f.charges) < 0 || Number(f.deposit) < 0) {
            return "Les montants ne peuvent pas être négatifs.";
        }
        if (f.date_end && f.date_end < f.date_start) {
            return "La date de fin doit être postérieure à la date d'entrée.";
        }
        const p = Number(f.payday);
        if (p < 1 || p > 28) {
            return "Le jour de paiement doit être compris entre 1 et 28.";
        }
        return "";
    }

    buildVals() {
        const f = this.state.form;
        const vals = {
            property_id: f.property_id,
            tenant_id: f.tenant_id,
            lease_type: f.lease_type,
            state: f.state,
            rent: Number(f.rent) || 0,
            charges: Number(f.charges) || 0,
            deposit: Number(f.deposit) || 0,
            date_start: f.date_start,
            date_end: f.date_end || false,
            payday: Number(f.payday) || 1,
            indexation: f.indexation || false,
            notice_tenant: f.notice_tenant || false,
            notice_owner: f.notice_owner || false,
            note: f.note || false,
        };
        // Si l'utilisateur a saisi un numero manuellement, on le respecte ;
        // sinon on laisse la sequence serveur decider (BL-YYYY-000).
        if (f.name && f.name.trim()) {
            vals.name = f.name.trim();
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
            let id = this.props.leaseId;
            if (this.props.mode === "edit") {
                await this.orm.write("civora.lease", [this.props.leaseId], vals);
            } else {
                const created = await this.orm.create("civora.lease", [vals]);
                id = Array.isArray(created) ? created[0] : created;
            }
            this.state.saving = false;
            this.props.onSaved(id);
        } catch (e) {
            this.state.saving = false;
            this.state.error = "Erreur lors de l'enregistrement.";
            throw e;
        }
    }

    // --- Suppression (edit uniquement) ---------------------------------
    askDelete() {
        this.state.confirmDelete = true;
    }
    cancelDelete() {
        this.state.confirmDelete = false;
    }
    async confirmDeleteNow() {
        if (this.props.mode !== "edit" || !this.props.leaseId) return;
        this.state.deleting = true;
        try {
            await this.orm.unlink("civora.lease", [this.props.leaseId]);
            this.state.deleting = false;
            this.props.onSaved(false);
        } catch (e) {
            this.state.deleting = false;
            this.state.error = "Impossible de supprimer ce bail.";
            throw e;
        }
    }
}
