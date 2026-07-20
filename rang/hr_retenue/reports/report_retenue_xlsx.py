# -*- coding:utf-8 -*-

import datetime

from odoo import models, _


class HrPayrollPayrollWizardXlsx(models.AbstractModel):
    _name = 'report.hr_retenue.report_retenue_xlsx'
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
            sheet = workbook.add_worksheet("Rapport de RETENUE")
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
            docs = self.env['hr.retenue.wizard'].browse(ids)
            self.formatSheet(sheet)
            sheet.write(0, 0, "Rubrique : %s" % docs.salary_id.name, header_format)
            sheet.write(1, 0, "MATRICULE ", header_format)
            sheet.write(1, 1, "AGENT ", header_format)
            sheet.write(1, 2, "MONTANT RETENUE ", header_format)
            line_ids = docs.line_ids
            i = 3
            amount = 0
            number = 0
            for line in line_ids.filtered(lambda l: l.amount != 0):
                sheet.write(i, 0, line.employee_id.identification_id, content_format)
                sheet.write(i, 1, line.employee_id.name, content_format)
                sheet.write(i, 2, line.amount, content_format)
                number += 1
                amount += line.amount
                i += 1
            k = i + 1
            sheet.write(k, 0, 'Total', header_format2)
            sheet.write(k, 1, number, content_format2)
            sheet.write(k, 2, amount, content_format2)

