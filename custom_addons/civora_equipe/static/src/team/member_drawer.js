/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CivoraDrawer } from "@civora_core/components/civora_drawer";

export class MemberDrawer extends Component {
    static template = "civora_equipe.MemberDrawer";
    static components = { CivoraDrawer };
    static props = {
        onClose: Function,
        onSaved: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            users: [],
            roles: [],
            form: {
                user_id: "",
                role_id: "",
                department: "commercial",
                phone: "",
                bio: "",
                hire_date: "",
            },
        });
        onWillStart(() => this.loadOptions());
    }

    async loadOptions() {
        const [users, roles] = await Promise.all([
            this.orm.searchRead("res.users", [["active", "=", true]], ["name"], { order: "name" }),
            this.orm.searchRead("civora.agent.role", [["active", "=", true]], ["name"], { order: "sequence" }),
        ]);
        this.state.users = users;
        this.state.roles = roles;
    }

    updateField(field, ev) {
        this.state.form[field] = ev.target.value;
    }

    async save() {
        const f = this.state.form;
        if (!f.user_id) return;
        const vals = {
            user_id: parseInt(f.user_id),
            department: f.department,
        };
        if (f.role_id) vals.role_id = parseInt(f.role_id);
        if (f.phone) vals.phone = f.phone;
        if (f.bio) vals.bio = f.bio;
        if (f.hire_date) vals.hire_date = f.hire_date;
        await this.orm.create("civora.team.member", [vals]);
        this.props.onSaved();
    }
}
