# -*- coding:utf-8 -*-

from odoo import models


class HrPayrollPayrollWizardXlsx(models.AbstractModel):
    _name = 'report.hr_payroll_book.report_payroll_wizard_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = "Payroll BOOK"

    i = 0

    h_format = {
        'bold': 1,
        'border': 1,
        'font_size': 10,
        'align': 'center',
        'valign': 'vcenter',
        'fg_color': 'gray',
        'text_wrap': 1
    }

    c_format = {
        'bold': 0,
        'border': 1,
        'align': 'left',
        'valign': 'vcenter',
        'fg_color': 'white'
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
            datas = self.env.context.get('data')
            sheet = workbook.add_worksheet('LIVRE DE PAIE')
            sheet.set_column(1, 100, 25)
            
            header_format = workbook.add_format(self.h_format)
            content_format = workbook.add_format(self.c_format)
            amount_format = workbook.add_format(self.a_format)
            amount_total_format = workbook.add_format(self.a_total_format)

            self.formatSheet(sheet)

            col = 2
            i = 3
            sheet.write(i, 0, "MATRICULE", header_format)
            sheet.write(i, 1, "NOM & PRENOMS", header_format)
            for value in datas['rules'].values():
                sheet.write(i, col, value, header_format)
                col += 1

            lines = datas['lines']
            j = i + 1
            if lines:
                for dt in lines:
                    col_m = 0
                    col_line = 1
                    sheet.write(j, col_m, dt['identification_id'], content_format)
                    sheet.write(j, col_line, dt['name'], content_format)
                    col_line += 1
                    for key in datas['rules'].keys():
                        sheet.write(j, col_line, dt.get(key, 0), amount_format)
                        col_line += 1
                    j += 1

            col_line_toto = 2
            h = j
            totaux = datas['total']
            sheet.write(h, 1, 'TOTAUX', amount_total_format)
            for key in datas['rules'].keys():
                sheet.write(h, col_line_toto, totaux.get(key, 0), amount_format)
                col_line_toto += 1
