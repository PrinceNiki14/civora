# -*- coding:utf-8 -*-
import time
from odoo import api, fields, models, _
from dateutil import relativedelta
from datetime import datetime
from itertools import groupby

import logging

_logger = logging.getLogger(__name__)


class HrPayrollCotisationSummary(models.TransientModel):
    _name = 'hr_payroll.cotisation_summary'
    _description = 'HR Payroll Cotisation Summary'

    type = ['impot', 'cotisation', 'assurance']

    date_from = fields.Date(string='Date de début', required=True,
                            default=time.strftime('%Y-%m-01'))
    date_to = fields.Date(string='Date de fin', required=True,
                          default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])
    line_ids = fields.One2many('hr_payroll.cotisation_summary_line', 'summary_id', 'Lignes')
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 copy=False, default=lambda self: self.env.company)
    type_employe = fields.Selection([('m', 'Mensuel'), ('j', 'Journalier'), ('h', 'Horaire'),
                                     ('all', 'Tous les employés')], "Livre de paie pour ", default="all")

    def _getPayslipsFprPeriodes(self, company_id, date_from, date_to, type):
        payslip_ids = ()
        payslip_ids = self.env['hr.payslip'].search([('company_id', '=', company_id), ('date_from', '>=', date_from),
                                                     ('date_to', '<=', date_to)])
        if payslip_ids:
            if type != 'all':
                return tuple(payslip_ids.filtered(lambda s: s.employee_id.type == type).ids)
            return tuple(payslip_ids.ids)
        else:
            return ()

    def _getSumBaseRubrique(self, payslips, type, plafond):
        code_rule = "BASE_IMP"
        res = {
            'total': 0,
            'local': 0,
            'expat': 0
        }
        expat = 0
        local = 0
        for nature, bulletins in groupby(payslips, lambda p: p.employee_id.nature_employe):
            total = 0
            if bulletins:
                for slip in bulletins:
                    amount = 0
                    if type == 'cotisation':
                        code_rule = "BASE_CNPS"
                    amount = slip._get_salary_line_total(code_rule)
                    if plafond != 0:
                        amount = min(amount, plafond)
                    total += amount
            if nature == 'local':
                res['local'] += total
            else:
                res['expat'] += total
            res['total'] += total
        return res

    def _getEmployeeByCriteria(self, criteria, company_id):
        employees = self.env['hr.employee'].search([('company_id', '=', company_id)])
        if criteria != 'all':
            employees.filtered(lambda e: e.type == criteria)
        return employees.ids

    def _getSummaryOfContribution(self, bulletins, rules):
        _query = """
            SELECT
                e.nature_employe as code,
                sum(l.total) as total
            FROM 
                (SELECT * FROM hr_payslip_line WHERE slip_id IN %(payslip_ids)s AND salary_rule_id IN %(rules)s) l 
                LEFT JOIN hr_employee e ON (e.id = l.employee_id)
            GROUP BY
                e.nature_employe
        """
        _params = {
            'payslip_ids': bulletins,
            'rules': rules
        }
        self.env.cr.execute(_query, _params)
        results = self.env.cr.dictfetchall()
        if results:
            return {x['code']: x['total'] for x in results}
        return {}

    def compute_summary(self):
        company_id = self.company_id
        date_from = self.date_from
        date_to = self.date_to
        criteria = self.type_employe
        payslip_ids = self._getPayslipsFprPeriodes(company_id.id, date_from, date_to, criteria)
        res = []

        employee_criteria = [('company_id', '=', self.company_id.id)]

        if self.type_employe != 'all':
            employee_criteria.append(('type', '=', self.type_employe))
        employees = self.env['hr.employee'].search(employee_criteria)
        contributions = self.env['hr.contribution.company'].search([('company_id', '=', self.company_id.id)])
        if contributions and payslip_ids:
            for contribution in contributions:
                l_vals = {
                    'name': contribution.name,
                    'type': contribution.type,
                    'contribution_base_local': 0.0,
                    'contribution_base_expat': 0.0,
                    'contribution_base': 0.0,
                    'employee_contribution_local': 0.0,
                    'employee_contribution_expat': 0.0,
                    'employee_contribution': 0.0,
                    'employer_contribution_local': 0.0,
                    'employer_contribution_expat': 0.0,
                    'employer_contribution': 0.0,
                    'total': 0.0
                }
                employee_rule_ids = tuple(contribution.employee_rule_ids.ids)
                employer_rule_ids = tuple(contribution.employer_rule_ids.ids)
                if employee_rule_ids:
                    employee_summary = self._getSummaryOfContribution(payslip_ids, employee_rule_ids)
                    if employee_summary:
                        for key, value in employee_summary.items():
                            if key == 'expat':
                                l_vals['employee_contribution_expat'] = value
                                l_vals['employee_contribution'] += value
                            else:
                                l_vals['employee_contribution_local'] = value
                                l_vals['employee_contribution'] += value
                if employer_rule_ids:
                    employer_summary = self._getSummaryOfContribution(payslip_ids, employer_rule_ids)
                    if employer_summary:
                        for key, value in employer_summary.items():
                            if key == 'expat':
                                l_vals['employer_contribution_expat'] = value
                                l_vals['employer_contribution'] += value
                            else:
                                l_vals['employer_contribution_local'] = value
                                l_vals['employer_contribution'] += value
                payslips = self.env['hr.payslip'].browse(payslip_ids)
                if payslips:
                    contribution_base = self._getSumBaseRubrique(payslips, contribution.type, contribution.plafond)
                    l_vals['contribution_base_local'] = contribution_base['local']
                    l_vals['contribution_base_expat'] = contribution_base['expat']
                    l_vals['contribution_base'] = contribution_base['total']
                l_vals['total'] = l_vals['employer_contribution'] + l_vals['employee_contribution']
                res.append(l_vals)
        return res

    def compute_all(self, type):
        lines = self.compute_summary()
        res = {
            'employee_contribution': 0.0,
            'employer_contribution': 0.0,
            'employe_local': 0.0,
            'employe_expat': 0.0,
            'contribution_base_local': 0.0,
            'contribution_base_expat': 0.0,
            'contribution_base': 0.0,
            'employee_contribution_local': 0.0,
            'employee_contribution_expat': 0.0,
            'employee_contribution': 0.0,
            'employer_contribution_local': 0.0,
            'employer_contribution_expat': 0.0,
            'employer_contribution': 0.0,
            'total': 0.0,
            'lines': []
        }
        for line in lines:
            if line['type'] == type:
                res['contribution_base_local'] += line['contribution_base_local']
                res['contribution_base_expat'] += line['contribution_base_expat']
                res['contribution_base'] += line['contribution_base']
                res['employee_contribution_local'] += line['employee_contribution_local']
                res['employee_contribution_expat'] += line['employee_contribution_expat']
                res['employee_contribution'] += line['employee_contribution']
                res['employer_contribution_local'] += line['employer_contribution_local']
                res['employer_contribution_expat'] += line['employer_contribution_expat']
                res['employer_contribution'] += line['employer_contribution']
                res['total'] += line['total']
                res['lines'].append(line)
        return res

    def format_amount_fr(self, amount, digits=0, separator=' '):
        if amount:
            amount_str = str((amount)).split('.')
            nb = 0
            amount_format = []
            temp = ''
            for i in reversed(amount_str[0]):
                if nb == 3:
                    amount_format.append(separator)
                    nb = 1
                else:
                    nb += 1
                amount_format.append(i)
            amount_format.reverse()
            if digits != 0:
                amount_format.append('.')
                amount_format.append(amount_str[1])
            result = ''.join(amount_format)
            return result

    def export_to_pdf(self):
        self.ensure_one()
        return self.env.ref('hr_contribution_summary.action_report_payroll_summary_contribution').with_context(landscape=True).report_action(self)

    def export_to_excel(self):
        self.ensure_one()
        return True


class HrPayrollCotisationSummaryLine(models.TransientModel):
    _name = 'hr_payroll.cotisation_summary_line'
    _description = 'HR Payroll Cotisation Summary Line'

    rule_id = fields.Many2one('hr.salary.rule', 'Règle salariale', required=True)
    type_rule = fields.Selection([('normal', 'Normal'), ('impot', 'Impôt'), ('cotisation', 'Cotisation'),
                                  ('assurance', 'Assurance')], string='Type de règle', related='rule_id.type_rule')
    contribution_base = fields.Float('Assiette de cotisation')
    employee_contribution = fields.Float('Part salarié')
    employer_contribution = fields.Float('Part employeur')
    employe_local = fields.Float('Local')
    employee_expat = fields.Float('Expatrié')
    total_contribution = fields.Float('Montant global')
    summary_id = fields.Many2one('hr_payroll.cotisation_summary', 'Résumé de cotisation', required=False)
