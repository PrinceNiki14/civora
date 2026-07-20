# -*- encoding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    rule_ids = fields.Many2many(
        'hr.salary.rule',
        'payroll_rule_real',
        'company_id',
        'rule_id',
        domain="[('appears_on_payroll', '=', True)]"
    )
