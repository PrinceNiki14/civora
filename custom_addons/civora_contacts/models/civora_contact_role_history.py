# -*- coding: utf-8 -*-
from odoo import api, fields, models


CIVORA_ROLE_HISTORY_ACTION = [
    ('added',      "Rôle ajouté"),
    ('removed',    "Rôle retiré"),
    ('set_primary', "Rôle principal défini"),
    ('initial',    "État initial"),
]


class CivoraContactRoleHistory(models.Model):
    """Historique des transitions de rôles d'un contact CIVORA.

    Alimenté automatiquement par le override write() de res.partner.
    Sert de source pour :
    - la timeline Activité (via création miroir dans civora.interaction)
    - le calcul d'ancienneté / fidélité pour le score IA
    """
    _name = 'civora.contact.role.history'
    _description = "Historique des rôles d'un contact CIVORA"
    _order = 'date desc, id desc'

    partner_id = fields.Many2one(
        'res.partner', string="Contact",
        required=True, ondelete='cascade', index=True,
    )
    role_id = fields.Many2one(
        'civora.contact.role', string="Rôle",
        required=True, ondelete='restrict', index=True,
    )
    action = fields.Selection(
        CIVORA_ROLE_HISTORY_ACTION, string="Action",
        required=True, default='added',
    )
    date = fields.Datetime(
        string="Date", required=True, default=fields.Datetime.now, index=True,
    )
    user_id = fields.Many2one(
        'res.users', string="Auteur",
        default=lambda self: self.env.user, required=True,
    )
    note = fields.Char(string="Note")
    company_id = fields.Many2one(
        'res.company', string="Société",
        related='partner_id.company_id', store=True, readonly=True,
    )
