# -*- coding:utf-8 -*-

from odoo import models, fields


class HrPayrollPayrollWizardXlsx(models.AbstractModel):

    _name = 'report.hr_cnps_mensuel.cnps_mensuel_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = "CNPS Mensuel XLSX Report"

    i = 0

    title = ['NUMERO CNPS', 'NOM', 'ANNEE DE NAISSANCE', 'DATE D\'EMBAUCHE',
             'TYPE SALARIE M: Mensuel J : Journalier '
             'H: Horaire', 'DUREE TRAVAILLEE', 'SALAIRE BRUT']

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
        'num_format': '# ##0'
    }

    a_total_format = {
        'border': 1,
        'align': 'right',
        'valign': 'vcenter',
        'num_format': '# ##0',
        'fg_color': 'gray',
    }
    
    d_format = {
        'bold': 0,
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'fg_color': 'white',
        'num_format': 'd/m/yyyy',
    }
    
    def formatSheet(self, sheet):
        sheet.set_column('A:A', 40)
        sheet.set_column('B:ZZ', 15)

    def generate_xlsx_report(self, workbook, data, obj):
        print("Juste un test")
        sheet = workbook.add_worksheet('LIVRE DE PAIE')
        bold = workbook.add_format({'bold': True})
        header_format = workbook.add_format(self.h_format)
        content_format = workbook.add_format(self.c_format)
        amount_format = workbook.add_format(self.a_format)
        d_format = workbook.add_format(self.d_format)
        amount_total_format = workbook.add_format(self.a_total_format)
        self.formatSheet(sheet)
        
        col = 0
        for i in range(len(self.title)):
            sheet.write(0, col, self.title[i], header_format)
            col += 1
        j = 1
        for line in obj.other_line_ids:
            birth_year = fields.Date.from_string(line.employee_id.birthday) if line.employee_id.birthday else None
            sheet.write(j, 0, line.employee_id.matricule_cnps, content_format)
            sheet.write(j, 1, line.employee_id.name, content_format)
            if birth_year:
                sheet.write(j, 2, birth_year.year, content_format)
            else:
                sheet.write(j, 2, '', content_format)
            sheet.write(j, 3, line.employee_id.start_date, d_format)
            sheet.write(j, 4, line.employee_id.type.upper(), content_format)
            sheet.write(j, 5, 1, content_format)
            sheet.write(j, 6, line.amount_brut, content_format)
            j += 1
