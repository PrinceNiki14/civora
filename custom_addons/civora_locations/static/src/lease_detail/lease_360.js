import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { CivoraStatCard } from "@civora_core/components/civora_stat_card";
import { CivoraAvatar, CivoraBadge, CivoraProgress } from "@civora_core/components/civora_kit";
import { LeaseDrawer } from "@civora_locations/leases/lease_drawer";
import { ContractTab } from "@civora_locations/contracts/contract_tab";
import { InstallmentSchedule } from "@civora_locations/installments/installment_schedule";
import { FinanceOverview } from "@civora_locations/finance/finance_overview";
import { PaymentMethodStats } from "@civora_locations/finance/payment_method_stats";
import { InitialPaymentWizard } from "@civora_locations/finance/initial_payment_wizard";
import { DepositRefund } from "@civora_locations/finance/deposit_refund";
import { LeaseTimeline } from "@civora_locations/timeline/lease_timeline";
import { IncidentsTab } from "@civora_locations/incidents/incidents_tab";

const STATUS_META = {
    actif: { label: "Actif", variant: "success" },
    retard: { label: "Retard", variant: "danger" },
    expire_bientot: { label: "Expire bientôt", variant: "warning" },
    resilie: { label: "Résilié", variant: "neutral" },
};
const TYPE_LABEL = { residentiel: "Résidentiel", commercial: "Commercial" };
const PAY_METHOD_LABEL = {
    virement: "Virement bancaire", wave: "Wave", orange_money: "Orange Money",
    mtn_momo: "MTN MoMo", cheque: "Chèque", especes: "Espèces", autre: "Autre",
};
const PAY_STATUS_META = {
    paid: { label: "Encaissé", variant: "success" },
    partial: { label: "Partiel", variant: "warning" },
    pending: { label: "En attente", variant: "neutral" },
};
const LEASE_FIELDS = [
    "name", "property_id", "tenant_id", "owner_id", "agent_id", "opportunity_id",
    "rent", "charges", "deposit",
    "date_start", "date_end", "payday", "lease_type", "state", "status",
    "payment_rate", "total_monthly", "total_paid", "total_expected", "arrears_amount",
    "indexation", "notice_tenant", "notice_owner", "note",
    "installment_overdue_count",
];
const PAYMENT_FIELDS = ["date", "amount", "method", "status", "source", "reference", "note", "payment_type"];

const PAYMENT_TYPE_LABELS = {
    rent:    "Loyer mensuel",
    advance: "Loyer d'avance",
    caution: "Caution",
    agency:  "Frais d'agence",
    other:   "Autre",
};

const METHOD_LABELS = {
    virement: "Virement",
    wave: "Wave",
    orange_money: "Orange Money",
    mtn_momo: "MTN MoMo",
    cheque: "Chèque",
    especes: "Espèces",
    autre: "Autre",
};

function emptyPaymentForm(lease) {
    return {
        date: new Date().toISOString().slice(0, 10),
        amount: lease ? (lease.rent || 0) + (lease.charges || 0) : 0,
        method: "virement",
        status: "paid",
        payment_type: "rent",
        reference: "",
        note: "",
    };
}

export class CivoraLease360 extends Component {
    static template = "civora_locations.Lease360";
    static components = { CivoraStatCard, CivoraAvatar, CivoraBadge, CivoraProgress, LeaseDrawer, ContractTab, InstallmentSchedule, FinanceOverview, PaymentMethodStats, InitialPaymentWizard, DepositRefund, LeaseTimeline, IncidentsTab };
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        const params = (this.props.action && this.props.action.params) || {};
        this.leaseId = Number(params.leaseId) || false;
        this.origin = params.origin || null;

        this.state = useState({
            loading: true,
            error: "",
            lease: null,
            payments: [],
            receipts: [],
            activeTab: "overview",
            showPaymentForm: false,
            showInitialWizard: false,
            showDepositRefund: false,
            pendingCancelId: null,
            collapsed: {
                initial: true,   // par défaut replié
                rent: true,      // par défaut replié
            },
            savingPayment: false,
            paymentForm: emptyPaymentForm(null),
            drawerOpen: false,
            showReceiptForm: false,
            generatingReceipt: false,
            receiptForm: { month: new Date().getMonth() + 1, year: new Date().getFullYear() },
        });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        if (!this.leaseId) {
            this.state.error = "Bail introuvable.";
            this.state.loading = false;
            return;
        }
        try {
            const [rec] = await this.orm.read("civora.lease", [this.leaseId], LEASE_FIELDS);
            if (!rec) {
                this.state.error = "Bail introuvable.";
                this.state.loading = false;
                return;
            }
            this.state.lease = rec;
            this.state.payments = await this.orm.searchRead(
                "civora.lease.payment", [["lease_id", "=", this.leaseId]], PAYMENT_FIELDS,
                { order: "date desc, id desc" }
            );
            this.state.receipts = await this.orm.searchRead(
                "civora.lease.receipt", [["lease_id", "=", this.leaseId]],
                ["name", "period_label", "amount_total", "date_issued", "date_paid", "payment_id"],
                { order: "period_year desc, period_month desc, id desc" }
            );
        } catch (e) {
            this.state.error = "Impossible de charger le bail.";
        }
        this.state.loading = false;
    }

    goBack() {
        if (this.origin && this.origin.tag) {
            this.action.doAction({ type: "ir.actions.client", tag: this.origin.tag, params: this.origin.params, target: "current" });
        } else {
            this.action.doAction({ type: "ir.actions.client", tag: "civora.leases", target: "current" });
        }
    }
    get backLabel() {
        return (this.origin && this.origin.label) || "Locations";
    }
    setTab(id) {
        this.state.activeTab = id;
    }
    openProperty() {
        const l = this.lease;
        if (!l.property_id) return;
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.property_360",
            params: {
                propertyId: l.property_id[0],
                origin: { tag: "civora.lease_360", params: { leaseId: this.leaseId }, label: "Bail" },
            },
            target: "current",
        });
    }
    openTenant() {
        const l = this.lease;
        if (!l.tenant_id) return;
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.contact_360",
            params: {
                contactId: l.tenant_id[0],
                origin: { tag: "civora.lease_360", params: { leaseId: this.leaseId }, label: "Bail" },
            },
            target: "current",
        });
    }

    // --- Drawer edition ------------------------------------------------
    openEditDrawer() {
        this.state.drawerOpen = true;
    }
    closeDrawer() {
        this.state.drawerOpen = false;
    }
    async onDrawerSaved(id) {
        this.state.drawerOpen = false;
        if (id === false) {
            // Suppression du bail depuis le drawer : on revient a la liste.
            this.goBack();
            return;
        }
        await this.load();
    }

    // --- Paiements (saisie manuelle) ------------------------------------
    toggleAddPayment() {
        this.state.paymentForm = emptyPaymentForm(this.lease);
        this.state.showPaymentForm = !this.state.showPaymentForm;
        this.state.showInitialWizard = false;
    }

    openInitialWizard() {
        this.state.showInitialWizard = true;
        this.state.showPaymentForm = false;
    }
    closeInitialWizard() {
        this.state.showInitialWizard = false;
    }
    async onInitialWizardSaved() {
        this.state.showInitialWizard = false;
        await this.load();
    }

    openDepositRefund() {
        this.state.showDepositRefund = true;
    }
    closeDepositRefund() {
        this.state.showDepositRefund = false;
    }
    async onDepositRefundSaved() {
        this.state.showDepositRefund = false;
        await this.load();
    }

    async cancelPayment(paymentId) {
        // Confirmation en 2 clics
        const p = (this.state.payments || []).find(x => x.id === paymentId);
        if (!p) return;
        if (this.state.pendingCancelId === paymentId) {
            try {
                await this.orm.call(
                    "civora.lease.payment",
                    "action_cancel_payment",
                    [[paymentId]]
                );
                this.notification.add("Paiement annulé.", { type: "success" });
                this.state.pendingCancelId = null;
                await this.load();
            } catch (e) {
                this.notification.add("Erreur : " + (e.message || e), { type: "danger" });
            }
        } else {
            this.state.pendingCancelId = paymentId;
            this.notification.add(
                "Cliquez à nouveau sur Annuler pour confirmer.",
                { type: "warning" }
            );
            // Auto-reset après 5s
            setTimeout(() => {
                if (this.state.pendingCancelId === paymentId) {
                    this.state.pendingCancelId = null;
                }
            }, 5000);
        }
    }

    toggleCollapse(section) {
        this.state.collapsed[section] = !this.state.collapsed[section];
    }

    setPaymentField(field, value) {
        this.state.paymentForm[field] = value;
    }
    onPaymentInput(field, ev) {
        this.setPaymentField(field, ev.target.value);
    }
    async savePayment() {
        const f = this.state.paymentForm;
        if (!f.date || !f.amount) return;
        this.state.savingPayment = true;
        try {
            await this.orm.create("civora.lease.payment", [{
                lease_id: this.leaseId,
                date: f.date,
                amount: Number(f.amount) || 0,
                method: f.method,
                status: f.status,
                payment_type: f.payment_type || "rent",
                source: "manual",
                reference: f.reference || false,
                note: f.note || false,
            }]);
            this.state.showPaymentForm = false;
            await this.load();
        } catch (e) {
            this.state.error = "Impossible d'enregistrer le paiement.";
        }
        this.state.savingPayment = false;
    }

    // --- Getters / helpers ------------------------------------------------
    get lease() {
        return this.state.lease || {};
    }
    get propertyLabel() {
        return this.lease.property_id ? this.lease.property_id[1] : "—";
    }
    get tenantLabel() {
        return this.lease.tenant_id ? this.lease.tenant_id[1] : "—";
    }
    get ownerLabel() {
        return this.lease.owner_id ? this.lease.owner_id[1] : "—";
    }
    get agentLabel() {
        return this.lease.agent_id ? this.lease.agent_id[1] : "—";
    }
    get opportunityLabel() {
        return this.lease.opportunity_id ? this.lease.opportunity_id[1] : "";
    }
    get hasOpportunity() {
        return !!(this.lease.opportunity_id);
    }
    openOpportunity() {
        if (!this.lease.opportunity_id) return;
        this.action.doAction({
            type: "ir.actions.client",
            tag: "civora.opportunity_360",
            params: { opportunityId: this.lease.opportunity_id[0] },
            target: "current",
        });
    }
    get statusInfo() {
        return STATUS_META[this.lease.status] || { label: "—", variant: "neutral" };
    }
    get typeLabel() {
        return TYPE_LABEL[this.lease.lease_type] || "—";
    }
    payMethodLabel(m) {
        return PAY_METHOD_LABEL[m] || m || "—";
    }
    payStatusMeta(s) {
        return PAY_STATUS_META[s] || { label: "—", variant: "neutral" };
    }
    paymentTypeLabel(t) {
        return PAYMENT_TYPE_LABELS[t] || t || "—";
    }
    isInitialType(t) {
        return t === "advance" || t === "caution" || t === "agency";
    }
    get initialPayments() {
        return (this.state.payments || []).filter(p => this.isInitialType(p.payment_type));
    }
    get rentPayments() {
        return (this.state.payments || []).filter(p => !this.isInitialType(p.payment_type));
    }
    get hasInitialPayments() {
        return this.initialPayments.length > 0;
    }
    get initialPaymentsTotal() {
        return this.initialPayments
            .filter(p => p.status !== 'cancelled')
            .reduce((s, p) => s + (p.amount || 0), 0);
    }
    get rentPaymentsTotal() {
        return this.rentPayments
            .filter(p => p.status !== 'cancelled')
            .reduce((s, p) => s + (p.amount || 0), 0);
    }
    fmtMoney(v) {
        const n = Number(v) || 0;
        return n.toLocaleString("fr-FR").replace(/,/g, " ") + " FCFA";
    }
    orDash(v) {
        return v || "—";
    }
    fmtDate(d) {
        if (!d) return "—";
        const [y, m, day] = String(d).split("-");
        return day && m && y ? `${day}/${m}/${y}` : d;
    }
    fmtMoney(n) {
        n = Number(n || 0);
        if (n >= 1e9) return (n / 1e9).toFixed(1).replace(".", ",") + " Md";
        if (n >= 1e6) return (n / 1e6).toFixed(n % 1e6 ? 1 : 0).replace(".", ",") + " M";
        if (n >= 1e3) return Math.round(n / 1e3) + " k";
        return "" + n;
    }
    kpiMoney(n) {
        return this.fmtMoney(n) + " FCFA";
    }
    get tabList() {
        return [
            { id: "overview", label: "Vue d'ensemble" },
            { id: "payments", label: "Paiements", count: this.state.payments.length },
            { id: "receipts", label: "Quittances", count: this.state.receipts.length },
            { id: "contrat", label: "Contrat" },
            { id: "incidents", label: "Incidents & Relances",
              count: this.lease && this.lease.installment_overdue_count ? this.lease.installment_overdue_count : 0 },
            { id: "history", label: "Historique" },
        ];
    }

    // --- Quittances ----------------------------------------------------
    async printReceipt(receiptId) {
        await this.action.doAction({
            type: "ir.actions.report",
            report_name: "civora_locations.report_lease_receipt",
            report_type: "qweb-pdf",
            context: { active_ids: [receiptId], active_model: "civora.lease.receipt" },
        });
    }
    async generateFromPayment(paymentId) {
        try {
            const rid = await this.orm.call("civora.lease.receipt", "create_from_payment", [paymentId]);
            await this.load();
            this.state.activeTab = "receipts";
            await this.printReceipt(rid);
        } catch (e) {
            this.state.error = "Impossible de générer la quittance.";
        }
    }
    toggleReceiptForm() {
        this.state.receiptForm = { month: new Date().getMonth() + 1, year: new Date().getFullYear() };
        this.state.showReceiptForm = !this.state.showReceiptForm;
    }
    setReceiptField(field, ev) {
        this.state.receiptForm[field] = ev.target.value === "" ? 0 : Number(ev.target.value);
    }
    async generateForPeriod() {
        const f = this.state.receiptForm;
        if (!f.month || !f.year) return;
        this.state.generatingReceipt = true;
        try {
            const rid = await this.orm.call(
                "civora.lease.receipt", "create_for_period", [this.leaseId, f.month, f.year]
            );
            this.state.showReceiptForm = false;
            await this.load();
            await this.printReceipt(rid);
        } catch (e) {
            this.state.error = "Impossible de générer la quittance.";
        }
        this.state.generatingReceipt = false;
    }
    receiptMonthLabel(m) {
        const names = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
            "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"];
        return names[m] || "";
    }
    get monthOptions() {
        return [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map((m) => ({ value: m, label: this.receiptMonthLabel(m) }));
    }
}

registry.category("actions").add("civora.lease_360", CivoraLease360);
