# -*- coding:utf-8 -*-

import datetime

from odoo import models, _


class HrPayrollPayrollWizardXlsx(models.AbstractModel):
    _name = 'report.hr_payroll_book.report_cmu_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    i = 0

    # Formattage pour les headers
    h_format = {
        'bold': 1,
        'border': 1,
        'font_size': 10,
        'align': 'center',
        'valign': 'vcenter',
        'fg_color': 'gray',
        'text_wrap': 1
    }
    h_format2 = {
        'bold': 1,
        'border': 1,
        'font_size': 10,
        'align': 'left',
        'valign': 'vcenter',
        'fg_color': 'gray',
        'text_wrap': 1
    }

    c_format = {
        'bold': 0,
        'border': 1,
        'align': 'left',
        'valign': 'vcenter',
        'fg_color': 'white',
    }
    c_format2 = {
        'bold': 0,
        'border': 1,
        'align': 'right',
        'valign': 'vcenter',
        'fg_color': 'white',
    }
    d_format = {
        'bold': 0,
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'fg_color': 'white',
        'num_format': 'dd-mm-yy',
    }

    a_format = {
        'border': 1,
        'align': 'right',
        'valign': 'vcenter',
        'num_format': '#,##0'
    }

    a_total_format = {
        'border': 1,
        'align': 'right',
        'valign': 'vcenter',
        'num_format': '#,##0',
        'fg_color': 'gray',
    }

    def formatSheet(self, sheet):
        sheet.set_column('A:A', 40)
        sheet.set_column('B:ZZ', 15)

    def generate_xlsx_report(self, workbook, data, objs):
        for obj in objs:
            self.env.context.get('data')
            sheet = workbook.add_worksheet("Rapport cotisation CMU")
            sheet.set_column(1, 100, 25)
            ids = obj.id
            workbook.add_format({'bold': True})
            header_format = workbook.add_format(self.h_format)
            header_format2 = workbook.add_format(self.h_format2)
            content_format = workbook.add_format(self.c_format)
            content_format2 = workbook.add_format(self.c_format2)
            date_format = workbook.add_format(self.d_format)
            amount_format = workbook.add_format(self.a_format)
            amount_total_format = workbook.add_format(self.a_total_format)
            docs = self.env['hr.cmu.wizard'].browse(ids)
            self.formatSheet(sheet)
            sheet.write(0, 0, "Rapport cotisation CMU", header_format)
            sheet.write(1, 0, "Date : ", header_format)
            sheet.write(1, 1, docs.start_date, date_format)
            sheet.write(1, 2, docs.end_date, date_format)
            sheet.write(2, 0, "Employee", header_format2)
            sheet.write(2, 1, "CMU employé", header_format)
            sheet.write(2, 2, "CMU employeur", header_format)
            line_ids = docs.line_ids
            i = 3
            cmu_employe = 0
            cmu_employeur = 0
            for line in line_ids.sorted(key=lambda r: r.employee_id.name):
                sheet.write(i, 0, line.employee_id.name, content_format)
                sheet.write(i, 1, line.cmu_employe, content_format2)
                sheet.write(i, 2, line.cmu_employeur, content_format2)
                cmu_employe += line.cmu_employe
                cmu_employeur += line.cmu_employeur
                i += 1
            k = i + 1
            sheet.write(k, 0, 'Total', header_format2)
            sheet.write(k, 1, cmu_employe, content_format2)
            sheet.write(k, 2, cmu_employeur, content_format2)

