# -*- coding:utf-8 -*-

import datetime

from odoo import models, _


class HrPayrollPayrollWizardXlsx(models.AbstractModel):
    _name = 'report.hr_301.report_301_xlsx'
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
    c_format3 = {
        'bold': 0,
        'border': 1,
        'align': 'center',
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
            sheet = workbook.add_worksheet("Etat 301")
            sheet.set_column(1, 100, 25)
            ids = obj.id
            workbook.add_format({'bold': True})
            header_format = workbook.add_format(self.h_format)
            header_format2 = workbook.add_format(self.h_format2)
            content_format = workbook.add_format(self.c_format)
            content_format2 = workbook.add_format(self.c_format2)
            content_format3 = workbook.add_format(self.c_format3)
            date_format = workbook.add_format(self.d_format)
            amount_format = workbook.add_format(self.a_format)
            amount_total_format = workbook.add_format(self.a_total_format)
            docs = self.env['hr.301'].browse(ids)
            self.formatSheet(sheet)
            sheet.write(0, 0, 'Date de début', content_format2)
            sheet.write(0, 1, docs.start_date, date_format)
            sheet.write(1, 0, 'Date de fin', content_format2)
            sheet.write(1, 1, docs.end_date, date_format)
            sheet.write(2, 0, "Etat 301", header_format)
            sheet.write(3, 0, "N° CNPS : ", header_format)
            sheet.write(3, 1, "Nom et Prénoms", header_format)
            sheet.write(3, 2, "Type de travailleur", header_format)
            sheet.write(3, 3, "Emploi ou Qualité", header_format)
            sheet.write(3, 4, "Code Emploi", header_format2)
            sheet.write(3, 5, "Régime Général G ou Agricole A", header_format)
            sheet.write(3, 6, "Sexe", header_format)
            sheet.write(3, 7, "Nationalité", header_format)
            sheet.write(3, 8, "Local/Expatrié", header_format)
            sheet.write(3, 9, "Etat civil", header_format)
            sheet.write(3, 10, "Nombre d'enfants à charge", header_format)
            sheet.write(3, 11, "Nombre de parts IGR", header_format)
            sheet.write(3, 12, "Nombre de jours d'application des paiements", header_format)
            sheet.write(3, 13, "Montant des salaires et rémunérations accessoires (ou pensions et rentes viagères)",
                        header_format)
            sheet.write(3, 14, "Montant des savantages en nature suivant barème réglementaire", header_format)
            sheet.write(3, 15, "Montant des savantages en nature selon valeur réelle", header_format)
            sheet.write(3, 16, "Rémuneration total brut", header_format)
            sheet.write(3, 17, "Révenus non imposables", header_format)
            sheet.write(3, 18, "Rémuneration brut imposable", header_format)
            sheet.write(3, 19, "Réduction d'impôt pour charges de famille (RICF)", header_format)
            sheet.write(3, 20, "Brut", header_format)
            sheet.write(3, 21, "Net", header_format)
            sheet.write(3, 22, "Montant", header_format)
            sheet.write(3, 23, "Désignation", header_format)
            sheet.write(3, 24, "ITS Patronal", header_format)
            sheet.write(3, 25, "FDFP TA", header_format)
            sheet.write(3, 26, "FDFP TFPC", header_format)
            line_ids = docs.line_ids
            i = 4
            total_its_p = 0
            total_TAXEAP = 0
            total_TAXEFP = 0
            for line in line_ids.sorted(key=lambda r: r.employee_id.name):
                # Sexe
                sexe = None
                if line.employee_id.gender == 'male':
                    sexe = 'M'
                if line.employee_id.gender == 'female':
                    sexe = 'F'
                # Local/Expatrié
                nature_employe = None
                if line.employee_id.nature_employe == 'local':
                    nature_employe = 'L'
                if line.employee_id.nature_employe == 'expat':
                    nature_employe = 'E'
                # Etat civil
                etat_civil = None
                if line.employee_id.marital == 'single':
                    etat_civil = 'C'
                if line.employee_id.marital == 'married':
                    etat_civil = 'M'
                if line.employee_id.marital == 'widower':
                    etat_civil = 'V'
                if line.employee_id.marital == 'divorced':
                    etat_civil = 'D'
                # Type de travailleur
                type_travailleur = None
                if line.employee_id.type == 'm':
                    type_travailleur = 'Salarié'
                if line.employee_id.type == 'h' or line.employee_id.type == 'j':
                    type_travailleur = "Main d'œuvre occasionnelle"
                sheet.write(i, 0, line.employee_id.matricule_cnps if line.employee_id.matricule_cnps else '',
                            content_format)
                sheet.write(i, 1, line.employee_id.name, content_format)
                sheet.write(i, 2, type_travailleur, content_format)
                sheet.write(i, 3, line.contract_id.job_id.name if line.contract_id.job_id.name else '', content_format)
                sheet.write(i, 4, '', content_format)
                sheet.write(i, 5, '', content_format)
                sheet.write(i, 6, sexe, content_format3)
                sheet.write(i, 7, 'I', content_format3)
                sheet.write(i, 8, nature_employe, content_format3)
                sheet.write(i, 9, etat_civil, content_format3)
                sheet.write(i, 10, line.employee_id.children, content_format3)
                sheet.write(i, 11, line.employee_id.part_igr, content_format3)
                sheet.write(i, 12, line.work_day, content_format3)
                sheet.write(i, 13, line.net_imp + line.ind_non_imp, content_format2)
                sheet.write(i, 14, 0, content_format2)
                sheet.write(i, 15, 0, content_format2)
                sheet.write(i, 16, line.net_imp + line.ind_non_imp, content_format2)
                sheet.write(i, 17, line.ind_non_imp, content_format2)
                sheet.write(i, 18, line.net_imp, content_format2)
                sheet.write(i, 19, line.r_its, content_format2)
                sheet.write(i, 20, line.b_its, content_format2)
                sheet.write(i, 21, line.b_its - line.r_its if line.b_its - line.r_its > 0 else 0, content_format)
                sheet.write(i, 22, line.transport, content_format)
                sheet.write(i, 23, 'Transport', content_format)
                sheet.write(i, 24, line.its_p, content_format2)
                sheet.write(i, 25, line.TAXEAP, content_format2)
                sheet.write(i, 26, line.TAXEFP, content_format2)
                total_its_p += line.its_p
                total_TAXEAP += line.TAXEAP
                total_TAXEFP += line.TAXEFP
                i += 1
            k = i + 1
            sheet.write(k, 24, total_its_p, header_format2)
            sheet.write(k, 25, total_TAXEAP, content_format2)
            sheet.write(k, 26, total_TAXEFP, content_format2)
