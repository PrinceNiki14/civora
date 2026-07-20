# -*- coding:utf-8 -*-

import datetime

from odoo import models, _


class HrPayrollPayrollWizardXlsx(models.AbstractModel):
    _name = 'report.hr_payroll_book.report_payroll_wizard_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = "Payroll BOOK"

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

    c_format = {
        'bold': 0,
        'border': 1,
        'align': 'left',
        'valign': 'vcenter',
        'fg_color': 'white'
    }
    c_format2 = {
        'bold': 1,
        'border': 1,
        'align': 'left',
        'valign': 'vcenter',
        'fg_color': '#b2b2b2'
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
    date_format = {
        'bold': 0,
        'border': 1,
        'align': 'left',
        'valign': 'vcenter',
        'fg_color': 'white',
        'num_format': 'dd/mm/yyyy'
    }
    h_format3 = {
        'bold': 1,
        'border': 1,
        'font_size': 11,
        'align': 'left',
        'valign': 'vcenter',
        'fg_color': 'white',
        'text_wrap': 1
    }
    d_format = {
        'bold': 1,
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'fg_color': 'white',
        'num_format': 'dd/mm/yy',
    }


    def formatSheet(self, sheet):
        sheet.set_column('A:A', 40)
        sheet.set_column('B:ZZ', 15)

    def generate_xlsx_report(self, workbook, data, objs):
        for obj in objs:
            datas = self.env.context.get('data')
            ids = obj.id
            docs = self.env["hr.payroll.book.wizard"].browse(ids)
            #print(datas)
            sheet = workbook.add_worksheet("LIVRE DE PAIE %s" % docs.company_id.name)
            sheet.set_column(1, 100, 25)
            #print(obj)
            total = {}
            bold = workbook.add_format({'bold': True})
            header_format = workbook.add_format(self.h_format)
            content_format = workbook.add_format(self.c_format)
            content_format2 = workbook.add_format(self.c_format2)
            amount_format = workbook.add_format(self.a_format)
            amount_total_format = workbook.add_format(self.a_total_format)
            date_format = workbook.add_format(self.date_format)
            h_format3 = workbook.add_format(self.h_format3)
            d_format = workbook.add_format(self.d_format)

            self.formatSheet(sheet)
            # self.generateHeader(sheet, datas)
            sheet.merge_range("A1:C1", "ENTITÉ : %s" % docs.company_id.name, content_format2)
            sheet.write(1, 0, "DATE DE PAIE", content_format2)
            sheet.write(1, 1, docs.date_from, d_format)
            sheet.write(1, 2, docs.date_to, d_format)

            col = 10
            i = 3
            sheet.write(i, 0, "MATRICULE", header_format)
            sheet.write(i, 1, "NUMERO CNPS", header_format)
            sheet.write(i, 2, "DATE D'EMBAUCHE", header_format)
            sheet.write(i, 3, "ETAT CIVIL", header_format)
            sheet.write(i, 4, "PARTS IGR", header_format)
            sheet.write(i, 5, "CATEGORIE PROFESSIONNELLE", header_format)
            sheet.write(i, 6, "POST OCCUPÉ", header_format)
            sheet.write(i, 7, "DATE NAISSANCE", header_format)
            sheet.write(i, 8, "SEXE", header_format)
            sheet.write(i, 9, "NOM & PRENOMS", header_format)
            for value in datas['rules'].values():
                sheet.write(i, col, value, header_format)
                col += 1

            # self.generateLines(sheet, datas)
            lines = datas['lines']
            j = i + 1
            if lines:
                for dt in lines:
                    col_m = 0
                    col_cnps = 1
                    col_start_date = 2
                    col_marital = 3
                    col_part_igr = 4
                    col_categ_prof = 5
                    col_post_occupe = 6
                    col_birthday = 7
                    col_sexe = 8
                    col_line = 9
                    sheet.write(j, col_m, dt['identification_id'], content_format)
                    sheet.write(j, col_cnps, dt['matricule_cnps'], content_format)
                    sheet.write(j, col_start_date, dt['start_date'], content_format)
                    sheet.write(j, col_marital, dt['marital'], content_format)
                    sheet.write(j, col_part_igr, dt['part_igr'], content_format)
                    sheet.write(j, col_categ_prof, dt['categ_prof'], content_format)
                    sheet.write(j, col_post_occupe, dt['post_occupe'], content_format)
                    sheet.write(j, col_birthday, dt['birthday'], date_format)
                    sheet.write(j, col_sexe, dt['gender'], content_format)
                    sheet.write(j, col_line, dt['name'], content_format)
                    col_line += 1
                    for key in datas['rules'].keys():
                        try:
                            sheet.write(j, col_line, dt[key], amount_format)
                        except:
                            sheet.write(j, col_line, 0, amount_format)
                        col_line += 1
                    j += 1

            # self.generateLinesTotaux(sheet, datas)
            col_line_toto = 10
            h = j
            totaux = datas['total']
            sheet.write(h, 9, 'TOTAUX', amount_total_format)
            for key in datas['rules'].keys():
                try:
                    sheet.write(h, col_line_toto, totaux[key], amount_format)
                except:
                    sheet.write(h, col_line_toto, 0, amount_format)
                col_line_toto += 1
