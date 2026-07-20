# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import format_amount, format_date
from itertools import groupby


class RapportCmu(models.Model):
    _name = "hr.cmu.wizard"

    start_date = fields.Date("Date début", required=True)
    end_date = fields.Date("Date Fin", required=True)
    company_id = fields.Many2one("res.company", "Unité", default=lambda self: self.env.company.id, required=True)
    lot_id = fields.Many2one("hr.payslip.run", "Lot")
    line_ids = fields.One2many("hr.cmu_wizard.line", "hr_cmu_id")

    @api.onchange("lot_id")
    @api.depends("lot_id")
    def onChangeLot(self):
        if self.lot_id:
            self.start_date = self.lot_id.date_start
            self.end_date = self.lot_id.date_end

    def _get_cmu_data(self):
        for rec in self:
            rec.env['hr.cmu_wizard.line'].search([]).sudo().unlink()
            cmu_data_ids = self.env["hr.payslip"].search([('date_from', '>=', rec.start_date),
                                                          ('date_to', '<=', rec.end_date),
                                                          ('payslip_run_id', '=', self.lot_id.id),
                                                          ('company_id', '=', rec.company_id.id)]) if self.lot_id else \
                self.env["hr.payslip"].search([('date_from', '>=', rec.start_date),
                                               ('date_to', '<=', rec.end_date),
                                               ('company_id', '=', rec.company_id.id)])
            if cmu_data_ids:
                emp_ids = cmu_data_ids.mapped('employee_id')
                emp_data_list = []
                total_cmu_employe = 0
                total_cmu_employeur = 0
                for emp_id in emp_ids:
                    emp_id_list = cmu_data_ids.filtered(lambda x: x.employee_id.id == emp_id.id).mapped('line_ids')
                    # print(emp_id_list)
                    if emp_id_list:
                        data_dict = {
                            'employee_id': None,
                            'cmu_employe': 0,
                            'cmu_employeur': 0
                        }
                        cmu_employe = 0
                        cmu_employeur = 0
                        for line in emp_id_list:
                            if line.code == 'CMU':
                                cmu_employe += line.total
                            if line.code == 'CMU_P':
                                cmu_employeur += line.total
                        total_cmu_employe += cmu_employe
                        total_cmu_employeur += cmu_employeur
                        data_dict['cmu_employe'] = cmu_employe
                        data_dict['cmu_employeur'] = cmu_employeur
                        data_dict['employee_id'] = emp_id.id
                        emp_data_list.append(data_dict)
                print(emp_data_list)
                self.line_ids = [(0, 0, d) for d in emp_data_list]
                return {'total_cmu_employe': total_cmu_employe, 'total_cmu_employeur': total_cmu_employeur}

    def _print_report(self, data):
        return self.env["ir.actions.report"].search([("report_name", "=", 'hr_cmu.report_hr_cmu')],
                                                    limit=1, ).report_action(self, data=data)

    def print_cmu(self):
        self.ensure_one()
        cmu_data = self._get_cmu_data()
        data = {'ids': self.id,
                'form': self.read(['company_id', 'start_date', 'end_date'])[0],
                'model': 'hr.cmu.wizard',
                'total_cmu_employe': cmu_data['total_cmu_employe'],
                'total_cmu_employeur': cmu_data['total_cmu_employeur'],
                }
        return self._print_report(data)

    # def export_xls(self):
    #     self.ensure_one()
    #     self._get_cmu_data()
    #     datas = {'ids': self.ids,
    #              'model': self._name,
    #              'start_date': self.start_date,
    #              'end_date': self.end_date}
    #     return self.env.ref('hr_payroll_book.report_cmu_xlsx_id').with_context(data=datas).report_action(self,
    #                                                                                                      data=datas)


class RapportCmuLine(models.Model):
    _name = "hr.cmu_wizard.line"

    employee_id = fields.Many2one("hr.employee", "Employé")
    cmu_employe = fields.Integer("CMU employé")
    cmu_employeur = fields.Integer("CMU employeur")
    hr_cmu_id = fields.Many2one("hr.cmu.wizard")
