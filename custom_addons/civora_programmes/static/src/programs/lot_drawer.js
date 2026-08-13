import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CivoraDrawer } from "@civora_core/components/civora_drawer";
import { LOT_TYPES, LOT_STATUSES, LOT_ORIENTATIONS } from "./lot_dialog";

const FIELDS = [
    "name", "building", "floor", "floor_label", "lot_type", "status", "price",
    "surface", "rooms", "bathrooms", "balcony", "terrace", "parking",
    "orientation", "exposure", "view", "features", "photo_urls", "notes",
    "buyer_id", "buyer_name",
];

/**
 * Panneau lateral de detail d'un lot (ouvert depuis le plan de masse,
 * la grille ou le tableau). Permet la reservation directe.
 */
export class LotDrawer extends Component {
    static template = "civora_programmes.LotDrawer";
    static components = { CivoraDrawer };
    static props = {
        lotId: Number,
        onClose: Function,
        onChanged: Function,
        onEdit: { type: Function, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({ loading: true, lot: null, busy: false });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        const [rec] = await this.orm.read("civora.program.lot", [this.props.lotId], FIELDS);
        this.state.lot = rec || null;
        this.state.loading = false;
    }

    get lot() {
        return this.state.lot || {};
    }
    get typeLabel() {
        return (LOT_TYPES.find((t) => t.id === this.lot.lot_type) || {}).label || "—";
    }
    get statusMeta() {
        return LOT_STATUSES.find((s) => s.id === this.lot.status)
            || { label: "—", variant: "neutral" };
    }
    get orientationLabel() {
        return (LOT_ORIENTATIONS.find((o) => o.id === this.lot.orientation) || {}).label || "—";
    }
    get coverClass() {
        return "civora-prg-lotcover civora-prg-lotcover--" + (this.lot.status || "disponible");
    }
    get subtitle() {
        return [this.lot.building ? "Bâtiment " + this.lot.building : "", this.lot.floor_label]
            .filter(Boolean).join(" · ");
    }
    get featureList() {
        return (this.lot.features || "").split("\n").filter(Boolean);
    }
    get photoList() {
        return (this.lot.photo_urls || "").split("\n").filter(Boolean);
    }
    get buyerLabel() {
        if (this.lot.buyer_id) return this.lot.buyer_id[1];
        return this.lot.buyer_name || "";
    }

    fmtPrice(n) {
        return new Intl.NumberFormat("fr-FR").format(Math.round(Number(n || 0))) + " FCFA";
    }

    /** Passe le lot au statut demande (Réserver / Optionner / Libérer). */
    async setStatus(status) {
        if (this.state.busy) return;
        this.state.busy = true;
        try {
            await this.orm.write("civora.program.lot", [this.props.lotId], { status });
            await this.load();
            const label = (LOT_STATUSES.find((s) => s.id === status) || {}).label || status;
            this.notification.add(`Lot ${this.lot.name} — ${label}`, { type: "success" });
            this.props.onChanged();
        } finally {
            this.state.busy = false;
        }
    }

    onEdit() {
        if (this.props.onEdit) {
            this.props.onEdit(this.props.lotId);
        }
    }
}
