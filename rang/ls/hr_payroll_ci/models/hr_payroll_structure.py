# -*- encoding: utf-8 -*-

##############################################################################
#
# Copyright (c) 2020 KERYATEC - support@keryatec.com
# Author: KERYATEC
#
# Fichier du module hr_payroll_ci
# ##############################################################################  -->


import time
from datetime import date
from datetime import datetime, time
from datetime import timedelta
from dateutil import relativedelta
from odoo import fields, osv, api, models
from odoo import tools
from odoo.tools.translate import _
from odoo.exceptions import UserError, ValidationError
from collections import namedtuple

import babel


# class HrSalaryRule(models.Model):
#     _inherit = "hr.salary.rule"
#
#     company_id = fields.Many2one('res.company', 'Société', related="struct_id.company_id", store=True)
#     company_id = fields.Many2one('res.company', "Entité", default=lambda self: self.env.company)


class HrPayrollStructure(models.Model):
    _inherit = "hr.payroll.structure"

    def updateRules(self):
        rules = self._get_default_rule_ids()
        print(rules)
        if rules:
            for struct in self:
                struct.rule_ids.unlink()
                struct.rule_ids = rules

    @api.model
    def _get_default_rule_ids(self):
        tempate = self.env['hr.payroll.template'].search([('active', '=', True)], limit=1)
        print(tempate)
        rules = []
        if tempate and tempate.line_ids:
            for rule in tempate.line_ids:
                val = {
                    'name': rule.name,
                    'code': rule.code,
                    'sequence': rule.sequence,
                    'appears_on_payslip': rule.appears_on_payslip,
                    'category_id': rule.category_id.id,
                    'condition_select': rule.condition_select,
                    'condition_python': rule.condition_python,
                    'amount_select': rule.amount_select,
                    'amount_python_compute': rule.amount_python_compute,
                    'amount_percentage_base': rule.amount_percentage_base,
                    'quantity': rule.quantity,
                    'amount_percentage': rule.amount_percentage,
                    'amount_fix': rule.amount_fix
                }
                rules.append((0, 0, val))
        return rules

    rule_ids = fields.One2many(
        'hr.salary.rule', 'struct_id',
        string='Salary Rules', default=_get_default_rule_ids)


    company_id = fields.Many2one("res.company", "Sosiété", default=lambda self: self.env.company)
    number_hours = fields.Float()
