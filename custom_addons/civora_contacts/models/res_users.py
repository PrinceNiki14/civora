# -*- coding: utf-8 -*-
from odoo import fields, models


class ResUsers(models.Model):
    """Extension res.users : fonction CIVORA de l'agent."""
    _inherit = 'res.users'

    civora_function_id = fields.Many2one(
        'civora.agent.role',
        string="Fonction CIVORA",
        help="Fonction de l'agent (agent immobilier, negociateur, gestionnaire...).",
    )
