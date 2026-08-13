# -*- coding: utf-8 -*-
from markupsafe import Markup

from odoo import api, fields, models

CIVORA_PAYMENT_METHOD = [
    ('virement', "Virement bancaire"),
    ('wave', "Wave"),
    ('orange_money', "Orange Money"),
    ('mtn_momo', "MTN MoMo"),
    ('cheque', "Chèque"),
    ('especes', "Espèces"),
    ('autre', "Autre"),
]
CIVORA_PAYMENT_STATUS = [
    ('paid', "Encaissé"),
    ('partial', "Partiel"),
    ('pending', "En attente"),
    ('cancelled', "Annulé"),
]
CIVORA_PAYMENT_SOURCE = [
    ('manual', "Saisie manuelle"),
    ('online', "Paiement en ligne"),
]
CIVORA_PAYMENT_TYPE = [
    ('rent',    "Loyer mensuel"),
    ('advance', "Loyer d'avance"),
    ('caution', "Caution / dépôt de garantie"),
    ('agency',  "Frais d'agence"),
    ('other',   "Autre"),
]


class CivoraLeasePayment(models.Model):
    """Encaissement de loyer / charges rattache a un bail."""
    _name = 'civora.lease.payment'
    _description = "Encaissement de loyer CIVORA"
    _order = 'date desc, id desc'
    _rec_name = 'lease_id'

    lease_id = fields.Many2one(
        'civora.lease', string="Bail", required=True, ondelete='cascade', index=True,
    )
    date = fields.Date(string="Date", required=True, default=fields.Date.context_today)
    amount = fields.Monetary(string="Montant", currency_field='currency_id', required=True)
    currency_id = fields.Many2one(
        related='lease_id.currency_id', string="Devise", store=True, readonly=True,
    )
    method = fields.Selection(CIVORA_PAYMENT_METHOD, string="Mode de paiement", default='virement')
    status = fields.Selection(
        CIVORA_PAYMENT_STATUS, string="Statut", default='paid', required=True,
    )
    payment_type = fields.Selection(
        CIVORA_PAYMENT_TYPE, string="Type de versement",
        default='rent', required=True,
        help="Nature du versement : loyer mensuel, mois d'avance, caution, "
             "frais d'agence ou autre.",
    )
    source = fields.Selection(
        CIVORA_PAYMENT_SOURCE, string="Origine", default='manual', required=True,
        help="Saisie manuelle par un agent (preuve de paiement) ou paiement en ligne "
             "recu automatiquement depuis le site web CIVORA (a venir).",
    )
    reference = fields.Char(string="Référence", help="Référence de transaction ou de dépôt.")
    note = fields.Char(string="Note")
    company_id = fields.Many2one(
        related='lease_id.company_id', string="Société", store=True, index=True, readonly=True,
    )
    installment_ids = fields.Many2many(
        'civora.lease.installment',
        'civora_lease_installment_payment_rel',
        'payment_id', 'installment_id',
        string="Mois couverts",
        help="Mois de l'échéancier couverts par ce paiement. "
             "Imputation automatique par défaut sur le mois impayé le plus ancien.",
    )

    _amount_positive = models.Constraint(
        'check (amount >= 0)',
        "Le montant ne peut pas être négatif.",
    )

    # ═══════════════════════════════════════════════════════════════════
    # Imputation automatique sur l'échéancier
    # ═══════════════════════════════════════════════════════════════════
    @api.model_create_multi
    def create(self, vals_list):
        payments = super().create(vals_list)
        for payment in payments:
            if payment.payment_type == 'rent' and payment.status in ('paid', 'partial'):
                payment._auto_impute_installments()
        return payments

    def write(self, vals):
        res = super().write(vals)
        # Réimputer si le type/statut/montant change
        if any(k in vals for k in ('payment_type', 'status', 'amount', 'lease_id')):
            for payment in self:
                if payment.payment_type == 'rent' and payment.status in ('paid', 'partial'):
                    payment._auto_impute_installments()
        return res

    def _auto_impute_installments(self):
        """Impute automatiquement ce paiement sur les échéances impayées
        les plus anciennes du bail.

        Règle :
        - N'impacte que les paiements de type 'rent'
        - Ne remplace pas une imputation manuelle déjà présente
        - Consomme les échéances 'pending', 'partial', 'overdue' par ordre chronologique
        - Le trop-plein déborde sur le mois suivant
        """
        self.ensure_one()
        # Skip si imputation manuelle déjà en place
        if self.installment_ids:
            return
        if not self.lease_id or self.payment_type != 'rent':
            return
        remaining = self.amount or 0.0
        if remaining <= 0:
            return
        # Chercher les échéances à combler : pending, partial, overdue
        installments = self.env['civora.lease.installment'].search([
            ('lease_id', '=', self.lease_id.id),
            ('state', 'in', ('pending', 'partial', 'overdue')),
        ], order='sequence asc')
        to_link = []
        for inst in installments:
            if remaining <= 0.01:
                break
            reste = inst.amount_remaining
            if reste <= 0:
                continue
            to_link.append(inst.id)
            remaining -= min(remaining, reste)
        if to_link:
            self.installment_ids = [(6, 0, to_link)]

    def action_reimpute(self):
        """Force une réimputation manuelle du paiement.

        Vide les imputations existantes et relance l'auto-imputation.
        """
        self.ensure_one()
        self.installment_ids = [(5, 0, 0)]
        self._auto_impute_installments()
        return True

    def action_cancel_payment(self, reason=None):
        """Annule un paiement (cas d'erreur de saisie).

        - Passe le statut à 'cancelled'
        - Détache toutes les échéances imputées (elles redeviennent impayées)
        - Log un chatter sur le bail

        Le paiement reste visible en base pour audit (pas de suppression).
        """
        self.ensure_one()
        if self.status == 'cancelled':
            from odoo.exceptions import UserError
            raise UserError("Ce paiement est déjà annulé.")
        old_status = self.status
        old_amount = self.amount
        self.installment_ids = [(5, 0, 0)]
        self.status = 'cancelled'
        # Chatter sur le bail
        if self.lease_id:
            body = Markup(
                "<b>⚠ Paiement annulé</b><br/>"
                "Date : %s<br/>"
                "Montant : %s %s<br/>"
                "Statut précédent : %s"
            ) % (
                self.date, old_amount,
                self.currency_id.name or "",
                dict(self._fields['status'].selection).get(old_status),
            )
            if reason:
                body += Markup("<br/>Motif : %s") % reason
            self.lease_id.message_post(
                body=body,
                subtype_xmlid='mail.mt_note',
            )
        return True
