import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CivoraDrawer } from "@civora_core/components/civora_drawer";

const STATUSES = [
    { value: "nouveau", label: "Nouveau" },
    { value: "a_qualifier", label: "À qualifier" },
    { value: "qualifie", label: "Qualifié" },
    { value: "rejete", label: "Rejeté" },
];
const TRANSACTIONS = [
    { value: "", label: "—" },
    { value: "vente", label: "Vente" },
    { value: "location", label: "Location" },
    { value: "saisonnier", label: "Saisonnier" },
];

export class LeadDrawer extends Component {
    static template = "civora_pipeline.LeadDrawer";
    static components = { CivoraDrawer };
    static props = {
        leadId: { type: [Number, Boolean], optional: true },
        onClose: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.statuses = STATUSES;
        this.transactions = TRANSACTIONS;
        this.partners = [];
        this.sources = [];
        this.properties = [];
        this.users = [];
        this.state = useState({
            loading: true,
            saving: false,
            error: "",
            form: this.emptyForm(),
        });
        onWillStart(() => this.load());
    }

    emptyForm() {
        return {
            name: "", partner_id: false, contact_name: "", email: "", phone: "",
            source_id: false, status: "nouveau", score: 0, transaction: false,
            budget_min: 0, budget_max: 0, property_id: false, agent_id: false, description: "",
        };
    }

    async load() {
        this.state.loading = true;
        this.partners = await this.orm.searchRead(
            "res.partner", [["civora_is_contact", "=", true]], ["name"], { limit: 500, order: "name" }
        );
        this.sources = await this.orm.searchRead("civora.contact.source", [], ["name"], { order: "name" });
        this.properties = await this.orm.searchRead("civora.property", [], ["name"], { limit: 500, order: "name" });
        this.users = await this.orm.searchRead("res.users", [["share", "=", false]], ["name"], { order: "name" });

        if (this.props.leadId) {
            const m2o = (v) => (v ? v[0] : false);
            const [rec] = await this.orm.read("civora.lead", [this.props.leadId], [
                "name", "partner_id", "contact_name", "email", "phone", "source_id",
                "status", "score", "transaction", "budget_min", "budget_max",
                "property_id", "agent_id", "description",
            ]);
            if (rec) {
                this.state.form = {
                    name: rec.name || "",
                    partner_id: m2o(rec.partner_id),
                    contact_name: rec.contact_name || "",
                    email: rec.email || "",
                    phone: rec.phone || "",
                    source_id: m2o(rec.source_id),
                    status: rec.status || "nouveau",
                    score: rec.score || 0,
                    transaction: rec.transaction || false,
                    budget_min: rec.budget_min || 0,
                    budget_max: rec.budget_max || 0,
                    property_id: m2o(rec.property_id),
                    agent_id: m2o(rec.agent_id),
                    description: rec.description || "",
                };
            }
        }
        this.state.loading = false;
    }

    get drawerTitle() {
        return this.props.leadId ? "Modifier la piste" : "Nouvelle piste";
    }

    setField(field, ev) {
        this.state.form[field] = ev.target.value;
    }
    setNumber(field, ev) {
        this.state.form[field] = Number(ev.target.value) || 0;
    }
    setM2O(field, ev) {
        this.state.form[field] = ev.target.value ? parseInt(ev.target.value) : false;
    }

    buildVals() {
        const f = this.state.form;
        return {
            name: f.name || "Piste sans titre",
            partner_id: f.partner_id || false,
            contact_name: f.contact_name || false,
            email: f.email || false,
            phone: f.phone || false,
            source_id: f.source_id || false,
            status: f.status,
            score: Number(f.score) || 0,
            transaction: f.transaction || false,
            budget_min: Number(f.budget_min) || 0,
            budget_max: Number(f.budget_max) || 0,
            property_id: f.property_id || false,
            agent_id: f.agent_id || false,
            description: f.description || false,
        };
    }

    async save() {
        if (!this.state.form.name.trim()) {
            this.state.error = "Le titre est obligatoire.";
            return;
        }
        this.state.saving = true;
        this.state.error = "";
        try {
            const vals = this.buildVals();
            if (this.props.leadId) {
                await this.orm.write("civora.lead", [this.props.leadId], vals);
            } else {
                await this.orm.create("civora.lead", [vals]);
            }
            this.props.onClose(true);
        } catch (e) {
            this.state.error = "Enregistrement impossible.";
            this.state.saving = false;
        }
    }
}
