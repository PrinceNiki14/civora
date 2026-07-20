# -*- coding:utf-8 -*-

from datetime import datetime
from dateutil import relativedelta
from odoo import models, api


class ContributionRegisterReport(models.AbstractModel):
    _name = 'report.hr_payroll_ci.report_contributionregister'
    _description = 'Contribution Register Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        date_from = data['form'].get('date_from', datetime.now().strftime('%Y-%m-%d'))
        date_to = data['form'].get('date_to', (datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1)).strftime('%Y-%m-%d'))
        
        docs = self.env['hr.contribution.register'].browse(docids)
        
        return {
            'doc_ids': docids,
            'doc_model': 'hr.contribution.register',
            'docs': docs,
            'data': data,
            'date_from': date_from,
            'date_to': date_to,
            'get_payslip_lines': self._get_payslip_lines,
            'sum_total': self._sum_total,
        }

    def _get_payslip_lines(self, obj, date_from, date_to):
        payslip_lines = []
        regi_total = 0.0
        
        self.env.cr.execute("""
            SELECT pl.id 
            FROM hr_payslip_line AS pl
            LEFT JOIN hr_payslip AS hp ON (pl.slip_id = hp.id)
            WHERE (hp.date_from >= %s) AND (hp.date_to <= %s)
            AND pl.register_id = %s
            AND hp.state = 'done'
            ORDER BY pl.slip_id, pl.sequence
        """, (date_from, date_to, obj.id))
        
        line_ids = [x[0] for x in self.env.cr.fetchall()]
        
        for line in self.env['hr.payslip.line'].browse(line_ids):
            payslip_lines.append({
                'payslip_name': line.slip_id.name,
                'name': line.name,
                'code': line.code,
                'quantity': line.quantity,
                'amount': line.amount,
                'total': line.total,
            })
            regi_total += line.total
        
        return payslip_lines, regi_total

    def _sum_total(self, lines):
        return sum(line.get('total', 0.0) for line in lines)
