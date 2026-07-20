# -*- coding:utf-8 -*-

from odoo import api, models, fields


class HrPyalipLine(models.Model):
    _inherit = "hr.payslip.line"

    appears_on_payroll = fields.Boolean(related='salary_rule_id.appears_on_payroll', readonly=True, store=True)
    date_from = fields.Date(string='From', related="slip_id.date_from", store=True)
    date_to = fields.Date(string='To', related="slip_id.date_to", store=True)
    company_id = fields.Many2one("res.company", related="slip_id.company_id", store=True)


class HrPayslip(models.Model):
    _inherit = "hr.payslip"