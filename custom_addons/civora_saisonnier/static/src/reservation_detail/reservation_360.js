/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";

function fmtMoney(v) {
    if (!v && v !== 0) return "0";
    return Number(v).toLocaleString("fr-FR");
}

const STATE_LABELS = {
    draft: "Brouillon", confirmed: "Confirmée",
    checkin: "En séjour", checkout: "Terminée", cancelled: "Annulée",
};
const DEPOSIT_LABELS = {
    pending: "En attente", collected: "Encaissée",
    returned: "Restituée", retained: "Retenue",
};

class CivoraReservation360 extends Component {
    static template = "civora_saisonnier.Reservation360";
    static components = { CivoraStatCard };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            reservation: null,
            reviews: [],
            cleaningTasks: [],
            activeTab: "overview",
            reviewForm: { rating: 5, cleanliness_rating: 5, location_rating: 5, comfort_rating: 5, value_rating: 5, comment: "", internal_note: "" },
        });
        onWillStart(() => this.load());
    }

    get reservationId() {
        const action = this.props.action || {};
        return (action.params && action.params.reservation_id) ||
               (action.context && action.context.reservation_id);
    }

    async load() {
        const id = this.reservationId;
        if (!id) return;
        const [rec] = await this.orm.read("civora.reservation", [id], [
            "name", "property_id", "guest_id", "agent_id", "owner_id",
            "checkin_date", "checkout_date", "num_nights", "num_guests",
            "tariff_night", "total_amount", "deposit_amount", "deposit_status",
            "state", "source", "notes", "access_instructions",
            "welcome_message_sent",
        ]);
        this.state.reservation = rec;

        const [reviews, tasks] = await Promise.all([
            this.orm.searchRead("civora.reservation.review",
                [["reservation_id", "=", id]], [
                "guest_id", "rating", "cleanliness_rating", "location_rating",
                "comfort_rating", "value_rating", "comment", "internal_note", "date",
            ], { order: "date desc" }),
            this.orm.searchRead("civora.cleaning.task",
                [["reservation_id", "=", id]], [
                "property_id", "date", "time_slot", "assigned_to",
                "state", "checklist_done", "notes",
            ], { order: "date asc" }),
        ]);
        this.state.reviews = reviews;
        this.state.cleaningTasks = tasks;
    }

    fmtMoney(v) { return fmtMoney(v); }
    stateLabel(s) { return STATE_LABELS[s] || s; }
    depositLabel(s) { return DEPOSIT_LABELS[s] || s; }

    stateClass(s) {
        const m = { draft: "muted", confirmed: "info", checkin: "accent", checkout: "success", cancelled: "danger" };
        return m[s] || "";
    }

    setTab(t) { this.state.activeTab = t; }

    goBack() {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.reservations",
        });
    }

    async doAction(method) {
        const id = this.reservationId;
        try {
            await this.orm.call("civora.reservation", method, [[id]]);
            await this.load();
            this.notification.add("Action effectuée", { type: "success" });
        } catch (e) {
            this.notification.add(e.message || "Erreur", { type: "danger" });
        }
    }

    async actionConfirm() { await this.doAction("action_confirm"); }
    async actionCheckin() { await this.doAction("action_checkin"); }
    async actionCheckout() { await this.doAction("action_checkout"); }
    async actionCancel() { await this.doAction("action_cancel"); }

    setReviewField(field, ev) {
        this.state.reviewForm[field] = ev.target.value;
    }
    setReviewNumber(field, ev) {
        this.state.reviewForm[field] = parseInt(ev.target.value) || 0;
    }

    async submitReview() {
        const f = this.state.reviewForm;
        try {
            await this.orm.create("civora.reservation.review", [{
                reservation_id: this.reservationId,
                rating: f.rating,
                cleanliness_rating: f.cleanliness_rating,
                location_rating: f.location_rating,
                comfort_rating: f.comfort_rating,
                value_rating: f.value_rating,
                comment: f.comment || false,
                internal_note: f.internal_note || false,
            }]);
            this.state.reviewForm = {
                rating: 5, cleanliness_rating: 5, location_rating: 5,
                comfort_rating: 5, value_rating: 5, comment: "", internal_note: "",
            };
            await this.load();
            this.notification.add("Avis enregistré", { type: "success" });
        } catch (e) {
            this.notification.add(e.message || "Erreur", { type: "danger" });
        }
    }

    async markCleaningDone(taskId) {
        await this.orm.call("civora.cleaning.task", "action_done", [[taskId]]);
        await this.load();
    }

    renderStars(rating) {
        return "★".repeat(rating) + "☆".repeat(5 - rating);
    }
}

registry.category("actions").add("civora.reservation_360", CivoraReservation360);
