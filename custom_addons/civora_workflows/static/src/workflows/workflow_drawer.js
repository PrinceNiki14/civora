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
    };

    setup() {
        this.orm = useService("orm");
        this.form = useState({
            title: "",
            template_id: "",
            category: "gestion",
            priority: "normal",
            deadline: "",
            notes: "",
        });
        this.templates = useState({ list: [] });
        onWillStart(() => this.loadTemplates());
    }

    async loadTemplates() {
        this.templates.list = await this.orm.searchRead(
            "civora.workflow.template",
            [["is_active", "=", true]],
            ["name", "category", "step_count"],
            { order: "sequence" },
        );
    }

    onTemplateChange(ev) {
        const id = parseInt(ev.target.value) || "";
        this.form.template_id = id;
        if (id) {
            const tmpl = this.templates.list.find(t => t.id === id);
            if (tmpl) {
                this.form.category = tmpl.category;
            }
        }
    }

    async save() {
        if (!this.form.title) return;
        const vals = {
            title: this.form.title,
            category: this.form.category,
            priority: this.form.priority,
            notes: this.form.notes || false,
            deadline: this.form.deadline || false,
        };
        if (this.form.template_id) {
            vals.template_id = this.form.template_id;
        }
        const id = await this.orm.create("civora.workflow", [vals]);
        if (this.form.template_id) {
            await this.orm.call("civora.workflow", "apply_template", [[id]]);
        }
        this.props.onSaved();
    }
}
