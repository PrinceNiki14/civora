# -*- encoding: utf-8 -*-

from odoo import fields, models


class HrPayslipSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'
    _order = 'sequence'

    type_rule = fields.Selection([('normal', 'Normal'), ('impot', 'Impôt'), ('cotisation', 'Cotisation'),
               ('assurance', 'Assurance')], default='normal', string='Type de règle')
