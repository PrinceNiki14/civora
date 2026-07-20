import { Component } from "@odoo/owl";

/**
 * CIVORA Drawer / Modale - conteneur reutilisable (overlay + panneau + header).
 *
 *   variant="drawer" (defaut) : panneau lateral droit, animation slide-in.
 *   variant="modal"           : modale CENTREE (carte), animation pop.
 *
 * Contenu principal via slot par defaut ; actions de pied via slot "footer".
 * Icone d'en-tete optionnelle (badge accent) via la prop `icon` (classe FontAwesome).
 * Largeur de la modale via `size` ("sm" | "md" | "lg" | "xl", defaut "lg").
 *
 * Retro-compatible : sans prop `variant`, le comportement du panneau lateral
 * existant (etape 1.3) est inchange.
 */
export class CivoraDrawer extends Component {
    static template = "civora_core.Drawer";
    static props = {
        title: { type: String, optional: true },
        subtitle: { type: String, optional: true },
        icon: { type: String, optional: true },      // ex: "fa-user-o"
        variant: { type: String, optional: true },   // "drawer" | "modal"
        size: { type: String, optional: true },      // "sm" | "md" | "lg" | "xl"
        onClose: Function,
        slots: { type: Object, optional: true },
    };

    get variant() {
        return this.props.variant === "modal" ? "modal" : "drawer";
    }

    get size() {
        return this.props.size || (this.variant === "modal" ? "lg" : "md");
    }

    get rootClass() {
        return "civora-drawer civora-drawer--" + this.variant + " civora-drawer--" + this.size;
    }
}
