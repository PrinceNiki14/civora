# -*- coding: utf-8 -*-
from odoo import api, fields, models


CIVORA_CONSENT_CHANNEL = [
    ('email', "Email"),
    ('sms', "SMS"),
    ('whatsapp', "WhatsApp"),
]

CIVORA_CONSENT_VALUE = [
    ('opt_in', "Opt-in"),
    ('opt_out', "Opt-out"),
    ('none', "Non renseigné"),
]


class CivoraConsentLog(models.Model):
    """Journal audit des changements de consentement RGPD.

    Rempli automatiquement par le override write() de res.partner à chaque
    modification d'un des 3 consentements (email / SMS / WhatsApp).

    Utilisé pour :
    - Répondre à une demande d'accès RGPD (le contact veut savoir quand
      et comment il a donné son consentement)
    - Audit interne (qui a modifié le consentement de qui, quand)
    - Export DPO au format tableau
    """
    _name = 'civora.consent.log'
    _description = "Journal des consentements RGPD"
    _order = 'date desc, id desc'

    partner_id = fields.Many2one(
        'res.partner', string="Contact",
        required=True, ondelete='cascade', index=True,
    )
    channel = fields.Selection(
        CIVORA_CONSENT_CHANNEL, string="Canal",
        required=True, index=True,
    )
    old_value = fields.Selection(
        CIVORA_CONSENT_VALUE, string="Ancien",
        default='none',
    )
    new_value = fields.Selection(
        CIVORA_CONSENT_VALUE, string="Nouveau",
        required=True,
    )
    date = fields.Datetime(
        string="Date", required=True, default=fields.Datetime.now, index=True,
    )
    user_id = fields.Many2one(
        'res.users', string="Auteur",
        default=lambda self: self.env.user, required=True,
    )
    source = fields.Selection([
        ('manual', "Saisie manuelle"),
        ('import', "Import"),
        ('portal', "Portail (contact lui-même)"),
        ('api', "API"),
        ('system', "Système"),
    ], string="Source", default='manual', required=True)
    note = fields.Char(string="Note")
    company_id = fields.Many2one(
        'res.company', string="Société",
        related='partner_id.company_id', store=True, readonly=True,
    )
