import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

/**
 * Ecran "Bientot disponible" affiche par les apps coquilles CIVORA.
 * Une seule action pour toutes : le nom affiche est celui de l'app courante.
 */
export class CivoraPlaceholder extends Component {
    static template = "civora_agence.Placeholder";
    static props = { ...standardActionServiceProps };

    setup() {
        this.menu = useService("menu");
    }

    get moduleName() {
        const app = this.menu.getCurrentApp();
        return app ? app.name : "Ce module";
    }
}

registry.category("actions").add("civora.placeholder", CivoraPlaceholder);
