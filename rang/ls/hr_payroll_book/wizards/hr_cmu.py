# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class RapportCmu(models.TransientModel):
    _name = "hr.cmu.wizard"
    _description = "HR CMU Report Wizard"

    start_date = fields.Date("Date début", required=True)
    end_date = fields.Date("Date Fin", required=True)
    company_id = fields.Many2one(
        "res.company",
        "Unité",
        default=lambda self: self.env.company.id,
        required=True
    )
    line_ids = fields.One2many("hr.cmu_wizard.line", "hr_cmu_id")

    def _get_cmu_data(self):
        for rec in self:
            rec.env['hr.cmu_wizard.line'].search([]).sudo().unlink()
            cmu_data_ids = self.env["hr.payslip"].search([
                ('date_from', '>=', rec.start_date),
                ('date_to', '<=', rec.end_date),
                ('company_id', '=', rec.company_id.id)
            ])
            if cmu_data_ids:
                emp_ids = cmu_data_ids.mapped('employee_id')
                emp_data_list = []
                for emp_id in emp_ids:
                    emp_id_list = cmu_data_ids.filtered(
                        lambda x: x.employee_id.id == emp_id.id
                    ).mapped('line_ids')
                    if emp_id_list:
                        data_dict = {
                            'employee_id': emp_id.id,
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
                        data_dict['cmu_employe'] = cmu_employe
                        data_dict['cmu_employeur'] = cmu_employeur
                        emp_data_list.append(data_dict)
                self.line_ids = [(0, 0, d) for d in emp_data_list]

    def export_xls(self):
        self.ensure_one()
        self._get_cmu_data()
        datas = {
            'ids': self.ids,
            'model': self._name,
            'start_date': self.start_date,
            'end_date': self.end_date
        }
        return self.env.ref('hr_payroll_book.report_cmu_xlsx_id').with_context(
            data=datas
        ).report_action(self, data=datas)


class RapportCmuLine(models.TransientModel):
    _name = "hr.cmu_wizard.line"
    _description = "HR CMU Wizard Line"

    employee_id = fields.Many2one("hr.employee", "Employé")
    cmu_employe = fields.Float("CMU employé")
    cmu_employeur = fields.Float("CMU employeur")
    hr_cmu_id = fields.Many2one("hr.cmu.wizard")
