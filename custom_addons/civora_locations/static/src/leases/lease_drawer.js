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
        agent_id: false,
        opportunity_id: false,
        lease_type: "residentiel",
        state: "active",
        rent: 0,
        charges: 0,
        deposit: 0,
        advance_months: 0,
        caution_months: 1,
        agency_months: 1,
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
        defaultOpportunityId: { type: [Number, Boolean], optional: true },
        onClose: Function,
        onSaved: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.types = TYPES;
        this.states = STATES;
        this.properties = [];
        this.tenants = [];
        this.agents = [];

        this.state = useState({
            loading: true,
            saving: false,
            deleting: false,
            error: "",
            confirmDelete: false,
            form: emptyForm(),
            availability: { checked: false, available: true, existing: null },
        });

        onWillStart(async () => {
            await this.loadRefData();
            if (this.props.mode === "edit" && this.props.leaseId) {
                await this.loadLease(this.props.leaseId);
                if (this.state.form.property_id) {
                    await this._checkAvailability(this.state.form.property_id);
                }
            } else if (this.props.defaultOpportunityId) {
                await this.prefillFromOpportunity(this.props.defaultOpportunityId);
                if (this.state.form.property_id) {
                    await this._checkAvailability(this.state.form.property_id);
                }
            } else if (this.props.defaultPropertyId) {
                this.state.form.property_id = this.props.defaultPropertyId;
                await this.prefillFromProperty(this.props.defaultPropertyId);
                await this._checkAvailability(this.props.defaultPropertyId);
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
        this.agents = await this.orm.searchRead(
            "res.users",
            [["active", "=", true]],
            ["name"],
            { limit: 200, order: "name" }
        );
    }

    async loadLease(id) {
        const fields = [
            "name", "property_id", "tenant_id", "agent_id", "opportunity_id", "lease_type", "state",
            "rent", "charges", "deposit", "date_start", "date_end", "payday",
            "advance_months", "caution_months", "agency_months",
            "indexation", "notice_tenant", "notice_owner", "note",
        ];
        const [rec] = await this.orm.read("civora.lease", [id], fields);
        const m2o = (v) => (v ? v[0] : false);
        this.state.form = {
            name: rec.name || "",
            property_id: m2o(rec.property_id),
            tenant_id: m2o(rec.tenant_id),
            agent_id: m2o(rec.agent_id),
            opportunity_id: m2o(rec.opportunity_id),
            lease_type: rec.lease_type || "residentiel",
            state: rec.state || "active",
            rent: rec.rent || 0,
            charges: rec.charges || 0,
            deposit: rec.deposit || 0,
            advance_months: rec.advance_months || 0,
            caution_months: rec.caution_months != null ? rec.caution_months : 1,
            agency_months: rec.agency_months != null ? rec.agency_months : 1,
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

    async prefillFromOpportunity(opportunityId) {
        if (!opportunityId) return;
        try {
            const vals = await this.orm.call(
                "civora.opportunity", "action_prepare_lease_vals",
                [[opportunityId]]
            );
            if (vals) {
                this.state.form.opportunity_id = vals.opportunity_id || false;
                if (vals.property_id) this.state.form.property_id = vals.property_id;
                if (vals.tenant_id) this.state.form.tenant_id = vals.tenant_id;
                if (vals.agent_id) this.state.form.agent_id = vals.agent_id;
                if (vals.rent && !this.state.form.rent) {
                    this.state.form.rent = vals.rent;
                    // Caution par défaut = 2 mois si non déjà calculée
                    if (!this.state.form.deposit) {
                        this.state.form.deposit = vals.rent * (this.state.form.caution_months || 1);
                    }
                }
            }
        } catch (e) {
            // Silence : on tombera dans la validation serveur
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
        // Vérifier la disponibilité du bien (règle : un seul bail actif par bien)
        await this._checkAvailability(id);
    }

    async _checkAvailability(propertyId) {
        this.state.availability = { checked: false, available: true, existing: null };
        if (!propertyId) return;
        try {
            const excludeId = this.props.mode === "edit" && this.props.leaseId
                ? this.props.leaseId
                : false;
            const res = await this.orm.call(
                "civora.lease",
                "check_property_availability",
                [propertyId, excludeId]
            );
            this.state.availability = {
                checked: true,
                available: res.available,
                existing: res.existing_lease || null,
            };
        } catch (_) {
            // Silence : on tombera dans la validation serveur
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
        const bits = [];
        if (p.ref) bits.push(`[${p.ref}]`);
        bits.push(p.name);
        if (p.city) bits.push(p.city);
        return bits.join(" · ");
    }
    tenantLabel(t) {
        return t.city ? `${t.name} · ${t.city}` : t.name;
    }

    // --- Computed financiers pour le récap -----------------------------
    get advanceMonths() { return Number(this.state.form.advance_months) || 0; }
    get cautionMonths() { return Number(this.state.form.caution_months) || 0; }
    get agencyMonths()  { return Number(this.state.form.agency_months)  || 0; }
    get rentValue()     { return Number(this.state.form.rent)    || 0; }
    get chargesValue()  { return Number(this.state.form.charges) || 0; }
    get totalMonthly()  { return this.rentValue + this.chargesValue; }
    get advanceAmount() { return this.advanceMonths * this.totalMonthly; }
    get cautionAmount() { return this.cautionMonths * this.rentValue; }
    get agencyAmount()  { return this.agencyMonths  * this.rentValue; }
    get initialPaymentTotal() {
        return this.advanceAmount + this.cautionAmount + this.agencyAmount;
    }
    get firstDueMonthLabel() {
        const ds = this.state.form.date_start;
        const n = this.advanceMonths;
        if (!ds) return "";
        const d = new Date(ds + "T00:00:00");
        d.setMonth(d.getMonth() + n);
        const MOIS = ["Janvier","Février","Mars","Avril","Mai","Juin",
                      "Juillet","Août","Septembre","Octobre","Novembre","Décembre"];
        return `${MOIS[d.getMonth()]} ${d.getFullYear()}`;
    }
    fmtAmount(v) {
        const n = Number(v) || 0;
        return n.toLocaleString("fr-FR").replace(/,/g, " ") + " " + this.currencyLabel;
    }
    get currencyLabel() {
        // Devise par défaut CFA — pourra être affiné en lisant currency_id
        return "FCFA";
    }

    // --- Validation & save ---------------------------------------------
    validate() {
        const f = this.state.form;
        if (!f.property_id) return "Sélectionnez un bien.";
        if (!f.tenant_id) return "Sélectionnez un locataire.";
        // Bien déjà loué : bloquer explicitement
        if (this.state.availability.checked && !this.state.availability.available) {
            const ex = this.state.availability.existing;
            return "Ce bien est déjà loué (bail " + (ex ? ex.name : "existant")
                 + (ex && ex.tenant_name ? " au nom de " + ex.tenant_name : "")
                 + "). Résiliez le bail existant avant d'en créer un nouveau.";
        }
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
            agent_id: f.agent_id || false,
            opportunity_id: f.opportunity_id || false,
            lease_type: f.lease_type,
            state: f.state,
            rent: Number(f.rent) || 0,
            charges: Number(f.charges) || 0,
            advance_months: Number(f.advance_months) || 0,
            caution_months: Number(f.caution_months) || 0,
            agency_months: Number(f.agency_months) || 0,
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
