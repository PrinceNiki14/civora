import { registry } from "@web/core/registry";

// =====================================================================
// CIVORA - Menu utilisateur (avatar) : retrait des entrees marque Odoo
// (edition Community : retrait autorise).
//   - "support"      -> "Aide" (doc/support Odoo)
//   - "odoo_account" -> "Mon compte Odoo.com"
// On conserve : raccourcis, preferences, installer l'app, deconnexion.
//
// Pour REACTIVER une entree, retirez sa cle de la liste ci-dessous.
// =====================================================================
const userMenu = registry.category("user_menuitems");

for (const key of ["support", "odoo_account"]) {
    if (userMenu.contains(key)) {
        userMenu.remove(key);
    }
}
