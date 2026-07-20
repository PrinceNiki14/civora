# -*- encoding: utf-8 -*-

##############################################################################
#
# Copyright (c) 2015 - SIIGCI - jonathan.arra@gmail.com
# Author: Jean Jonathan ARRA
#
# Fichier du module hr_payroll_ci_raport
# ##############################################################################



from odoo import fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    rule_ids = fields.Many2many('hr.salary.rule', 'payroll_rule_real', 'company_id', 'rule_id',
                                domain="[('appears_on_payroll', '=', True)]")
