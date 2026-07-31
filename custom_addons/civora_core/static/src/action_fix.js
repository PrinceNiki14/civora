import { registry } from "@web/core/registry";

const civoraActionFixService = {
    dependencies: ["action"],
    start(env, { action }) {
        const url = window.location.pathname;

        let targetAction = null;
        const match = url.match(/\/odoo\/action-(\d+)/);
        if (match) {
            targetAction = parseInt(match[1], 10);
        } else if (url === "/odoo" || url === "/odoo/" || url === "/web" || url === "/web/") {
            targetAction = "menu";
        }

        if (!targetAction) return;

        setTimeout(async () => {
            if (action.currentController) return;
            try {
                await action.doAction(targetAction);
            } catch (e) {
                // silently ignore
            }
        }, 500);
    },
};

registry.category("services").add("civora_action_fix", civoraActionFixService);
