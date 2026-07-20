#-*- coding:utf-8 -*-

from odoo import fields, models, api
from collections import namedtuple
from calendar import monthrange
from datetime import datetime


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    def createHolidays(self, employee_id, number_of_days):
        type= self.env['hr.leave.status'].search([('code', '=', 'CONG')], limit=1)
        if type:
            vals = {
                'holidays_type': 'employee',
                'employee_id': employee_id,
                'holidays_status_id': type.id,
                'number_of_days_temps': number_of_days,
            }
            self.create(vals)

    @api.model
    def computeHoldaysByType(self,date_from, date_to, contract, employee_id):
        res = []
        Range = namedtuple('Range',['start','end'])
        hstatus = self.env['hr.holidays.status'].search([])
        r1=Range(start=date_from,end=date_to)
        self._cr.execute("SELECT id FROM hr_holidays WHERE ((date_from"
                       " between to_date(%s,'yyyy-mm-dd') AND to_date(%s,'yyyy-mm-dd')) OR (date_to"
                       " between to_date(%s,'yyyy-mm-dd') AND to_date(%s,'yyyy-mm-dd')))"
                       " AND state='validate' AND payslip_status = TRUE  AND type='remove' AND employee_id='%s'",(str(date_from),str(date_to),
                           str(date_from), str(date_to), employee_id))
        holidays_ids = [x[0] for x in self._cr.fetchall()]
        if holidays_ids :
            holidays = self.browse(holidays_ids)
            print(holidays)
            for status in hstatus:
                days = 0
                temp = holidays.filtered(lambda r: r.holiday_status_id == status)
                for tp in temp :
                    print(tp.date_from)
                    old_date_from=datetime.strptime(tp.date_from[:10],'%Y-%m-%d')
                    old_date_to = datetime.strptime(tp.date_to[:10],'%Y-%m-%d')
                    r2=Range(start=old_date_from,end=old_date_to)
                    result = (min(r1.end, r2.end)  - max(r1.start,r2.start)).days + 1
                    if result > 0:
                        days+= result
                if days != 0 :
                    nb_days = monthrange(date_from.year, date_from.month)
                    if days == nb_days[1] :
                        days = 30
                    hours = days * 173.33/30
                    vals = {
                        'name': status.name,
                        'sequence': 5,
                        'code': status.code,
                        'number_of_days': days,
                        'number_of_hours': hours,
                        'contract_id': contract.id,

                    }
                    res += [vals]
        return res

    code = fields.Char('Code',required=False)
    company_id = fields.Many2one('res.company', "Société", related='employee_id.company_id')
    payroll_date = fields.Date("Date de paie")
    code_conge = fields.Char(string="Code", store=True, compute="_get_default_code")

    @api.depends("holiday_status_id")
    @api.onchange("holiday_status_id")
    def _get_default_code(self):
        for rec in self:
            if rec.holiday_status_id:
                rec.code_conge = rec.holiday_status_id.code


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    code = fields.Char('Code', required=False)
    number_of_days = fields.Integer('Nombre de jours autorisés', default=0)
    is_calendar = fields.Boolean("Basé sur les jours calendaires", default=False)


class HrLeaveAllocation(models.Model):
    _inherit = "hr.leave.allocation"

    company_id = fields.Many2one('res.company', "Société", related='employee_id.company_id')
    date_allocation = fields.Date("Date d'attribution", default=lambda self: fields.Date.today(), required=False)