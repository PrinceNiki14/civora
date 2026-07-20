# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import format_amount, format_date
from itertools import groupby


class RapportCmu(models.TransientModel):
    _name = "hr.cgrae"

    start_date = fields.Date("Date début", required=True)
    end_date = fields.Date("Date Fin", required=True)
    company_id = fields.Many2one("res.company", "Unité", default=lambda self: self.env.company.id, required=True)
    line_ids = fields.One2many("hr.cgrae.line", "hr_cgrae_id")
    lot_id = fields.Many2one("hr.payslip.run", "Lot")

    @api.onchange("lot_id")
    @api.depends("lot_id")
    def onChangeLot(self):
        if self.lot_id:
            self.start_date = self.lot_id.date_start
            self.end_date = self.lot_id.date_end

    def _get_cgrae_data(self):
        for rec in self:
            rec.env['hr.cgrae.line'].search([]).sudo().unlink()
            cotisation_emp_data_ids = self.env["hr.payslip"].search([('date_from', '>=', rec.start_date),
                                                         ('date_to', '<=', rec.end_date),
                                                         ('payslip_run_id', '=', self.lot_id.id),
                                                         ('company_id', '=', rec.company_id.id)])
            # cgrae_data_list = []
            # if payslis_ids:
            #     emp_ids = payslis_ids.mapped('employee_id')
            #     data_dict = {
            #         'effectifs': 0,
            #         'sal_brut_ind_soum': 0,
            #         'cgrae_employe': 0,
            #         'cgrae_employeur': 0,
            #         'total_cgrae': 0
            #     }
            #     cgrae_data_ids = payslis_ids.filtered(lambda x: x.employee_id.type_employee == 'F')
            #     emp_ids = cgrae_data_ids.mapped('employee_id')
            #     emp_obj = emp_ids.filtered(lambda x: x.type_employee == 'F')
            #     print(emp_ids)
            #     line_ids = cgrae_data_ids.mapped('line_ids')
            #     cgrae_employe = 0
            #     cgrae_employeur = 0
            #     sal_brut_ind_soum = 0
            #     for line in line_ids:
            #         if line.code == 'CGRAE':
            #             cgrae_employe += line.total
            #         if line.code == 'CGRAE_P':
            #             cgrae_employeur += line.total
            #         if line.code == 'BASE_CGRAE':
            #             sal_brut_ind_soum += line.total
            #     data_dict['cgrae_employe'] = sum(line.total for line in line_ids if line.code == 'CGRAE')
            #     #data_dict['cgrae_employe'] = cgrae_employe
            #     #data_dict['cgrae_employeur'] = cgrae_employeur
            #     data_dict['cgrae_employeur'] = sum(line.total for line in line_ids if line.code == 'CGRAE_P')
            #     data_dict['total_cgrae'] = cgrae_employeur + cgrae_employe
            #     #data_dict['sal_brut_ind_soum'] = cgrae_employeur + cgrae_employe
            #     data_dict['sal_brut_ind_soum'] = sum(line.total for line in line_ids if line.code == 'BASE_CGRAE')
            #     data_dict['effectifs'] = len(emp_obj) if emp_obj else 0
            #     cgrae_data_list.append(data_dict)
            #     return data_dict
            # else:
            #     return {
            #         'effectifs': 0,
            #         'sal_brut_ind_soum': 0,
            #         'cgrae_employe': 0,
            #         'cgrae_employeur': 0,
            #         'total_cgrae': 0
            #     }
            if cotisation_emp_data_ids:
                emp_ids = cotisation_emp_data_ids.mapped('employee_id')
                emp_data_list = []
                total_cotisation_employe = 0
                total_cotisation_employeur = 0
                total_BASE_CGRAE = 0
                effectifs = 0
                for emp_id in emp_ids:
                    emp_id_list = cotisation_emp_data_ids.filtered(lambda x: x.employee_id.id == emp_id.id).mapped('line_ids')
                    if emp_id_list:
                        data_dict = {
                            'employee_id': None,
                            'cotisation_employe': 0,
                            'cotisation_employeur': 0,
                            'BASE_CGRAE': 0
                        }
                        cotisation_employe = 0
                        cotisation_employeur = 0
                        BASE_CGRAE = 0
                        #rule_code = self.env["hr.salary.rule"].search([('linked_to', '=', self.salary_id.id)]).code
                        for line in emp_id_list:
                            if line.code == 'CGRAE' and line.total != 0:
                                effectifs += 1
                                cotisation_employe += line.total
                            if line.code == 'CGRAE_P' and line.total != 0:
                                cotisation_employeur += line.total
                            if line.code == 'BASE_CGRAE' and line.total != 0:
                                BASE_CGRAE += line.total
                        total_cotisation_employe += cotisation_employe
                        total_cotisation_employeur += cotisation_employeur
                        total_BASE_CGRAE += BASE_CGRAE
                #         data_dict['cotisation_employe'] = cotisation_employe
                #         data_dict['cotisation_employeur'] = cotisation_employeur
                #         data_dict['total_BASE_CGRAE'] = total_BASE_CGRAE
                #         data_dict['employee_id'] = emp_id.id
                #         emp_data_list.append(data_dict)
                # self.line_ids = [(0, 0, d) for d in emp_data_list]
                return {
                    'total_cotisation_employe': total_cotisation_employe,
                    'total_cotisation_employeur': total_cotisation_employeur,
                    'total_BASE_CGRAE': total_BASE_CGRAE,
                    'total_cgrae': total_cotisation_employe + total_cotisation_employeur,
                    'effectifs': effectifs,
                    }

    def _print_report(self, data):
        return self.env["ir.actions.report"].search([("report_name", "=", 'hr_cgrae.report_hr_cgrae')],
                                                    limit=1, ).report_action(self, data=data)

    def print_cgrae(self):
        self.ensure_one()
        cotisation_data = self._get_cgrae_data()
        data = {'ids': self.id,
                'form': self.read(['company_id', 'start_date', 'end_date'])[0],
                'model': 'hr.cgrae',
                'total_cotisation_employe': cotisation_data['total_cotisation_employe'],
                'total_cotisation_employeur': cotisation_data['total_cotisation_employeur'],
                'total_BASE_CGRAE': cotisation_data['total_BASE_CGRAE'],
                'effectifs': cotisation_data['effectifs'],
                'total_cgrae': cotisation_data['total_cgrae'],
                # 'effectifs': data_dict['effectifs'],
                # 'cgrae_employeur': data_dict['cgrae_employeur'],
                # 'cgrae_employe': data_dict['cgrae_employe'],
                # 'total_cgrae': data_dict['total_cgrae'],
                # 'sal_brut_ind_soum': data_dict['sal_brut_ind_soum']
                }
        return self._print_report(data)


class RapportCmuLine(models.TransientModel):
    _name = "hr.cgrae.line"

    effectifs = fields.Integer("Effectifs")
    total_cgrae = fields.Float("Total CGRAE")
    cgrae_employe = fields.Float("CGRAE employé")
    cgrae_employeur = fields.Float("CGRAE employeur")
    hr_cgrae_id = fields.Many2one("hr.cgrae")
