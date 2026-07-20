# -*- coding:utf-8 -*-

import datetime

from odoo import models, _


class OdreVirementXlsx(models.AbstractModel):
    _name = 'report.hr_payroll_book.report_ordre_virement_xlsx'
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
            ids = obj.id
            docs = self.env['ordre.virement'].browse(ids)
            sheet = workbook.add_worksheet("ORDRE DE VIREMENT DE %s " % docs.company_id.name)
            sheet.set_column(1, 100, 25)
            workbook.add_format({'bold': True})
            header_format = workbook.add_format(self.h_format)
            header_format2 = workbook.add_format(self.h_format2)
            content_format = workbook.add_format(self.c_format)
            content_format2 = workbook.add_format(self.c_format2)
            date_format = workbook.add_format(self.d_format)
            amount_format = workbook.add_format(self.a_format)
            amount_total_format = workbook.add_format(self.a_total_format)
            self.formatSheet(sheet)
            #sheet.write(0, 0, "ORDRE DE VIREMENT DE %s " % docs.company_id.name, header_format)
            sheet.merge_range('A1:E1', "ORDRE DE VIREMENT DE %s " % docs.company_id.name, header_format)
            if docs.type_virement == 'salaire':
                sheet.write(1, 0, "PERIDOE : ", content_format)
                sheet.write(1, 1, docs.date_from, date_format)
                sheet.write(1, 2, docs.date_to, date_format)
                sheet.write(3, 0, "Matricule", header_format2)
                sheet.write(3, 1, "Bénéficiare", header_format2)
                sheet.write(3, 2, "Banque", header_format)
                sheet.write(3, 3, "Code Banque", header_format)
                sheet.write(3, 4, "Code guichet", header_format)
                sheet.write(3, 5, "Clé RIB", header_format)
                sheet.write(3, 6, "Compte", header_format)
                sheet.write(3, 7, "Net à Payer", header_format)
            if docs.type_virement == 'accessoire':
                sheet.write(1, 0, "PERIDOE : ", content_format)
                sheet.write(1, 1, docs.date_from, date_format)
                sheet.write(1, 2, docs.date_to, date_format)
                sheet.write(3, 0, "Bénéficiare", header_format2)
                sheet.write(3, 1, "Banque", header_format)
                sheet.write(3, 2, "Code Banque", header_format)
                sheet.write(3, 3, "Code guichet", header_format)
                sheet.write(3, 4, "Clé RIB", header_format)
                sheet.write(3, 5, "Compte", header_format)
                sheet.write(3, 6, "Net à Payer", header_format)
            salaire_ids = docs.salaire_ids
            accessoire_ids = docs.accessoire_ids
            i = 4
            net_paie = 0
            if docs.type_virement == 'salaire':
                for line in salaire_ids.sorted(key=lambda r: r.employee_id.name):
                    sheet.write(i, 0, line.employee_id.identification_id if line.employee_id.identification_id else '', content_format)
                    sheet.write(i, 1, line.employee_id.name, content_format2)
                    sheet.write(i, 2, line.employee_id.banque_id.name if line.employee_id.banque_id.name else '', content_format2)
                    sheet.write(i, 3, line.employee_id.code_banque if line.employee_id.code_banque else '', content_format2)
                    sheet.write(i, 4, line.employee_id.code_guichet if line.employee_id.code_guichet else '', content_format2)
                    sheet.write(i, 5, line.employee_id.cle_rib if line.employee_id.cle_rib else '', content_format2)
                    sheet.write(i, 6, line.employee_id.num_compte_bancaire if line.employee_id.num_compte_bancaire else '', content_format2)
                    sheet.write(i, 7, line.net_paie if line.net_paie else 0, content_format2)
                    net_paie += line.net_paie
                    i += 1
                k = i + 1
                sheet.write(k, 3, 'Total', header_format2)
                sheet.write(k, 4, net_paie, content_format2)
            if docs.type_virement == 'accessoire':
                for line in accessoire_ids.sorted(key=lambda r: r.salary_rule_id.name):
                    sheet.write(i, 0, line.salary_rule_id.name, content_format2)
                    sheet.write(i, 1, line.salary_rule_id.banque_id.name if line.salary_rule_id.banque_id.name else '', content_format2)
                    sheet.write(i, 2, line.salary_rule_id.code_banque if line.salary_rule_id.code_banque else '', content_format2)
                    sheet.write(i, 3, line.salary_rule_id.code_guichet if line.salary_rule_id.code_guichet else '', content_format2)
                    sheet.write(i, 4, line.salary_rule_id.cle_rib if line.salary_rule_id.cle_rib else '', content_format2)
                    sheet.write(i, 5, line.salary_rule_id.num_compte_bancaire if line.salary_rule_id.num_compte_bancaire else '', content_format2)
                    sheet.write(i, 6, line.net_paie if line.net_paie else 0, content_format2)
                    net_paie += line.net_paie
                    i += 1
                k = i + 1
                sheet.write(k, 3, 'Total', header_format2)
                sheet.write(k, 4, net_paie, content_format2)

