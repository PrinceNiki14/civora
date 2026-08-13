import { Component, onWillStart, useExternalListener, useRef, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Autocomplete m2o : recherche serveur avec debounce, dropdown de resultats.
 *
 * Props :
 *   model        : nom du modele Odoo (ex: "res.partner")
 *   value        : id selectionne (ou false)
 *   valueLabel   : libelle affiche pour la valeur selectionnee (ou "")
 *   domain       : domaine de recherche additionnel (defaut: [])
 *   placeholder  : placeholder de l'input
 *   context      : contexte a passer a la recherche
 *   metaField    : nom d'un champ booleen a lire pour afficher un badge dans
 *                  les resultats (ex: "civora_is_contact"). Si le champ est
 *                  a True sur un enregistrement, un badge s'affiche a droite
 *                  du libelle.
 *   metaLabel    : texte affiche dans le badge (defaut: "CIVORA")
 *   onSelect     : callback (id, label) appele au choix
 *   onClear      : callback () appele quand l'utilisateur efface
 *
 * NB : la recherche utilise search_read (et non name_search) pour permettre
 * la lecture du champ meta en un seul aller-retour. La recherche par nom est
 * faite avec un domaine 'ilike' construit cote client.
 */
export class CivoraAutocomplete extends Component {
    static template = "civora_pipeline.CivoraAutocomplete";
    static props = {
        model: String,
        value: { type: [Number, Boolean], optional: true },
        valueLabel: { type: String, optional: true },
        domain: { type: Array, optional: true },
        placeholder: { type: String, optional: true },
        context: { type: Object, optional: true },
        metaField: { type: String, optional: true },
        metaLabel: { type: String, optional: true },
        secondaryField: { type: String, optional: true },
        secondaryPrefix: { type: String, optional: true },
        onSelect: Function,
        onClear: { type: Function, optional: true },
        disabled: { type: Boolean, optional: true },
    };
    static defaultProps = {
        value: false,
        valueLabel: "",
        domain: [],
        placeholder: "Rechercher…",
        context: {},
        metaField: "",
        metaLabel: "CIVORA",
        secondaryField: "",
        secondaryPrefix: "",
        disabled: false,
    };

    setup() {
        this.orm = useService("orm");
        this.rootRef = useRef("root");
        this.state = useState({
            open: false,
            query: "",
            results: [],
            searching: false,
            highlight: -1,
        });
        this._debounce = null;
        useExternalListener(document, "mousedown", (ev) => this.onDocMouseDown(ev));
        onWillStart(async () => {
            await this.search("");
        });
    }

    get isFilled() {
        return !!this.props.value && !!this.props.valueLabel;
    }
    get showChip() {
        // Ex-t-if "isFilled and !state.query" — le "and" Python etait interdit en OWL Odoo 19.
        return this.isFilled && !this.state.query;
    }

    // ---- Recherche serveur ------------------------------------------
    async search(query) {
        this.state.searching = true;
        try {
            const baseDomain = [...(this.props.domain || [])];
            let searchDomain = baseDomain;
            const q = (query || "").trim();
            if (q) {
                // Recherche sur name + secondaryField (ex: ref) si defini
                if (this.props.secondaryField) {
                    searchDomain = [
                        ...baseDomain,
                        "|",
                        ["name", "ilike", q],
                        [this.props.secondaryField, "ilike", q],
                    ];
                } else {
                    searchDomain = [...baseDomain, ["name", "ilike", q]];
                }
            }
            const fields = ["name"];
            if (this.props.metaField) fields.push(this.props.metaField);
            if (this.props.secondaryField) fields.push(this.props.secondaryField);
            const rows = await this.orm.searchRead(
                this.props.model,
                searchDomain,
                fields,
                {
                    limit: 10,
                    order: this.props.metaField
                        ? `${this.props.metaField} desc, name asc`
                        : "name asc",
                    context: this.props.context || {},
                },
            );
            this.state.results = (rows || []).map((row) => ({
                id: row.id,
                label: row.name || `#${row.id}`,
                secondary: this.props.secondaryField ? (row[this.props.secondaryField] || "") : "",
                meta: this.props.metaField ? !!row[this.props.metaField] : false,
            }));
            this.state.highlight = this.state.results.length ? 0 : -1;
        } catch (e) {
            this.state.results = [];
            this.state.highlight = -1;
        } finally {
            this.state.searching = false;
        }
    }

    onInput(ev) {
        this.state.query = ev.target.value;
        this.state.open = true;
        if (this._debounce) clearTimeout(this._debounce);
        this._debounce = setTimeout(() => this.search(this.state.query), 180);
    }

    onFocus() {
        if (this.props.disabled) return;
        this.state.open = true;
    }

    onKey(ev) {
        if (!this.state.open) return;
        const n = this.state.results.length;
        if (ev.key === "ArrowDown") {
            ev.preventDefault();
            this.state.highlight = n ? (this.state.highlight + 1) % n : -1;
        } else if (ev.key === "ArrowUp") {
            ev.preventDefault();
            this.state.highlight = n ? (this.state.highlight - 1 + n) % n : -1;
        } else if (ev.key === "Enter") {
            ev.preventDefault();
            if (this.state.highlight >= 0 && this.state.results[this.state.highlight]) {
                this.pick(this.state.results[this.state.highlight]);
            }
        } else if (ev.key === "Escape") {
            this.state.open = false;
        }
    }

    pick(res) {
        // Construction du label enrichi : "[REF] Nom" si secondaryField défini
        let displayLabel = res.label;
        if (res.secondary) {
            const prefix = this.props.secondaryPrefix || "";
            displayLabel = `${prefix}${res.secondary} · ${res.label}`;
        }
        this.props.onSelect(res.id, displayLabel);
        this.state.open = false;
        this.state.query = "";
    }

    clear(ev) {
        if (ev) ev.stopPropagation();
        if (this.props.onClear) this.props.onClear();
        else this.props.onSelect(false, "");
        this.state.query = "";
        this.state.open = false;
    }

    onDocMouseDown(ev) {
        if (!this.state.open) return;
        const root = this.rootRef.el;
        if (root && root.contains(ev.target)) return;
        this.state.open = false;
    }
}
