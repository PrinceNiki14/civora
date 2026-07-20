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
            emprunt = self.env['hr.emprunt.loaning'].search([('state', '=', 'confirmed'), ('employee_id', '=', self.employee_id.id)])
            if emprunt:
                for emp in emprunt:
                    echeance_ids = emp.mapped('echeance_ids')
                    type_pret_id = emp.mapped('type_pret_id')
                    montant = 0
                    for line in echeance_ids:
                        if date_from2 <= line.date_prevu <= date_to:
                            montant += line.montant
                    type_line = self.env['hr.payslip.input.type'].search([('code', '=', type_pret_id.code)], limit=1)
                    val = {
                        'input_type_id': type_line.id,
                        'amount': montant,
                        'contract_id': self.id,
                    }
                    res.append(val)
            return res
