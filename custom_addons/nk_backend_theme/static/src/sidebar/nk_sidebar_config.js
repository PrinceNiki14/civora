// =====================================================================
// NK / CIVORA - Configuration de la sidebar (sections + entrees)
// =====================================================================
// Chaque entree cible un menu Odoo par :
//   - "xmlid"  : identifiant technique exact (recommande, ex. coquilles CIVORA)
//   - ou "name": nom du menu (secours ; utile pour les apps natives Odoo)
// Options par entree :
//   - "icon"   : classe Font Awesome (icone monochrome facon CIVORA)
//   - "label"  : libelle affiche (sinon nom du menu)
//   - "home"   : true => entree speciale "Accueil / Command Center"
//
// Les entrees introuvables (module non installe) sont simplement ignorees.
// Pour reordonner : deplacez les lignes. Pour deplacer une entree de
// section : coupez/collez la ligne dans une autre section.
// =====================================================================

export const SIDEBAR_SECTIONS = [
    {
        label: "PILOTAGE",
        items: [
            { home: true, icon: "fa fa-th-large", label: "Command Center" },
            { xmlid: "civora_agence.menu_ia_insights", icon: "fa fa-magic", label: "IA & Insights" },
            { xmlid: "civora_agence.menu_market_pulse", icon: "fa fa-line-chart", label: "Market Pulse" },
            { xmlid: "civora_agence.menu_rapports", icon: "fa fa-bar-chart", label: "Rapports" },
        ],
    },
    {
        label: "CRM",
        items: [
            { xmlid: "civora_contacts.menu_civora_contacts", icon: "fa fa-address-card-o", label: "Contacts" },
            { xmlid: "civora_pipeline.menu_pistes", icon: "fa fa-bullseye", label: "Pistes" },
            { xmlid: "civora_pipeline.menu_pipeline", icon: "fa fa-filter", label: "Pipeline" },
            { xmlid: "civora_calendar.menu_calendrier", icon: "fa fa-calendar-o", label: "Calendrier" },
        ],
    },
    {
        label: "IMMOBILIER",
        items: [
            { xmlid: "civora_agence.menu_biens", icon: "fa fa-building-o", label: "Biens" },
            { xmlid: "civora_agence.menu_programmes", icon: "fa fa-cubes", label: "Programmes" },
            { xmlid: "civora_agence.menu_locations", icon: "fa fa-key", label: "Locations" },
            { xmlid: "civora_agence.menu_saisonnier", icon: "fa fa-calendar-check-o", label: "Saisonnier" },
            { xmlid: "civora_agence.menu_ventes", icon: "fa fa-handshake-o", label: "Ventes" },
        ],
    },
    {
        label: "GESTION",
        items: [
            { xmlid: "civora_agence.menu_proprietaires", icon: "fa fa-user-circle-o", label: "Propriétaires" },
            { xmlid: "civora_agence.menu_locataires", icon: "fa fa-users", label: "Locataires" },
            { xmlid: "civora_agence.menu_acquereurs", icon: "fa fa-user-plus", label: "Acquéreurs" },
            { name: "Comptabilité", icon: "fa fa-calculator" },
        ],
    },
    {
        label: "OPÉRATIONS",
        items: [
            { name: "Documents", icon: "fa fa-file-text-o" },
            { xmlid: "civora_agence.menu_workflows", icon: "fa fa-random", label: "Workflows" },
            { xmlid: "civora_agence.menu_equipe", icon: "fa fa-user-o", label: "Équipe" },
        ],
    },
    {
        label: "SYSTÈME",
        items: [
            { name: "Utilisateurs", icon: "fa fa-users" },
            { name: "Paramètres", icon: "fa fa-cog" },
        ],
    },
];

export const SIDEBAR_OPTIONS = {
    // Affiche une section "AUTRES" avec les apps installees non mappees ci-dessus
    // (mettez false pour un menu strictement CIVORA).
    showOthers: true,
    othersLabel: "AUTRES",
};
