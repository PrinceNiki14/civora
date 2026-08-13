# -*- coding: utf-8 -*-
"""Échéancier mensuel d'un bail CIVORA.

Chaque enregistrement représente une échéance mensuelle : le mois X-année Y
pour le bail B est dû tel montant à telle date, et a été payé (ou non).

Généré automatiquement à la signature du contrat par les deux parties.
"""
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models

INSTALLMENT_STATE = [
    ('covered_by_advance', "Couvert par avance"),
    ('pending',            "En attente"),
    ('partial',            "Partiel"),
    ('paid',               "Payé"),
    ('overdue',            "En retard"),
]

MONTHS_FR = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
]


class CivoraLeaseInstallment(models.Model):
    _name = 'civora.lease.installment'
    _description = "Échéance mensuelle d'un bail CIVORA"
    _order = 'lease_id, sequence, period_year, period_month'
    _rec_name = 'period_label'

    lease_id = fields.Many2one(
        'civora.lease', string="Bail", required=True, ondelete='cascade', index=True,
    )
    company_id = fields.Many2one(
        related='lease_id.company_id', store=True, string="Société",
    )
    currency_id = fields.Many2one(
        related='lease_id.currency_id', store=True, string="Devise",
    )
    tenant_id = fields.Many2one(
        related='lease_id.tenant_id', store=True, string="Locataire",
    )
    property_id = fields.Many2one(
        related='lease_id.property_id', store=True, string="Bien",
    )

    sequence = fields.Integer(string="Séquence", default=0, index=True)
    period_month = fields.Integer(string="Mois", required=True)
    period_year = fields.Integer(string="Année", required=True)
    period_label = fields.Char(
        string="Période", compute='_compute_period_label', store=True,
    )
    due_date = fields.Date(string="Date d'échéance", required=True, index=True)

    amount_due = fields.Monetary(
        string="Montant dû", currency_field='currency_id', required=True,
    )
    amount_paid = fields.Monetary(
        string="Montant payé", currency_field='currency_id',
        compute='_compute_amount_paid', store=True,
    )
    amount_remaining = fields.Monetary(
        string="Reste à payer", currency_field='currency_id',
        compute='_compute_amount_paid', store=True,
    )

    state = fields.Selection(
        INSTALLMENT_STATE, string="État",
        compute='_compute_state', store=True, index=True,
    )

    payment_ids = fields.Many2many(
        'civora.lease.payment',
        'civora_lease_installment_payment_rel',
        'installment_id', 'payment_id',
        string="Paiements affectés",
    )
    note = fields.Char(string="Note")

    # ── Computed ────────────────────────────────────────────────────────
    @api.depends('period_month', 'period_year')
    def _compute_period_label(self):
        for inst in self:
            if inst.period_month and inst.period_year:
                m = MONTHS_FR[inst.period_month - 1] if 1 <= inst.period_month <= 12 else "?"
                inst.period_label = "%s %d" % (m, inst.period_year)
            else:
                inst.period_label = ""

    @api.depends('payment_ids.amount', 'payment_ids.status', 'amount_due')
    def _compute_amount_paid(self):
        for inst in self:
            total_paid = sum(
                p.amount for p in inst.payment_ids
                if p.status in ('paid', 'partial')
            )
            inst.amount_paid = total_paid
            inst.amount_remaining = max((inst.amount_due or 0.0) - total_paid, 0.0)

    @api.depends('amount_paid', 'amount_due', 'due_date', 'sequence', 'lease_id.advance_months')
    def _compute_state(self):
        today = fields.Date.context_today(self)
        for inst in self:
            # Couvert par l'avance : les N premiers mois (sequence < advance_months)
            advance = inst.lease_id.advance_months or 0
            if inst.sequence < advance:
                inst.state = 'covered_by_advance'
                continue
            paid = inst.amount_paid or 0.0
            due = inst.amount_due or 0.0
            if paid <= 0:
                # Rien payé : pending ou overdue selon date
                if inst.due_date and inst.due_date < today:
                    inst.state = 'overdue'
                else:
                    inst.state = 'pending'
            elif paid + 0.5 >= due:  # tolérance arrondi
                inst.state = 'paid'
            else:
                # Payé partiellement
                if inst.due_date and inst.due_date < today:
                    inst.state = 'overdue'
                else:
                    inst.state = 'partial'

    # ── Utils ───────────────────────────────────────────────────────────
    @api.model
    def _months_between(self, date_start, date_end):
        """Nombre de mois pleins entre deux dates (inclusif date_start)."""
        if not date_start or not date_end:
            return 0
        delta = relativedelta(date_end, date_start)
        return delta.years * 12 + delta.months + 1
