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


class HrPayrollTemplate(models.Model):
    _name = "hr.payroll.template"
    _description = "Template de paie"

    name = fields.Char("Libellé", required=True)
    active = fields.Boolean(default=True,
            help="If the active field is set to false, it will allow you to hide the salary rule without removing it.")
    line_ids = fields.Many2many("hr.salary.rule_template", "structure_template_rule_reel", "template_id", "rule_id",
                                "Règles salariales")
    company_id = fields.Many2one('res.company', "Entité", default=lambda self: self.env.company)


class HrSalaryRuleTemplate(models.Model):
    _name = "hr.salary.rule_template"
    _description = "Salary Rules template"

    _order = 'sequence, id'
    _description = 'Salary Rule'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True,
                       help="The code of salary rules can be used as reference in computation of other rules. "
                            "In that case, it is case sensitive.")
    sequence = fields.Integer(required=True, index=True, default=5,
                              help='Use to arrange calculation sequence')
    template_id = fields.Many2one("hr.payroll.template", "Parent", required=False)
    quantity = fields.Char(default='1.0',
                           help="It is used in computation for percentage and fixed amount. "
                                "For e.g. A rule for Meal Voucher having fixed amount of "
                                u"1â‚¬ per worked day can have its quantity defined in expression "
                                "like worked_days.WORK100.number_of_days.")
    category_id = fields.Many2one('hr.salary.rule.category', string='Category', required=True)
    active = fields.Boolean(default=True,
                            help="If the active field is set to false, it will allow you to hide the salary rule without removing it.")
    appears_on_payslip = fields.Boolean(string='Appears on Payslip', default=True,
                                        help="Used to display the salary rule on payslip.")
    condition_select = fields.Selection([
        ('none', 'Always True'),
        ('range', 'Range'),
        ('python', 'Python Expression')
    ], string="Condition Based on", default='none', required=True)
    condition_range = fields.Char(string='Range Based on', default='contract.wage',
                                  help='This will be used to compute the % fields values; in general it is on basic, '
                                       'but you can also use categories code fields in lowercase as a variable names '
                                       '(hra, ma, lta, etc.) and the variable basic.')
    condition_python = fields.Text(string='Python Condition', required=True,
                                   default='''
                        # Available variables:
                        #----------------------
                        # payslip: object containing the payslips
                        # employee: hr.employee object
                        # contract: hr.contract object
                        # rules: object containing the rules code (previously computed)
                        # categories: object containing the computed salary rule categories (sum of amount of all rules belonging to that category).
                        # worked_days: object containing the computed worked days
                        # inputs: object containing the computed inputs.

                        # Note: returned value have to be set in the variable 'result'

                        result = rules.NET > categories.NET * 0.10''',
                                   help='Applied this rule for calculation if condition is true. You can specify condition like basic > 1000.')
    condition_range_min = fields.Float(string='Minimum Range', help="The minimum amount, applied for this rule.")
    condition_range_max = fields.Float(string='Maximum Range', help="The maximum amount, applied for this rule.")
    amount_select = fields.Selection([
        ('percentage', 'Percentage (%)'),
        ('fix', 'Fixed Amount'),
        ('code', 'Python Code'),
    ], string='Amount Type', index=True, required=True, default='fix',
        help="The computation method for the rule amount.")
    amount_fix = fields.Float(string='Fixed Amount', digits=(16, 2))
    amount_percentage = fields.Float(string='Percentage (%)', digits='Payroll Rate',
                                     help='For example, enter 50.0 to apply a percentage of 50%')
    amount_python_compute = fields.Text(string='Python Code',
                                        default='''
                        # Available variables:
                        #----------------------
                        # payslip: object containing the payslips
                        # employee: hr.employee object
                        # contract: hr.contract object
                        # rules: object containing the rules code (previously computed)
                        # categories: object containing the computed salary rule categories (sum of amount of all rules belonging to that category).
                        # worked_days: object containing the computed worked days.
                        # inputs: object containing the computed inputs.

                        # Note: returned value have to be set in the variable 'result'

                        result = contract.wage * 0.10''')
    amount_percentage_base = fields.Char(string='Percentage based on', help='result will be affected to a variable')
    partner_id = fields.Many2one('res.partner', string='Partner',
                                 help="Eventual third party involved in the salary payment of the employees.")
    note = fields.Text(string='Description')
