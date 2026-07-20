# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import format_amount, format_date
from itertools import groupby


class RapportCmu(models.Model):
    _name = "hr.disa.wizard"

    start_date = fields.Date("Date début", required=True)
    end_date = fields.Date("Date Fin", required=True)
    company_id = fields.Many2one("res.company", "Unité", default=lambda self: self.env.company.id, required=True)
    line_ids = fields.One2many("hr.disa_wizard.line", "hr_disa_id")

    def _get_disa_data(self):
        for rec in self:
            rec.env['hr.disa_wizard.line'].search([]).sudo().unlink()
            disa_data_ids = self.env["hr.payslip"].search([('date_from', '>=', rec.start_date),
                                                          ('date_to', '<=', rec.end_date),
                                                          ('company_id', '=', rec.company_id.id)])
            if disa_data_ids:
                emp_ids = disa_data_ids.mapped('employee_id')
                emp_data_list = []
                for emp_id in emp_ids:
                    hr_contract_ids = self.env['hr.contract'].search(
                        [('employee_id', '=', emp_id.id), ('state', '=', 'open')])
                    an_anciennete = 0
                    mois_anciennete = 0
                    for contract in hr_contract_ids:
                        an_anciennete = contract.an_anciennete
                        mois_anciennete = contract.mois_anciennete
                    emp_payslip = disa_data_ids.filtered(lambda x: x.employee_id.id == emp_id.id)
                    emp_id_list = disa_data_ids.filtered(lambda x: x.employee_id.id == emp_id.id).mapped('line_ids')
                    if emp_id_list:
                        type_emp = None
                        if emp_id.type == 'm':
                            type_emp = 'M'
                        if emp_id.type == 'j':
                            type_emp = 'J'
                        if emp_id.type == 'h':
                            type_emp = 'H'
                        data_dict = {
                            'employee_id': emp_id.id,
                            'type': type_emp,
                            'nombre_mois': 0,
                            'brut_imposable': 0,
                            'base_prestation_famille': 0,
                            'montant_prestation_famille': 0,
                            'base_accident_travail': 0,
                            'montant_accident_travail': 0,
                        }
                        brut_imposable = 0
                        base_prestation_famille = 0
                        base_accident_travail = 0
                        montant_prestation_famille = 0
                        montant_accident_travail = 0
                        for line in emp_id_list:
                            if line.code == 'BASE_IMP':
                                brut_imposable += line.total
                            if line.code == 'PF':
                                montant_prestation_famille += line.total
                            if line.code == 'ACT':
                                montant_accident_travail += line.total
                            if line.code == 'BACT_PF':
                                base_prestation_famille += line.total
                                base_accident_travail += line.total
                        data_dict['base_prestation_famille'] = base_prestation_famille
                        data_dict['base_accident_travail'] = base_accident_travail
                        data_dict['montant_prestation_famille'] = montant_prestation_famille
                        data_dict['montant_accident_travail'] = montant_accident_travail
                        data_dict['brut_imposable'] = brut_imposable
                        data_dict['nombre_mois'] = len(emp_payslip)
                        emp_data_list.append(data_dict)
                print(emp_data_list)
                self.line_ids = [(0, 0, d) for d in emp_data_list]

    # def _print_report(self, data):
    #     return self.env["ir.actions.report"].search([("report_name", "=", 'hr_disa.report_hr_disa')],
    #                                                 limit=1, ).report_action(self, data=data)
    #
    # def print_disa(self):
    #     self.ensure_one()
    #     self._get_disa_data()
    #     data = {'ids': self.id,
    #             'form': self.read(['company_id', 'start_date', 'end_date'])[0],
    #             'model': 'hr.disa.wizard',
    #             }
    #     return self._print_report(data)

    def export_xls(self):
        self.ensure_one()
        self._get_disa_data()
        datas = {'ids': self.ids,
                 'model': self._name,
                 'start_date': self.start_date,
                 'end_date': self.end_date,
                 'company_id': self.company_id}
        print(datas)
        return self.env.ref('hr_disa.report_disa_xlsx_id').with_context(data=datas).report_action(self, data=datas)


class RapportCmuLine(models.Model):
    _name = "hr.disa_wizard.line"

    employee_id = fields.Many2one("hr.employee", "Employé")
    type = fields.Char("Type employé")
    nombre_mois = fields.Integer("Nombre de mois")
    brut_imposable = fields.Float("Brut imposable")
    base_prestation_famille = fields.Float("Base prestation familiale")
    montant_prestation_famille = fields.Float("Montant prestation familiale")
    base_accident_travail = fields.Float("Base accident de travail")
    montant_accident_travail = fields.Float("Montant accident de travail")
    hr_disa_id = fields.Many2one("hr.disa.wizard")
