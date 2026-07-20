# -*- coding: utf-8 -*-
import time
import babel
from odoo import models, fields, api, tools, _
from datetime import datetime
from odoo.tools.misc import format_date


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    @api.depends('employee_id', 'struct_id', 'date_from')
    def _compute_name(self):
        for slip in self.filtered(lambda p: p.employee_id and p.date_from):
            slip._input_lines(slip.contract_id, slip.struct_id)
            lang = slip.employee_id.sudo().address_home_id.lang or self.env.user.lang
            context = {'lang': lang}
            payslip_name = slip.struct_id.payslip_name or _('Salary Slip')
            del context

            slip.name = '%(payslip_name)s - %(employee_name)s - %(dates)s' % {
                'payslip_name': payslip_name,
                'employee_name': slip.employee_id.name,
                'dates': format_date(self.env, slip.date_from, date_format="MMMM y", lang_code=lang)
            }

    @api.depends('employee_id', 'date_from')
    def _input_lines(self, contract_id, struct_id):
        input_lines = self.input_line_ids.browse([])
        if contract_id and struct_id:
            data_inputs = contract_id.get_inputs_payslip()
            emprunt = self.env['hr.emprunt.loaning'].search([('state', '=', 'confirmed'),('employee_id', '=', self.employee_id.id)])
            if emprunt:
                for emp in emprunt:
                    echeance_ids = emp.mapped('echeance_ids')
                    type_pret_id = emp.mapped('type_pret_id')
                    montant = 0
                    for line in echeance_ids:
                        if self.date_from <= line.date_prevu <= self.date_to:
                            montant += line.montant
                    if type_pret_id:
                        type_line = self.env['hr.payslip.input.type'].search([('code', '=', type_pret_id.code)], limit=1)
                        val = {
                            'input_type_id': type_line.id,
                            'amount': montant,
                            'contract_id': contract_id.id,
                        }
                        data_inputs.append(val)
            for r in data_inputs:
                input_lines |= input_lines.new(r)
            if struct_id.input_line_type_ids:
                intups_data = []
                for type in struct_id.input_line_type_ids:
                    val = {
                        'input_type_id': type.id,
                        'amount': 0,
                        'contract_id': contract_id.id,
                        #'struct_id': struct_id.id
                    }
                    intups_data.append(val)
                for r in intups_data:
                    input_lines |= input_lines.new(r)
            return input_lines
        else:
            return [(5, False, False)]

