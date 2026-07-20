import { patch } from "@web/core/utils/patch";
import { NavBar } from "@web/webclient/navbar/navbar";

// =====================================================================
// CIVORA - Nettoyage du systray (rendu "produit" facon CIVORA)
// On filtre les items Odoo au rendu de la navbar : on ne garde qu'une
// cloche (messagerie) + l'avatar, aux cotes de la recherche et de Ask AI.
//
// Pour REACTIVER un element, retirez sa cle de l'ensemble ci-dessous.
// (ex : "SwitchCompanyMenu" si vous gerez plusieurs societes)
// =====================================================================
const CIVORA_HIDDEN_SYSTRAY = new Set([
    "web.debug_mode_menu", // icone "outils" (mode debug)
    "mail.activity_menu",  // horloge des activites
    "SwitchCompanyMenu",   // selecteur de societe
]);

patch(NavBar.prototype, {
    get systrayItems() {
        return super.systrayItems.filter((item) => !CIVORA_HIDDEN_SYSTRAY.has(item.key));
    },
});
