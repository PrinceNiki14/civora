# -*- coding:utf-8 -*-
from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import format_amount, format_date
from itertools import groupby


class Hr_301(models.TransientModel):
    _name = "hr.301"

    start_date = fields.Date("Date début", required=True)
    end_date = fields.Date("Date Fin", required=True)
    company_id = fields.Many2one("res.company", "Unité", default=lambda self: self.env.company.id, required=True)
    line_ids = fields.One2many("hr_301.line", "hr_301_id")
    lot_id = fields.Many2one("hr.payslip.run", "Lot")

    @api.onchange("lot_id")
    @api.depends("lot_id")
    def onChange_lot(self):
        if self.lot_id:
            self.start_date = self.lot_id.date_start
            self.end_date = self.lot_id.date_end

    def _get_hr_301_data(self):
        for rec in self:
            rec.env['hr_301.line'].search([]).sudo().unlink()
            hr_301_data_ids = self.env["hr.payslip"].search([('date_from', '>=', rec.start_date),
                                                         ('date_to', '<=', rec.end_date),
                                                         ('payslip_run_id', '=', self.lot_id.id),
                                                         ('company_id', '=', rec.company_id.id)])
            if hr_301_data_ids:
                emp_ids = hr_301_data_ids.mapped('employee_id')
                emp_data_list = []
                total_its_p = 0
                for emp_id in emp_ids:
                    emp_id_list = hr_301_data_ids.filtered(lambda x: x.employee_id.id == emp_id.id).mapped('line_ids')
                    worked_days_line_ids = hr_301_data_ids.filtered(lambda x: x.employee_id.id == emp_id.id).mapped('worked_days_line_ids')
                    work_day = 0
                    cong = 0
                    for line in worked_days_line_ids:
                        work_day = sum(l.number_of_days for l in line if line.work_entry_type_id.code == 'WORK100')
                        cong = sum(l.number_of_days for l in line if line.work_entry_type_id.code == 'CONG')
                    if emp_id_list:
                        data_dict = {
                            'employee_id': None,
                            'contract_id': None,
                            'its': 0,
                            'its_p': 0,
                            'cn': 0,
                            'igr': 0
                        }
                        contract_id = self.env["hr.contract"].search([('employee_id', '=', emp_id.id),('state', '=', 'open')])
                        its = 0
                        its_p = 0
                        cn = 0
                        igr = 0
                        net_imp = 0
                        ind_non_imp = 0
                        b_its = 0
                        r_its = 0
                        TAXEAP = 0
                        TAXEFP = 0
                        transport = 0
                        for line in emp_id_list:
                            if line.code == 'ITS':
                                its += line.total
                            if line.code == 'ITS_P':
                                its_p += line.total
                            if line.code == 'TAXEAP':
                                TAXEAP += line.total
                            if line.code == 'TAXEFP':
                                TAXEFP += line.total
                            if line.code == 'CN':
                                cn += line.total
                            if line.code == 'IGR':
                                igr += line.total
                            if line.code == 'BRUT':
                                net_imp += line.total
                            if line.category_id == 'INDMNI' and line.code != 'TRSP':
                                ind_non_imp += line.total
                            if line.code == 'BITS':
                                b_its += line.total
                            if line.code == 'RITS':
                                r_its += line.total
                            if line.code == 'TRSP':
                                transport += line.total
                        total_its_p += its_p
                        data_dict['its'] = its
                        data_dict['its_p'] = its_p
                        data_dict['cn'] = cn
                        data_dict['igr'] = emp_id.id
                        data_dict['TAXEAP'] = TAXEAP
                        data_dict['TAXEFP'] = TAXEFP
                        data_dict['employee_id'] = emp_id.id
                        data_dict['contract_id'] = contract_id.id
                        data_dict['work_day'] = work_day + cong
                        data_dict['net_imp'] = net_imp
                        data_dict['ind_non_imp'] = ind_non_imp
                        data_dict['b_its'] = b_its
                        data_dict['r_its'] = r_its
                        data_dict['transport'] = transport
                        emp_data_list.append(data_dict)
                print(emp_data_list)
                self.line_ids = [(0, 0, d) for d in emp_data_list]

    def export_xls(self):
        self.ensure_one()
        self._get_hr_301_data()
        datas = {'ids': self.ids,
                 'model': self._name,
                 'start_date': self.start_date,
                 'end_date': self.end_date,
                 }
        return self.env.ref('hr_301.report_301_xlsx_id').with_context(data=datas).report_action(self, data=datas)


class RapportCmuLine(models.TransientModel):
    _name = "hr_301.line"

    employee_id = fields.Many2one("hr.employee")
    contract_id = fields.Many2one("hr.contract")
    its = fields.Float("ITS")
    work_day = fields.Float("Jour travaillé")
    its_p = fields.Float("ITS Patronal")
    TAXEAP = fields.Float()
    TAXEFP = fields.Float()
    cn = fields.Float("CN")
    igr = fields.Float("IGR")
    net_imp = fields.Float("Net imposable")
    ind_non_imp = fields.Float("Indemnité non imposable")
    total_brut = fields.Float("Total brut")
    b_its = fields.Float("Brut impôt ITS")
    r_its = fields.Float("Réduction impôt ITS")
    transport = fields.Float("Transport")
    hr_301_id = fields.Many2one("hr.301")
