import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { computeAppsAndMenuItems } from "@web/webclient/menus/menu_helpers";
import { user } from "@web/core/user";
import { _t } from "@web/core/l10n/translation";

// Devise affichee sur les KPI monetaires.
// (A terme on pourra la tirer de la societe : company.currentCompany.currency)
const CURRENCY = "FCFA";

/**
 * Formate un montant en version compacte facon "35,8 M FCFA" / "2,1 Md FCFA".
 */
function formatCompact(value) {
    const v = value || 0;
    const n = Math.abs(v);
    let out;
    if (n >= 1e9) {
        out = (v / 1e9).toFixed(1).replace(".", ",") + " Md";
    } else if (n >= 1e6) {
        out = (v / 1e6).toFixed(1).replace(".", ",") + " M";
    } else if (n >= 1e3) {
        out = Math.round(v / 1e3).toString() + " k";
    } else {
        out = Math.round(v).toString();
    }
    return out + " " + CURRENCY;
}

/**
 * Ecran d'accueil NK SERVICE ("Command Center").
 * Remplace l'action "menu" (grille d'apps) de web_enterprise.
 * Affiche des KPI reels + conserve l'acces aux applications.
 */
export class NkHomeDashboard extends Component {
    static template = "nk_backend_theme.HomeDashboard";
    static target = "current";
    static props = { ...standardActionServiceProps };
    static displayName = _t("Accueil");

    setup() {
        this.orm = useService("orm");
        this.menu = useService("menu");

        // Liste des applications, calculee comme dans le home menu natif.
        this.apps = computeAppsAndMenuItems(this.menu.getMenuAsTree("root")).apps;

        this.state = useState({
            loading: true,
            kpis: [],
        });

        onWillStart(() => this.loadDashboard());
    }

    get companyName() {
        // user.activeCompany = societe principale sur laquelle l'utilisateur est connecte
        return (user.activeCompany && user.activeCompany.name) || "";
    }

    get subtitle() {
        const nbApps = this.apps.length;
        return _t("%s application(s) disponible(s)", nbApps);
    }

    // --- Helpers ORM ----------------------------------------------------

    /** Premier jour du mois courant au format YYYY-MM-DD. */
    _monthStart() {
        const d = new Date();
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, "0");
        return `${y}-${m}-01`;
    }

    /** Somme d'un champ (Odoo 19 : formatted_read_group avec "champ:sum"). */
    async _sum(model, domain, field) {
        const groups = await this.orm.formattedReadGroup(model, domain, [], [`${field}:sum`]);
        return groups.length ? (groups[0][`${field}:sum`] || 0) : 0;
    }

    /** Nombre d'enregistrements. */
    async _count(model, domain) {
        return this.orm.searchCount(model, domain);
    }

    /**
     * Execute une requete en la protegeant : si le modele/champ n'existe pas
     * (module non installe, droits insuffisants...), on renvoie null au lieu
     * de faire planter tout le tableau de bord.
     */
    async _safe(fn) {
        try {
            return await fn();
        } catch {
            return null;
        }
    }

    // --- Chargement des KPI ---------------------------------------------

    async loadDashboard() {
        const monthStart = this._monthStart();
        const kpis = [];

        // 1) CA facture du mois (factures clients validees)
        const caMois = await this._safe(() =>
            this._sum(
                "account.move",
                [
                    ["move_type", "=", "out_invoice"],
                    ["state", "=", "posted"],
                    ["invoice_date", ">=", monthStart],
                ],
                "amount_total"
            )
        );
        if (caMois !== null) {
            kpis.push({
                id: "ca_mois",
                label: _t("CA facture du mois"),
                value: formatCompact(caMois),
                icon: "fa-line-chart",
                accent: "green",
            });
        }

        // 2) Factures impayees (restant du)
        const impayeDomain = [
            ["move_type", "=", "out_invoice"],
            ["state", "=", "posted"],
            ["payment_state", "in", ["not_paid", "partial"]],
        ];
        const impaye = await this._safe(() => this._sum("account.move", impayeDomain, "amount_residual"));
        if (impaye !== null) {
            const nb = await this._safe(() => this._count("account.move", impayeDomain));
            kpis.push({
                id: "impaye",
                label: _t("Factures impayees"),
                value: formatCompact(impaye),
                sub: nb !== null ? _t("%s facture(s)", nb) : "",
                icon: "fa-exclamation-circle",
                accent: "red",
            });
        }

        // 3) Devis en cours (module Ventes - protege)
        const devisDomain = [["state", "in", ["draft", "sent"]]];
        const devis = await this._safe(() => this._count("sale.order", devisDomain));
        if (devis !== null) {
            const devisAmt = await this._safe(() => this._sum("sale.order", devisDomain, "amount_total"));
            kpis.push({
                id: "devis",
                label: _t("Devis en cours"),
                value: String(devis),
                sub: devisAmt !== null ? formatCompact(devisAmt) : "",
                icon: "fa-file-text-o",
                accent: "blue",
            });
        }

        // 4) Ventes confirmees du mois (module Ventes - protege)
        const cmdMois = await this._safe(() =>
            this._sum(
                "sale.order",
                [
                    ["state", "=", "sale"],
                    ["date_order", ">=", monthStart],
                ],
                "amount_total"
            )
        );
        if (cmdMois !== null) {
            kpis.push({
                id: "cmd_mois",
                label: _t("Ventes confirmees (mois)"),
                value: formatCompact(cmdMois),
                icon: "fa-shopping-cart",
                accent: "green",
            });
        }

        // 5) Clients
        const clients = await this._safe(() => this._count("res.partner", [["customer_rank", ">", 0]]));
        if (clients !== null) {
            kpis.push({
                id: "clients",
                label: _t("Clients"),
                value: String(clients),
                icon: "fa-users",
                accent: "violet",
            });
        }

        // 6) Opportunites CRM (module CRM - protege)
        const oppsDomain = [["type", "=", "opportunity"]];
        const opps = await this._safe(() => this._count("crm.lead", oppsDomain));
        if (opps !== null) {
            const oppAmt = await this._safe(() => this._sum("crm.lead", oppsDomain, "expected_revenue"));
            kpis.push({
                id: "opps",
                label: _t("Opportunites"),
                value: String(opps),
                sub: oppAmt !== null ? _t("%s attendus", formatCompact(oppAmt)) : "",
                icon: "fa-bullseye",
                accent: "blue",
            });
        }

        this.state.kpis = kpis;
        this.state.loading = false;
    }

    // --- Navigation ------------------------------------------------------

    /** Ouvre une application (comme le home menu natif). */
    openApp(app) {
        return this.menu.selectMenu(app);
    }
}

// NOTE : l'ecran d'accueil est desormais fourni par le module civora_core
// (Command Center). Cet ancien dashboard n'est plus enregistre comme action "menu".
