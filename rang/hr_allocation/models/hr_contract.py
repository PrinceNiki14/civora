# -*- coding: utf-8 -*-
import time
import babel
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, tools, _
from datetime import datetime, date


class HrContract(models.Model):
    _inherit = 'hr.contract'

    def get_inputs_payslip(self):
        res = super(HrContract, self).get_inputs_payslip()
        if self.employee_id:
            date_from = fields.Date.to_string(date.today().replace(day=1))
            next_month = relativedelta(months=+1, day=1, days=-1)
            date_from2 = fields.Date.from_string(date_from)
            date_to = date_from2 + next_month
            historique = self.env['historique.retour_conge'].search([
                ('employee_id', '=', self.employee_id.id),
                ('payroll_date', '>=', date_from2),
                ('payroll_date', '<=', date_to)
            ])
            if historique:
                montant = 0
                for hist in historique:
                    #montant += hist.allocation_conge
                    montant += hist.smj
                type_line = self.env['hr.payslip.input.type'].search([('code', '=', 'CONG')], limit=1)
                if montant:
                    val = {
                        'input_type_id': type_line.id,
                        'amount': montant,
                        'contract_id': self.id,
                    }
                    res.append(val)
            return res
