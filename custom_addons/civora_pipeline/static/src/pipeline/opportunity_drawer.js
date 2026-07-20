import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CivoraDrawer } from "@civora_core/components/civora_drawer";

const TRANSACTIONS = [
    { value: "", label: "—" },
    { value: "vente", label: "Vente" },
    { value: "location", label: "Location" },
    { value: "saisonnier", label: "Saisonnier" },
];

export class OpportunityDrawer extends Component {
    static template = "civora_pipeline.OpportunityDrawer";
    static components = { CivoraDrawer };
    static props = {
        opportunityId: { type: [Number, Boolean], optional: true },
        onClose: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.transactions = TRANSACTIONS;
        this.partners = [];
        this.properties = [];
        this.propertyMap = {};
        this.users = [];
        this.stages = [];
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
            name: "", partner_id: false, property_id: false, transaction: false,
            stage_id: false, expected_amount: 0, probability: 0, score: 0,
            agent_id: false, date_close: false, description: "",
        };
    }

    async load() {
        this.state.loading = true;
        this.partners = await this.orm.searchRead(
            "res.partner", [["civora_is_contact", "=", true]], ["name"], { limit: 500, order: "name" }
        );
        this.properties = await this.orm.searchRead(
            "civora.property", [], ["name", "price", "monthly_revenue", "transaction"], { limit: 500, order: "name" }
        );
        for (const p of this.properties) this.propertyMap[p.id] = p;
        this.users = await this.orm.searchRead("res.users", [["share", "=", false]], ["name"], { order: "name" });
        this.stages = await this.orm.searchRead(
            "civora.pipeline.stage", [], ["name"], { order: "sequence, id" }
        );

        if (this.props.opportunityId) {
            const m2o = (v) => (v ? v[0] : false);
            const [rec] = await this.orm.read("civora.opportunity", [this.props.opportunityId], [
                "name", "partner_id", "property_id", "transaction", "stage_id",
                "expected_amount", "probability", "score", "agent_id", "date_close", "description",
            ]);
            if (rec) {
                this.state.form = {
                    name: rec.name || "",
                    partner_id: m2o(rec.partner_id),
                    property_id: m2o(rec.property_id),
                    transaction: rec.transaction || false,
                    stage_id: m2o(rec.stage_id),
                    expected_amount: rec.expected_amount || 0,
                    probability: rec.probability || 0,
                    score: rec.score || 0,
                    agent_id: m2o(rec.agent_id),
                    date_close: rec.date_close || false,
                    description: rec.description || "",
                };
            }
        } else if (this.stages.length) {
            this.state.form.stage_id = this.stages[0].id;
        }
        this.state.loading = false;
    }

    get drawerTitle() {
        return this.props.opportunityId ? "Modifier l'opportunité" : "Nouvelle opportunité";
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
    onPropertyChange(ev) {
        const id = ev.target.value ? parseInt(ev.target.value) : false;
        this.state.form.property_id = id;
        const p = id ? this.propertyMap[id] : null;
        if (p) {
            if (!this.state.form.transaction && p.transaction) this.state.form.transaction = p.transaction;
            if (!this.state.form.expected_amount) {
                this.state.form.expected_amount = p.transaction === "vente"
                    ? (p.price || 0) : (p.monthly_revenue || p.price || 0);
            }
            if (!this.state.form.name.trim()) {
                this.state.form.name = p.name;
            }
        }
    }

    buildVals() {
        const f = this.state.form;
        return {
            name: f.name || "Opportunité",
            partner_id: f.partner_id || false,
            property_id: f.property_id || false,
            transaction: f.transaction || false,
            stage_id: f.stage_id || false,
            expected_amount: Number(f.expected_amount) || 0,
            probability: Number(f.probability) || 0,
            score: Number(f.score) || 0,
            agent_id: f.agent_id || false,
            date_close: f.date_close || false,
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
            if (this.props.opportunityId) {
                await this.orm.write("civora.opportunity", [this.props.opportunityId], vals);
            } else {
                await this.orm.create("civora.opportunity", [vals]);
            }
            this.props.onClose(true);
        } catch (e) {
            this.state.error = "Enregistrement impossible.";
            this.state.saving = false;
        }
    }
}
