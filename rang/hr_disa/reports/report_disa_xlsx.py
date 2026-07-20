# -*- coding:utf-8 -*-

import datetime

from odoo import models, _


class HrPayrollPayrollDISAWizardXlsx(models.AbstractModel):
    _name = 'report.hr_disa.report_disa_xlsx'
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
        'num_format': 'dd/mm/yy',
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
            print('here')
            self.env.context.get('data')
            sheet = workbook.add_worksheet("Rapport DISA")
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
            docs = self.env['hr.disa.wizard'].browse(ids)
            self.formatSheet(sheet)
            sheet.write(0, 0, "Numéro CNPS", header_format)
            sheet.write(0, 1, "Nom", header_format)
            sheet.write(0, 2, "Prénom", header_format)
            sheet.write(0, 3, "Date de naissance", header_format)
            sheet.write(0, 4, "Date d'embauche société", header_format)
            sheet.write(0, 5, "Date de départ société", header_format)
            sheet.write(0, 6, "Type de salaire H, J OU M", header_format)
            sheet.write(0, 7, "Nombre de mois", header_format)
            sheet.write(0, 8, "Brut total", header_format)
            sheet.write(0, 9, "Base prestation familiale", header_format)
            sheet.write(0, 10, "Montant prestation familiale", header_format)
            sheet.write(0, 11, "Base accident de travail", header_format)
            sheet.write(0, 12, "Montant accident de travail", header_format)
            line_ids = docs.line_ids
            i = 1
            for line in line_ids.sorted(key=lambda r: r.employee_id.name):
                sheet.write(i, 0, line.employee_id.matricule_cnps if line.employee_id.matricule_cnps else '', content_format)
                sheet.write(i, 1, line.employee_id.firstname, content_format)
                sheet.write(i, 2, line.employee_id.lastname, content_format)
                sheet.write(i, 3, str(line.employee_id.birthday)[:4])
                sheet.write(i, 4, line.employee_id.start_date, date_format)
                sheet.write(i, 5, line.employee_id.end_date if line.employee_id.end_date else '', date_format)
                sheet.write(i, 6, line.type, content_format)
                sheet.write(i, 7, line.nombre_mois, content_format2)
                sheet.write(i, 8, line.brut_imposable, content_format2)
                sheet.write(i, 9, line.base_prestation_famille, content_format2)
                sheet.write(i, 10, line.montant_prestation_famille, content_format2)
                sheet.write(i, 11, line.base_accident_travail, content_format2)
                sheet.write(i, 12, line.montant_accident_travail, content_format2)
                i += 1
