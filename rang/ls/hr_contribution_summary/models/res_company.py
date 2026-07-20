# -*- encoding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    contribution_summary_ids = fields.Many2many('hr.contribution.company', string="Résumé des contributions",
                                                required=False)
