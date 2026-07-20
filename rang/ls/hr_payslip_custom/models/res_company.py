# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    signatory_id = fields.Many2one('hr.employee', string='Signataire', help="Signataire des bulletins de salaire")
    stamp = fields.Binary(string='Cachet', help="Cachet du signataire qui devra apparaitre sur les bulletins de salaire")
