# -*- coding: utf-8 -*-
import time
import babel
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, tools, _
from datetime import datetime, date


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    def _get_worked_day_lines(self):
        """
        :returns: a list of dict containing the worked days values that should be applied for the given payslip
        """
        res = []
        # fill only if the contract as a working schedule linked
        self.ensure_one()
        # Nombre de jours de congés
        date_from = fields.Date.to_string(date.today().replace(day=1))
        next_month = relativedelta(months=+1, day=1, days=-1)
        date_from2 = fields.Date.from_string(date_from)
        date_to = date_from2 + next_month
        leave_historique = self.env['historique.retour_conge'].search([
            ('employee_id', '=', self.employee_id.id),
            ('payroll_date', '>=', date_from2),
            ('payroll_date', '<=', date_to)
        ])
        if leave_historique:
            number_of_days_display = 0
            for lv in leave_historique:
                number_of_days_display += lv.number_of_days_display
            work_entry_type1 = self.env['hr.work.entry.type'].search([('code', '=', 'CONG')])
            if work_entry_type1:
                leave_line = {
                    'sequence': work_entry_type1.sequence,
                    'work_entry_type_id': work_entry_type1.id,
                    'number_of_days': number_of_days_display,
                }
                res.append(leave_line)
            # Nombre de jours travaillés
            if number_of_days_display <= 30:
                worked_days = 30 - number_of_days_display
                worked_hours = worked_days * 173.33 / 30
                work_entry_type = self.env['hr.work.entry.type'].search([('code', '=', 'WORK100')])
                if work_entry_type:
                    attendance_line = {
                        'sequence': work_entry_type.sequence,
                        'work_entry_type_id': work_entry_type.id,
                        'number_of_days': worked_days,
                        'number_of_hours': worked_hours,
                        'rate': worked_days / 30,
                        'amount': 0,
                    }
                    res.append(attendance_line)
            else:
                worked_days = 0
                worked_hours = 0
                work_entry_type = self.env['hr.work.entry.type'].search([('code', '=', 'WORK100')])
                if work_entry_type:
                    attendance_line = {
                        'sequence': work_entry_type.sequence,
                        'work_entry_type_id': work_entry_type.id,
                        'number_of_days': worked_days,
                        'number_of_hours': worked_hours,
                        'rate': worked_days / 30,
                        'amount': 0,
                    }
                    res.append(attendance_line)
        else:
            # Nombre de jours travaillés
            worked_days = 30
            worked_hours = 173.33
            work_entry_type = self.env['hr.work.entry.type'].search([('code', '=', 'WORK100')])
            if work_entry_type:
                attendance_line = {
                    'sequence': work_entry_type.sequence,
                    'work_entry_type_id': work_entry_type.id,
                    'number_of_days': worked_days,
                    'number_of_hours': worked_hours,
                    'rate': worked_days / 30,
                    'amount': 0,
                }
                res.append(attendance_line)
        return res
