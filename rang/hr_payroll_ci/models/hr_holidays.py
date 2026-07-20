#-*- coding:utf-8 -*-

from odoo import fields, models, api
from collections import namedtuple
from datetime import datetime

class hr_holidays(models.Model):
    _inherit= 'hr.leave'

    conge_non_exceptionne = fields.Boolean('Congé non exceptionnel')
    montant_conge = fields.Float('Montant')
    motif_conge = fields.Char('Motif de la demande')

    # @api.model
    # def computeHoldaysByType(self,date_from, date_to, contract):
    #     res = []
    #     Range = namedtuple('Range',['start','end'])
    #     hstatus = self.env['hr.leave.type'].search([])
    #     r1=Range(start=date_from,end=date_to)
    #     self._cr.execute("SELECT id FROM hr_leave WHERE ((date_from"
    #                    " between to_date(%s,'yyyy-mm-dd') AND to_date(%s,'yyyy-mm-dd')) OR (date_to"
    #                    " between to_date(%s,'yyyy-mm-dd') AND to_date(%s,'yyyy-mm-dd')))"
    #                    " AND state='validate' AND type='remove'",(str(date_from),str(date_to), str(date_from), str(date_to)))
    #     holidays_ids = [x[0] for x in self._cr.fetchall()]
    #     if holidays_ids :
    #         holidays = self.browse(holidays_ids)
    #         #print holidays
    #         for status in hstatus:
    #             days = 0
    #             temp = holidays.filtered(lambda r: r.holiday_status_id == status)
    #             for tp in temp:
    #                 #print tp.date_from
    #                 old_date_from = datetime.strptime(tp.date_from[:10], '%Y-%m-%d')
    #                 old_date_to = datetime.strptime(tp.date_to[:10], '%Y-%m-%d')
    #                 r2 = Range(start=old_date_from, end=old_date_to)
    #                 result = (min(r1.end, r2.end) - max(r1.start, r2.start)).days + 1
    #                 if result > 0:
    #                     days += result
    #             if days != 0:
    #                 vals = {
    #                     'name': status.name,
    #                     'sequence': 5,
    #                     'code': status.code,
    #                     'number_of_days': days,
    #                     'number_of_hours': days * 8,
    #                     'contract_id': contract.id,
    #
    #                 }
    #                 res += [vals]
    #         #print res
    #     return res
    #         # print holidays
    #     # print holidays_ids
    #
    # def getHolidays(self, date_from, date_to, employee_id):
    #     res = []
    #     self._cr.execute("SELECT sum(number_of_days), holiday_status_id, subtract_worked_days FROM hr_leave WHERE (date_payment"
    #                      " between to_date(%s,'yyyy-mm-dd') AND to_date(%s,'yyyy-mm-dd'))"
    #                      " AND state='validate' AND payslip_status = True AND employee_id = %s AND subtract_worked_days = True "
    #                      "GROUP BY holiday_status_id, subtract_worked_days",
    #                      (str(date_from), str(date_to), employee_id))
    #     holidays = self._cr.dictfetchall()
    #     print(holidays)
    #     if holidays:
    #         for holiday in holidays:
    #             type_holiday = self.env['hr.leave.type'].browse(holiday['holiday_status_id'])
    #             if type_holiday:
    #                 val = {
    #                     'name' : type_holiday.name,
    #                     'code' : type_holiday.code,
    #                     'number_of_days' : holiday['sum'],
    #                     'number_of_hours' : holiday['sum'] * 8,
    #                 }
    #                 res.append(val)
    #     return res



__author__ = 'lekaizen'
