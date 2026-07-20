import { Component } from "@odoo/owl";

// =====================================================================
// CIVORA CORE - Kit de composants reutilisables (portage de ui-kit.tsx)
// =====================================================================

/** Badge colore (variants alignes sur le front). */
export class CivoraBadge extends Component {
    static template = "civora_core.Badge";
    static props = {
        label: { type: String, optional: true },
        variant: { type: String, optional: true }, // success|warning|info|neutral|danger|accent|primary
        slots: { type: Object, optional: true },
    };
    get variant() {
        return this.props.variant || "neutral";
    }
}

/** Avatar avec initiales (ou image), tailles sm/md/lg/xl. */
export class CivoraAvatar extends Component {
    static template = "civora_core.Avatar";
    static props = {
        name: { type: String, optional: true },
        size: { type: String, optional: true },     // sm|md|lg|xl
        gradient: { type: String, optional: true }, // brand|accent
        src: { type: String, optional: true },
    };
    get initials() {
        return (this.props.name || "")
            .split(" ")
            .filter(Boolean)
            .slice(0, 2)
            .map((s) => s[0])
            .join("")
            .toUpperCase();
    }
    get sizeClass() {
        return "civora-av-" + (this.props.size || "lg");
    }
    get gradientClass() {
        return this.props.gradient === "accent" ? "civora-av-accent" : "civora-av-brand";
    }
}

/** Onglets soulignes (label + compteur optionnel). */
export class CivoraTabs extends Component {
    static template = "civora_core.Tabs";
    static props = {
        tabs: Array,          // [{ id, label, count? }]
        active: String,
        onChange: Function,
    };
}

/** Barre de progression coloree (0-100). */
export class CivoraProgress extends Component {
    static template = "civora_core.Progress";
    static props = {
        value: Number,
        tone: { type: String, optional: true }, // accent|primary|warning|danger|success|info
    };
    get width() {
        return Math.max(0, Math.min(100, this.props.value || 0));
    }
    get toneClass() {
        return "civora-pg-" + (this.props.tone || "accent");
    }
}
