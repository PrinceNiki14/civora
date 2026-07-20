# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import format_amount, format_date
from itertools import groupby


class RapportCmu(models.TransientModel):
    _name = "hr.retenue.wizard"

    start_date = fields.Date("Date début", required=True)
    end_date = fields.Date("Date Fin", required=True)
    company_id = fields.Many2one("res.company", "Unité", default=lambda self: self.env.company.id, required=True)
    line_ids = fields.One2many("hr.retenue_wizard.line", "retenue_id")
    lot_id = fields.Many2one("hr.payslip.run", "Lot")
    salary_id = fields.Many2one("hr.salary.rule", "Retenue", domain=[('type_rule', '=', 'retenue')])

    @api.onchange("lot_id")
    @api.depends("lot_id")
    def onChangeLot(self):
        if self.lot_id:
            self.start_date = self.lot_id.date_start
            self.end_date = self.lot_id.date_end

    def _get_retenue_data(self):
        self.env['hr.retenue_wizard.line'].search([]).sudo().unlink()
        payslips = self.env["hr.payslip"].search([('date_from', '>=', self.start_date),
                                                  ('date_to', '<=', self.end_date),
                                                  ('payslip_run_id', '=', self.lot_id.id),
                                                  ('company_id', '=', self.company_id.id)])
        if payslips:
            print(payslips)
            emp_ids = payslips.mapped('employee_id')
            emp_data_list = []
            total_amount = 0
            for emp_id in emp_ids:
                line_ids = payslips.filtered(lambda x: x.employee_id.id == emp_id.id).mapped('line_ids')
                if line_ids:
                    data_dict = {
                        'employee_id': None,
                        'amount': 0,
                    }
                    amount = 0
                    for line in line_ids:
                        if line.code == self.salary_id.code:
                            amount += line.total
                    data_dict['amount'] = amount
                    data_dict['employee_id'] = emp_id.id
                    total_amount += amount
                    emp_data_list.append(data_dict)
            print(emp_data_list)
            self.line_ids = [(0, 0, d) for d in emp_data_list]
            return total_amount

    def _print_report(self, data):
        return self.env["ir.actions.report"].search([("report_name", "=", 'hr_retenue.report_hr_retenue')],
                                                    limit=1, ).report_action(self, data=data)

    def print_retenue_wizard(self):
        self.ensure_one()
        total_amount = self._get_retenue_data()
        data = {'ids': self.id,
                'form': self.read(['company_id', 'start_date', 'end_date'])[0],
                'model': 'hr.retenue.wizard',
                'total_amount': total_amount if total_amount else 0
                }
        return self._print_report(data)

    def export_xls(self):
        self.ensure_one()
        total_amount = self._get_retenue_data()
        data = {'ids': self.id,
                'form': self.read(['company_id', 'start_date', 'end_date'])[0],
                'model': 'hr.retenue.wizard',
                'total_amount': total_amount if total_amount else 0
                }
        return self.env.ref('hr_retenue.report_retenue_xlsx_id').with_context(data=data).report_action(self, data=data)


class RapportCmuLine(models.TransientModel):
    _name = "hr.retenue_wizard.line"

    employee_id = fields.Many2one("hr.employee", "Employé")
    amount = fields.Float()
    retenue_id = fields.Many2one("hr.retenue.wizard")
