# -*- coding:utf-8 -*-
from datetime import date

from odoo import api, models, fields, _
from dateutil import relativedelta

from odoo.tools import format_date


class Employee(models.Model):
    _inherit = "hr.employee"

    @api.model
    def compute_holidays_auto(self):
        this_date = date.today()
        type = self.env['hr.leave.type'].search([('code', '=', 'CONG')],limit=1)
        if type:
            for emp in self.search([('type', '=', 'm')]):
                temp_date = fields.Date.from_string(emp.start_date) + relativedelta.relativedelta(month=this_date.month,
                                                                                                  year=this_date.year)
                # if temp_date == this_date:
                # print("Employé %s est venu le %s",(emp.name, emp.start_date))
                # self.name = '%s - %s - %s' % (payslip_name, self.employee_id.name or '', format_date(self.env, self.date_from, date_format="MMMM y"))
                # name = 'Attribution congés annuels de %s-%s' % (this_date.month, this_date.year)
                name = 'Attribution congés annuels de %s' % (format_date(self.env, this_date, date_format="MMMM y"))
                # if emp.id == 419:
                vals = {
                    'name': name,
                    'employee_id': emp.id,
                    'holiday_status_id': type.id,
                    'allocation_type': 'regular',
                    'holiday_type': 'employee',
                    'date_allocation': this_date,
                    'company_id': emp.company_id.id,
                }
                if emp.nature_employe == 'local':
                    vals['number_of_days'] = emp.company_id.number_holidays_locaux
                else:
                    vals['number_of_days'] = emp.company_id.number_holidays_expat
                holidays = self.env['hr.leave.allocation'].create(vals)
                if holidays:
                    holidays.action_validate()
        return True

    # def _get_remaining_leaves_legals(self):
    #     """ Helper to compute the remaining leaves for the current employees
    #         :returns dict where the key is the employee id, and the value is the remain leaves
    #     """
    #     self._cr.execute("""
    #         SELECT
    #             sum(h.number_of_days) AS days,
    #             h.employee_id
    #         FROM
    #             hr_leave h
    #             join hr_leave_type_status s ON (s.id=h.holiday_status_id)
    #         WHERE
    #             h.state='validate' AND
    #             s.limit=False AND
    #             h.employee_id in %s AND s.code='CONG'
    #         GROUP BY h.employee_id""", (tuple(self.ids),))
    #     return dict((row['employee_id'], row['days']) for row in self._cr.dictfetchall())
    #
    # def _compute_remaining_leaves_legals(self):
    #     for emp in self:
    #         # remaining = emp._get_remaining_leaves_legals()
    #         emp.holidays_legal_leaves = 0
    #
    # def _get_holidays_taked(self):
    #     this_date = fields.Date.today()
    #     date_from = this_date + relativedelta(month=1, day=1)
    #     date_to = this_date + relativedelta(month=12, day=31)
    #     print(date_from)
    #     print(date_to)
    #
    # def _getAllInfosLeave(self):
    #     for emp in self:
    #         first_day = fields.Date.today().replace(day=1, month=1)
    #         print(first_day)
    #         allocations = self.env['hr.leave.allocation']
    #         emp.leave_acquired_this_year = 0
    #
    # def getAcquiredHolidaysByPeriod(self, date_from, date_to):
    #     _query = """
    #                 SELECT
    #                     type.name,
    #                     sum(allocation.number_of_days) AS allocation_days,
    #                     allocation.employee_id
    #                 FROM
    #                     (   select * FROM hr_leave_type WHERE code = 'CONG' ) type
    #                     LEFT JOIN hr_leave_allocation allocation ON (allocation.holiday_status_id = type.id AND
    #                     date_allocation <= %(date_to)s AND allocation.employee_id = %(employee_id)s AND
    #                     date_allocation >= %(date_from)s AND allocation.state = 'validate')
    #                 GROUP BY
    #                     type.name,
    #                     allocation.employee_id
    #             """
    #
    #     _params = {
    #         'employee_id': self.id,
    #         'date_to': date_to,
    #         'date_from': date_from
    #     }
    #
    #     self.env.cr.execute(_query, _params)
    #     result = self.env.cr.dictfetchone()
    #     if result:
    #         return result.get('allocation_days') or 0
    #     return 0
    #
    # def getAcquiredHolidays(self, date_to):
    #     _query = """
    #         SELECT
    #             type.name,
    #             sum(allocation.number_of_days) AS allocation_days,
    #             allocation.employee_id
    #         FROM
    #             (   select * FROM hr_leave_type WHERE code = 'CONG' ) type
    #             LEFT JOIN hr_leave_allocation allocation ON (allocation.holiday_status_id = type.id AND
    #             date_allocation <= %(date_to)s AND allocation.employee_id = %(employee_id)s AND allocation.state = 'validate')
    #         GROUP BY
    #             type.name,
    #             allocation.employee_id
    #     """
    #
    #     _params = {
    #         'employee_id': self.id,
    #         'date_to': date_to
    #     }
    #
    #     self.env.cr.execute(_query, _params)
    #     result = self.env.cr.dictfetchone()
    #     if result:
    #         return result.get('allocation_days') or 0
    #     return 0
    #
    # def getATotalTakedHolidays(self, date_to):
    #     _query = """
    #         SELECT
    #             type.name,
    #             sum(leave.number_of_days) AS leaves,
    #             leave.employee_id
    #         FROM
    #             (   select * FROM hr_leave_type WHERE code = 'CONG' ) type
    #             LEFT JOIN hr_leave leave ON (leave.holiday_status_id = type.id AND
    #             leave.request_date_from < %(date_to)s AND leave.employee_id = %(employee_id)s AND leave.state = 'validate')
    #         GROUP BY
    #             type.name,
    #             leave.employee_id
    #     """
    #     _params = {
    #         'employee_id': self.id,
    #         'date_to': date_to
    #     }
    #     self.env.cr.execute(_query, _params)
    #     result = self.env.cr.dictfetchone()
    #     if result:
    #         return result.get('leaves') or 0
    #     return 0
    #
    # def getSummaryHolidaysAllocation(self, date_from, date_to):
    #     allocations = self.getAcquiredHolidays(date_to)
    #     leaves = self.getATotalTakedHolidays(date_from)
    #     print(allocations)
    #     print(leaves)
    #     return allocations - leaves
    #
    # def getTakedHoliday(self, date_from, date_to, type):
    #     if type != 'monthly':
    #         date_from = fields.Date.to_string(date_to.replace(day=1, month=1))
    #     _query = """
    #         SELECT
    #             type.name,
    #             sum( leave.number_of_days) AS leave_days,
    #             leave.employee_id
    #         FROM
    #             (   select * FROM hr_leave_type WHERE code = 'CONG' ) type
    #             LEFT JOIN hr_leave leave ON (leave.holiday_status_id = type.id AND request_date_from >= %(date_from)s
    #             AND request_date_from <= %(date_to)s AND leave.employee_id = %(employee_id)s AND leave.state = 'validate')
    #         GROUP BY
    #             type.name,
    #             leave.employee_id
    #     """
    #
    #     _params = {
    #         'employee_id': self.id,
    #         'date_from': date_from,
    #         'date_to': date_to
    #     }
    #
    #     self.env.cr.execute(_query, _params)
    #     result = self.env.cr.dictfetchone()
    #     if result:
    #         return result.get('leave_days') or 0
    #     return 0
    #
    # leave_acquired_this_year = fields.Float("Congés acquis sur l'année", compute="_getAllInfosLeave")
    # holidays_legal_leaves = fields.Float(compute='_compute_remaining_leaves_legals', string='Congés légaux restants')
    # current_leave_state = fields.Selection(compute='_compute_leave_status', string="Current Leave Status",
    #                                        selection_add=[('technical', 'Technical'), ('not_technical', 'No Technical'),
    #                                                       ('chef_service', 'Chef de service'),
    #                                                       ('crh', 'Chargé des RH'),
    #                                                       ('chef_depart', 'Chef de departement'), ('cdaf', 'RAF'), ])
