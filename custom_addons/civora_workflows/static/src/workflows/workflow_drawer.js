/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CivoraDrawer } from "@civora_core/components/civora_drawer";

export class WorkflowDrawer extends Component {
    static template = "civora_workflows.WorkflowDrawer";
    static components = { CivoraDrawer };
    static props = {
        onSaved: { type: Function },
        onClose: { type: Function },
        editId: { optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.form = useState({
            name: "",
            category: "gestion",
            trigger_type: "event",
            trigger_description: "",
            description: "",
        });
        onWillStart(async () => {
            if (this.props.editId) {
                const records = await this.orm.read(
                    "civora.workflow.template",
                    [this.props.editId],
                    ["name", "category", "trigger_type", "trigger_description", "description"],
                );
                if (records.length) {
                    const rec = records[0];
                    this.form.name = rec.name || "";
                    this.form.category = rec.category || "gestion";
                    this.form.trigger_type = rec.trigger_type || "event";
                    this.form.trigger_description = rec.trigger_description || "";
                    this.form.description = rec.description || "";
                }
            }
        });
    }

    get isEdit() {
        return !!this.props.editId;
    }

    get drawerTitle() {
        return this.isEdit ? "Modifier l'automatisation" : "Nouvelle automatisation";
    }

    async save() {
        if (!this.form.name) return;
        const vals = {
            name: this.form.name,
            category: this.form.category,
            trigger_type: this.form.trigger_type,
            trigger_description: this.form.trigger_description || false,
            description: this.form.description || false,
        };
        if (this.isEdit) {
            await this.orm.write("civora.workflow.template", [this.props.editId], vals);
        } else {
            await this.orm.create("civora.workflow.template", [vals]);
        }
        this.props.onSaved();
    }
}
