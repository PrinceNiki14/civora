import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

/**
 * Pill de recherche globale (facon CIVORA) -> ouvre la palette de commande (Ctrl/Cmd+K).
 */
export class CivoraSearch extends Component {
    static template = "civora_core.SearchSystray";
    static props = {};
    setup() {
        this.command = useService("command");
    }
    openSearch() {
        this.command.openMainPalette();
    }
}

/**
 * Bouton "Ask CIVORA AI" (vert). Placeholder pour l'assistant IA a venir.
 */
export class CivoraAskAI extends Component {
    static template = "civora_core.AskAISystray";
    static props = {};
    setup() {
        this.notification = useService("notification");
    }
    ask() {
        this.notification.add(_t("L'assistant IA CIVORA arrive bientôt."), {
            title: "Ask CIVORA AI",
            type: "info",
        });
    }
}

// Sequences elevees = plus a gauche dans le systray (l'avatar est en sequence 0, a droite).
registry.category("systray").add("civora.search", { Component: CivoraSearch }, { sequence: 130 });
registry.category("systray").add("civora.ask_ai", { Component: CivoraAskAI }, { sequence: 120 });
