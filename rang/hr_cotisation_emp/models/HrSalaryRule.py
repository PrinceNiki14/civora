# -*- encoding: utf-8 -*-

##############################################################################
#
# Copyright (c) 2015 - KERYATEC - jonathan.arra@KERYATEC.com
# Author: Jean Jonathan ARRA
#
# Fichier du module HR_CONTRIBUTION_SUMMARY
# ##############################################################################


from odoo import fields, models


class HrPayslipSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    company_id = fields.Many2one("res.company", "Unité", default=lambda self: self.env.company.id, required=True)
    type_cotisation = fields.Boolean("Cotisation employé/Employeur")
    linked_to = fields.Many2one("hr.salary.rule", "Rubrique lié à")

