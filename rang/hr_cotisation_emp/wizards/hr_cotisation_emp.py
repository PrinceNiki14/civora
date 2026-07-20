# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import format_amount, format_date
from itertools import groupby


class RapportITS(models.Model):
    _name = "hr.cotisation.emp"

    start_date = fields.Date("Date début", required=True)
    end_date = fields.Date("Date Fin", required=True)
    company_id = fields.Many2one("res.company", "Unité", default=lambda self: self.env.company.id, required=True)
    lot_id = fields.Many2one("hr.payslip.run", "Lot")
    line_ids = fields.One2many("hr.cotisation_emp.line", "cotisation_emp_id")
    salary_id = fields.Many2one("hr.salary.rule", "Rubrique", domain=[('type_cotisation', '=', True)])

    @api.onchange("lot_id")
    @api.depends("lot_id")
    def onChangeLot(self):
        if self.lot_id:
            self.start_date = self.lot_id.date_start
            self.end_date = self.lot_id.date_end

    def _get_cotisation_emp_data(self):
        for rec in self:
            rec.env['hr.cotisation_emp.line'].search([]).sudo().unlink()
            cotisation_emp_data_ids = self.env["hr.payslip"].search([('date_from', '>=', rec.start_date),
                                                          ('date_to', '<=', rec.end_date),
                                                          ('payslip_run_id', '=', self.lot_id.id),
                                                          ('company_id', '=', rec.company_id.id)])
            if cotisation_emp_data_ids:
                emp_ids = cotisation_emp_data_ids.mapped('employee_id')
                emp_data_list = []
                total_cotisation_employe = 0
                total_cotisation_employeur = 0
                for emp_id in emp_ids:
                    emp_id_list = cotisation_emp_data_ids.filtered(lambda x: x.employee_id.id == emp_id.id).mapped('line_ids')
                    if emp_id_list:
                        data_dict = {
                            'employee_id': None,
                            'cotisation_employe': 0,
                            'cotisation_employeur': 0
                        }
                        cotisation_employe = 0
                        cotisation_employeur = 0
                        rule_code = self.env["hr.salary.rule"].search([('linked_to', '=', self.salary_id.id)]).code
                        for line in emp_id_list:
                            if line.code == self.salary_id.code:
                                cotisation_employe += line.total
                            if line.code == rule_code:
                                cotisation_employeur += line.total
                        total_cotisation_employe += cotisation_employe
                        total_cotisation_employeur += cotisation_employeur
                        data_dict['cotisation_employe'] = cotisation_employe
                        data_dict['cotisation_employeur'] = cotisation_employeur
                        data_dict['employee_id'] = emp_id.id
                        emp_data_list.append(data_dict)
                print(emp_data_list)
                self.line_ids = [(0, 0, d) for d in emp_data_list]
                print(total_cotisation_employe,total_cotisation_employeur)
                return {
                    'total_cotisation_employe': total_cotisation_employe,
                    'total_cotisation_employeur': total_cotisation_employeur,
                    }

    def _print_report(self, data):
        return self.env["ir.actions.report"].search([("report_name", "=", 'hr_cotisation_emp.report_cotisation_emp')],
                                                    limit=1, ).report_action(self, data=data)

    def print_cotisation_emp(self):
        self.ensure_one()
        cotisation_data = self._get_cotisation_emp_data()
        data = {'ids': self.id,
                'form': self.read(['company_id', 'start_date', 'end_date'])[0],
                'model': 'hr.cotisation.emp',
                'total_cotisation_employe': cotisation_data['total_cotisation_employe'],
                'total_cotisation_employeur': cotisation_data['total_cotisation_employeur'],
                }
        return self._print_report(data)


class RapportITSLine(models.Model):
    _name = "hr.cotisation_emp.line"

    employee_id = fields.Many2one("hr.employee", "Employé")
    cotisation_employe = fields.Float("Cotisation employé")
    cotisation_employeur = fields.Float("Cotisation employeur")
    cotisation_emp_id = fields.Many2one("hr.cotisation.emp")
