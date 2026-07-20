# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def get_value_by_code(self, code, value='total'):
        self.ensure_one()
        line = self.line_ids.filtered(lambda l: l.code == code)[:1]
        if line:
            if value == 'total':
                return line.total
            elif value == 'rate':
                return line.rate
            else:
                return line.amount
        return 0

    def get_cumul_by_category_code(self, code, value='total'):
        self.ensure_one()
        category_rec = self.env['hr.salary.rule.category'].search([('code', '=', code)], limit=1)
        if not category_rec:
            return 0.0
        value_map = {'amount': 'amount', 'rate': 'rate', 'total': 'total'}
        value_field = value_map.get(value, 'total')
        lines = self.line_ids.filtered(lambda l: l.category_id.id == category_rec.id)
        return sum(getattr(line, value_field) for line in lines)

    def get_gross_data(self):
        def format_amount(value):
            return '{0:,.0f}'.format(round(value)).replace(',', ' ')

        self.ensure_one()
        data = []
        sequences_to_include = [(100, 300), (500, 520)]
        for start, end in sequences_to_include:
            for line in self.line_ids.filtered(
                    lambda l: l.appears_on_payslip and start <= l.sequence < end and l.amount != 0):
                rate = None
                try:
                    if hasattr(line, 'rate') and line.rate is not False:
                        rate = line.rate
                    elif hasattr(line, 'get_rate'):
                        rate = line.get_rate()
                except Exception:
                    rate = None
                data.append({
                    'sequence': line.sequence,
                    'name': line.name,
                    'code': line.code,
                    'quantity': line.quantity,
                    'amount': format_amount(line.amount),
                    'total': format_amount(line.total),
                    'rate': rate
                })
        return data

    def format_date(self, month):
        months_translation = {
            'January': 'Janvier',
            'February': 'Février',
            'March': 'Mars',
            'April': 'Avril',
            'May': 'Mai',
            'June': 'Juin',
            'July': 'Juillet',
            'August': 'Août',
            'September': 'Septembre',
            'October': 'Octobre',
            'November': 'Novembre',
            'December': 'Décembre'
        }
        return months_translation.get(month, "")

    def format_number(self, value):
        try:
            return '{:,.0f}'.format(float(value)).replace(',', ' ').replace('.', ',')
        except (ValueError, TypeError):
            return value
