import { Component, useState, useRef, onWillDestroy } from "@odoo/owl";
import { user } from "@web/core/user";

/**
 * Selecteur de societe CIVORA, integre en bas de la sidebar permanente.
 *
 * Choix d'implementation : on s'appuie sur l'objet `user` (@web/core/user),
 * disponible de facon fiable partout (contrairement au service "company" qui
 * n'est pas expose dans le contexte d'un main_component comme la sidebar), et
 * on applique le changement de societe via le parametre d'URL `cids` suivi d'un
 * rechargement — c'est le mecanisme natif d'Odoo, stable entre les versions.
 *
 * - Affiche la societe active (logo res.company ou initiale + nom).
 * - Se deplie vers le HAUT pour lister les societes autorisees.
 * - Multi-societe : cases a cocher pour activer plusieurs societes ; clic sur
 *   le nom pour basculer en societe principale.
 * - S'auto-masque s'il n'y a qu'une seule societe autorisee.
 */
export class NkCompanySwitcher extends Component {
    static template = "nk_backend_theme.CompanySwitcher";
    static props = {};

    setup() {
        this.state = useState({ open: false });
        this.rootRef = useRef("root");

        this._onDocClick = (ev) => {
            if (this.state.open && this.rootRef.el && !this.rootRef.el.contains(ev.target)) {
                this.state.open = false;
            }
        };
        document.addEventListener("click", this._onDocClick, true);
        onWillDestroy(() => document.removeEventListener("click", this._onDocClick, true));
    }

    // --- Donnees (via l'objet user, fiable partout) ---------------------
    get companies() {
        // user.allowedCompanies : dict {id: {id, name, ...}} en Odoo 19.
        const all = user.allowedCompanies || {};
        return Object.values(all).sort((a, b) => (a.sequence || 0) - (b.sequence || 0));
    }
    get hasMultiple() {
        return this.companies.length > 1;
    }
    get canShow() {
        return this.companies.length >= 1;
    }
    get activeIds() {
        // Ids des societes actuellement actives (selection multi-societe).
        return user.activeCompanyIds || (user.activeCompany ? [user.activeCompany.id] : []);
    }
    get currentCompanyId() {
        return user.activeCompany ? user.activeCompany.id : (this.activeIds[0] || false);
    }
    get currentName() {
        const co = this.companies.find((c) => c.id === this.currentCompanyId);
        return co ? co.name : (user.activeCompany ? user.activeCompany.name : "");
    }
    get currentInitial() {
        const n = (this.currentName || "").trim();
        return n ? n[0].toUpperCase() : "?";
    }
    logoUrl(companyId) {
        return "/web/image/res.company/" + companyId + "/logo";
    }
    isActive(companyId) {
        return this.activeIds.includes(companyId);
    }
    isCurrent(companyId) {
        return this.currentCompanyId === companyId;
    }
    initialOf(name) {
        const n = (name || "").trim();
        return n ? n[0].toUpperCase() : "?";
    }

    // --- Application du changement -------------------------------------
    _companyService() {
        // Recupere le service "company" AU MOMENT DU CLIC (le webclient est
        // alors entierement demarre, contrairement au setup de la sidebar).
        const svcs = (this.env && this.env.services) || {};
        return svcs.company || svcs.company_service || null;
    }

    _applyCompanies(ids, primaryId) {
        const ordered = [primaryId, ...ids.filter((id) => id !== primaryId)];
        const svc = this._companyService();
        // Voie ideale : le service natif gere le switch proprement (sans reload
        // brutal, avec la bonne synchronisation serveur).
        if (svc && typeof svc.setCompanies === "function") {
            try {
                svc.setCompanies(ordered, false);
                return;
            } catch (e) {
                try {
                    svc.setCompanies("loginto", primaryId);
                    return;
                } catch (e2) {
                    // on retombe sur le cookie ci-dessous
                }
            }
        }
        // Repli robuste : cookie "cids" (format Odoo, ids separes par tirets)
        // puis rechargement.
        document.cookie = "cids=" + ordered.join("-") + "; path=/; max-age=" + (60 * 60 * 24 * 365);
        window.location.reload();
    }

    // --- Interactions ----------------------------------------------------
    toggle() {
        if (!this.hasMultiple) {
            return;
        }
        this.state.open = !this.state.open;
    }

    switchTo(companyId) {
        if (this.isCurrent(companyId) && this.activeIds.length === 1) {
            this.state.open = false;
            return;
        }
        this._applyCompanies([companyId], companyId);
    }

    toggleCompany(companyId, ev) {
        if (ev) {
            ev.stopPropagation();
        }
        const active = new Set(this.activeIds);
        if (active.has(companyId)) {
            if (active.size === 1) {
                return; // au moins une societe doit rester active
            }
            active.delete(companyId);
        } else {
            active.add(companyId);
        }
        const ids = [...active];
        const primary = active.has(this.currentCompanyId) ? this.currentCompanyId : ids[0];
        this._applyCompanies(ids, primary);
    }

    selectAll(ev) {
        if (ev) {
            ev.stopPropagation();
        }
        const ids = this.companies.map((c) => c.id);
        const primary = this.currentCompanyId || ids[0];
        this._applyCompanies(ids, primary);
    }
}
