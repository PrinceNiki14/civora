import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService, useBus } from "@web/core/utils/hooks";
import { computeAppsAndMenuItems } from "@web/webclient/menus/menu_helpers";
import { user } from "@web/core/user";
import { BRANDING } from "../branding/nk_branding";
import { SIDEBAR_SECTIONS, SIDEBAR_OPTIONS } from "./nk_sidebar_config";
import { NkCompanySwitcher } from "./nk_company_switcher";

/**
 * Barre laterale gauche permanente, organisee en SECTIONS (facon CIVORA).
 * - Sections + entrees definies dans nk_sidebar_config.js
 * - Chaque entree est resolue par xmlid (prioritaire) ou par nom de menu
 * - Entrees introuvables ignorees ; apps non mappees regroupees dans "AUTRES"
 * - Surlignage de l'app / accueil courant
 * - Bas de sidebar : utilisateur courant + deconnexion
 */
export class NkSidebar extends Component {
    static template = "nk_backend_theme.Sidebar";
    static components = { NkCompanySwitcher };
    static props = {};

    setup() {
        this.menu = useService("menu");
        this.homeMenu = useService("home_menu");
        this.brand = BRANDING;
        this.options = SIDEBAR_OPTIONS;
        this.state = useState({ mobileOpen: false });

        // Re-render au changement d'app OU au basculement de l'accueil.
        // On en profite pour refermer le volet mobile apres navigation.
        useBus(this.env.bus, "MENUS:APP-CHANGED", () => {
            this.state.mobileOpen = false;
            this.render();
        });
        useBus(this.env.bus, "HOME-MENU:TOGGLED", () => {
            this.state.mobileOpen = false;
            this.render();
        });
    }

    // --- Volet mobile ----------------------------------------------------
    toggleMobile() {
        this.state.mobileOpen = !this.state.mobileOpen;
    }
    closeMobile() {
        this.state.mobileOpen = false;
    }

    get userName() {
        return user.name || "";
    }

    // --- Etat courant ----------------------------------------------------
    get isHomeActive() {
        return Boolean(this.homeMenu.hasHomeMenu);
    }

    get currentAppId() {
        const app = this.menu.getCurrentApp();
        return app ? app.appID : null;
    }

    // --- Index des menus (xmlid / nom) -----------------------------------
    _flatten() {
        const out = [];
        const walk = (node) => {
            if (node.id) {
                out.push(node);
            }
            (node.childrenTree || []).forEach(walk);
        };
        walk(this.menu.getMenuAsTree("root"));
        return out;
    }

    _buildIndex() {
        const byXml = {};
        const byName = {};
        for (const m of this._flatten()) {
            if (m.xmlid && !(m.xmlid in byXml)) {
                byXml[m.xmlid] = m;
            }
            const key = (m.name || "").toLowerCase();
            if (key && !(key in byName)) {
                byName[key] = m;
            }
        }
        return { byXml, byName };
    }

    _resolve(item, index) {
        if (item.xmlid && index.byXml[item.xmlid]) {
            return index.byXml[item.xmlid];
        }
        if (item.name && index.byName[item.name.toLowerCase()]) {
            return index.byName[item.name.toLowerCase()];
        }
        return null;
    }

    // --- Construction des sections a afficher ----------------------------
    get renderSections() {
        const index = this._buildIndex();
        const used = new Set();
        const sections = [];

        for (const sec of SIDEBAR_SECTIONS) {
            const items = [];
            for (const it of sec.items) {
                if (it.home) {
                    items.push({
                        key: "home",
                        home: true,
                        icon: it.icon || "fa fa-home",
                        label: it.label || "Accueil",
                        active: this.isHomeActive,
                    });
                    continue;
                }
                const m = this._resolve(it, index);
                if (!m || !m.actionID) {
                    continue; // module non installe -> ignore
                }
                used.add(m.appID);
                items.push({
                    key: m.id,
                    menu: m,
                    icon: it.icon || "fa fa-circle-o",
                    label: it.label || m.name,
                    active: !this.isHomeActive && this.currentAppId === m.appID,
                });
            }
            if (items.length) {
                sections.push({ label: sec.label, items });
            }
        }

        // Section "AUTRES" : apps installees non referencees ci-dessus.
        if (this.options.showOthers) {
            const apps = computeAppsAndMenuItems(this.menu.getMenuAsTree("root")).apps;
            const others = apps
                .filter((a) => !used.has(a.appID))
                .map((a) => ({
                    key: a.id,
                    app: a,
                    label: a.label,
                    active: !this.isHomeActive && this.currentAppId === a.appID,
                }));
            if (others.length) {
                sections.push({ label: this.options.othersLabel, items: others, isOthers: true });
            }
        }

        return sections;
    }

    // --- Actions ---------------------------------------------------------
    openItem(item) {
        this.state.mobileOpen = false;
        if (item.home) {
            return this.homeMenu.toggle(true);
        }
        if (item.menu) {
            return this.menu.selectMenu(item.menu);
        }
        if (item.app) {
            return this.menu.selectMenu(item.app);
        }
    }

    goHome() {
        this.state.mobileOpen = false;
        return this.homeMenu.toggle(true);
    }

    logout() {
        window.location.href = "/web/session/logout";
    }
}

registry.category("main_components").add("NkSidebar", { Component: NkSidebar });
