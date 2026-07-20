# -*- coding: utf-8 -*-
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
]
# 'manual' = saisie par un agent pour prouver un paiement recu hors ligne.
# 'online' = reserve pour le futur portail de paiement (webhook site web CIVORA).
CIVORA_PAYMENT_SOURCE = [
    ('manual', "Saisie manuelle"),
    ('online', "Paiement en ligne"),
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

    _amount_positive = models.Constraint(
        'check (amount >= 0)',
        "Le montant ne peut pas être négatif.",
    )
