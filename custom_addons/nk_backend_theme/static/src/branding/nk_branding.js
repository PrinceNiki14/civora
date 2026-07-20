import { registry } from "@web/core/registry";

// =====================================================================
// NK SERVICE - Configuration de marque (source unique)
// =====================================================================
// Un seul endroit a modifier pour rebrander tout le backend :
//  - nom affiche dans la sidebar et l'onglet navigateur
//  - logo de la sidebar
//
// Pour le logo, 3 options pour "logoUrl" :
//   ""                                        -> affiche les initiales (defaut)
//   "/nk_backend_theme/static/src/img/logo.png" -> logo statique (deposez le fichier)
//   "/web/image/res.company/1/logo"           -> logo de la societe (auto par client)
// =====================================================================
export const BRANDING = {
    name: "CIVORA 360°",
    tagline: "AI PropTech OS",
    initials: "C",
    logoUrl: "",
};

// ---------------------------------------------------------------------
// Titre de l'onglet navigateur : on ajoute le nom du produit comme
// suffixe permanent (remplace le "Odoo" par defaut des pages vides).
// ---------------------------------------------------------------------
const nkBrandingService = {
    dependencies: ["title"],
    start(env, { title }) {
        title.setParts({ nk_brand: BRANDING.name });
    },
};
registry.category("services").add("nk_branding", nkBrandingService);
