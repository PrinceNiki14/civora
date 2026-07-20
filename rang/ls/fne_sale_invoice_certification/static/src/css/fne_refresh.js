/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";

// Intercepter l'exécution des boutons sur le formulaire de facture
patch(FormController.prototype, {
    async executeButtonCallback(clickParams) {
        const result = await super.executeButtonCallback(clickParams);
        
        // Si le bouton cliqué est "action_certify_fne" et qu'il a réussi
        if (clickParams.name === "action_certify_fne" && result) {
            // Attendre 2 secondes pour que la notification s'affiche
            setTimeout(() => {
                // Recharger le formulaire
                this.model.root.load();
            }, 2000);
        }
        
        return result;
    },
});
