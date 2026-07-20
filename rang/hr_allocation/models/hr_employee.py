# -*- coding:utf-8 -*-
import logging

from collections import defaultdict
from datetime import datetime, date, time
from dateutil.relativedelta import relativedelta
import pytz

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools import format_date

_logger = logging.getLogger(__name__)
class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'
    _description = 'Generate payslips for all selected employees'

    def _check_undefined_slots(self, work_entries, payslip_run):
        """
        Check if a time slot in the contract's calendar is not covered by a work entry
        """
        work_entries_by_contract = defaultdict(lambda: self.env['hr.work.entry'])
        for work_entry in work_entries:
            work_entries_by_contract[work_entry.contract_id] |= work_entry

        for contract, work_entries in work_entries_by_contract.items():
            if contract.work_entry_source != 'calendar':
                continue
            calendar_start = pytz.utc.localize(datetime.combine(max(contract.date_start, payslip_run.date_start), time.min))
            calendar_end = pytz.utc.localize(datetime.combine(min(contract.date_end or date.max, payslip_run.date_end), time.max))
            outside = contract.resource_calendar_id._attendance_intervals_batch(calendar_start, calendar_end)[False] - work_entries._to_intervals()
            if outside:
                time_intervals_str = "\n - ".join(['', *["%s -> %s" % (s[0], s[1]) for s in outside._items]])
                #raise UserError(_("Some part of %s's calendar is not covered by any work entry. Please complete the schedule. Time intervals to look for:%s") % (contract.employee_id.name, time_intervals_str))

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    date_retour_conge = fields.Date(string="Date rétour congé")
    historique_allocation_line_ids = fields.One2many("historique.retour_conge", "employee_id", "Historique des allocations")


class HrEmployeeRetourConge(models.Model):
    _name = 'historique.retour_conge'

    request_date_from = fields.Date("Date départ congé")
    request_date_to = fields.Date("Date fin congé")
    number_of_days_display = fields.Float("Durée")
    date_retour_conge = fields.Date("Date rétour congé")
    payroll_date = fields.Date("Date de paie")
    allocation_conge = fields.Float("Allocation congé")
    smj = fields.Float("Salaire moyen Journalier")
    nombre_mois_smj = fields.Integer("Nombre de mois")
    leave_id = fields.Many2one("hr.leave")
    employee_id = fields.Many2one("hr.employee")