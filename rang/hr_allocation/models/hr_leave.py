# -*- coding:utf-8 -*-
import logging

from odoo import models, api, fields, exceptions, _
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    @api.model
    def _default_holiday_status_id(self):
        return self.env.ref('hr_holidays.holiday_status_cl')

    # holiday_status_id = fields.Many2one(
    #     "hr.leave.type", compute='_compute_from_employee_id', store=True, string="Time Off Type", required=True,
    #     readonly=False, states={'cancel': [('readonly', True)], 'refuse': [('readonly', True)], 'validate1': [('readonly', True)],
    #                             'validate': [('readonly', True)]},
    #     default=_default_holiday_status_id, domain="[('company_id', '?=', employee_company_id), '|', ('requires_allocation', '=', 'no'), ('has_valid_allocation', '=', True)]")
    first_holiday = fields.Selection([('no', 'Non'), ('yes', 'Oui')], default="no", string="Premier congé ?")
    date_retour_conge = fields.Date(string="Date rétour congé")
    date_retour_conge_pre = fields.Date(string="Date rétour congé précédent", store=True,
                                        compute="_get_employee_date_retour_conge")
    code_conge = fields.Char(string="Code", store=True, compute="_get_default_code")
    nombre_mois_smj = fields.Integer("SMJ sur combien de mois ?")
    smj = fields.Float("Salaire moyen Journalier", store=True, compute="_get_smj_allocation")
    allocation_conge = fields.Float("Allocation congé", store=True, compute="_get_smj_allocation")
    #date_reference = fields.Date(string="Période de référence")

    @api.depends("employee_id")
    @api.onchange("employee_id")
    def _get_employee_date_retour_conge(self):
        for rec in self:
            if rec.employee_id:
                rec.date_retour_conge_pre = rec.employee_id.date_retour_conge

    @api.depends("holiday_status_id")
    @api.onchange("holiday_status_id")
    def _get_default_code(self):
        for rec in self:
            if rec.holiday_status_id:
                rec.code_conge = rec.holiday_status_id.code

    @api.depends("employee_id")
    @api.onchange("employee_id")
    def _get_default_value(self):
        for rec in self:
            leave_ids = self.env['hr.leave'].search([('employee_id', '=', rec.employee_id.id)])
            if len(leave_ids) > 0:
                rec.first_holiday = "no"
            else:
                rec.first_holiday = "yes"

    @api.depends("employee_id", "nombre_mois_smj", "payroll_date", "date_retour_conge_pre")
    @api.onchange("employee_id", "nombre_mois_smj", "payroll_date", "date_retour_conge_pre")
    def _get_smj_allocation(self):
        slip_obj = self.env['hr.payslip']
        for rec in self:
            if rec.holiday_status_id.code == 'CONG':
                if rec.first_holiday == 'yes':
                    payslip_ids = slip_obj.search([('employee_id', '=', rec.employee_id.id), ('date_from', '<', rec.payroll_date)], limit=rec.nombre_mois_smj)
                    # payslip = payslip_ids[:-rec.nombre_mois_smj]
                    payslip = payslip_ids
                    if payslip != 0:
                        # Calcul du Salaire moyen journalier
                        line_ids = payslip.mapped('line_ids')
                        montant = sum(line.total for line in line_ids if line.code == 'BASE_IMP')
                        work_days = len(payslip) * 30
                        SMJ = montant / work_days if work_days > 0 else 0.0
                        SMJ2 = round(SMJ)
                        # Calcul du montant du congé payé
                        if SMJ2:
                            rec.smj = SMJ2
                            rec.allocation_conge = SMJ2 * rec.number_of_days_display
                    else:
                        rec.smj = 0
                        rec.allocation_conge = 0
                        # return SMJ2
                if rec.first_holiday == 'no':
                    # Date retour congé précedent
                    date_retour_conge_pre = rec.date_retour_conge_pre
                    date = fields.Date.from_string(date_retour_conge_pre)
                    # Début du mois
                    debut_mois = date.replace(day=1)
                    # Si tu veux le remettre au format Odoo (string ISO)
                    date_retour_conge = fields.Date.to_string(debut_mois)
                    # Date de paie
                    payroll_date = rec.payroll_date
                    date2 = fields.Date.from_string(payroll_date)
                    debut_mois2 = date2.replace(day=1)
                    date_paie = fields.Date.to_string(debut_mois2)
                    payslip = slip_obj.search([
                        ('employee_id', '=', rec.employee_id.id),
                        ('date_from', '>=', date_retour_conge),  # Prendre la date de 1er du mois à partir de la date de retour de congé
                        ('date_from', '<', date_paie)
                    ])
                    print("date_retour_conge", date_retour_conge, "date_paie", date_paie)
                    print("payslip", payslip)
                    if payslip != 0:
                        # Calcul du Salaire moyen journalier
                        line_ids = payslip.mapped('line_ids')
                        # if 100 <= nombre <= 299:
                        montant = sum(line.total for line in line_ids if line.code == 'BASE_IMP')
                        # montant = sum(line.total for line in line_ids if line.code != 'BASE_IMP' and 100 <= line.sequence <= 299)
                        print('montant', montant)
                        work_days = len(payslip) * 30
                        SMJ = montant / work_days if work_days > 0 else 0.0
                        SMJ2 = round(SMJ)
                        # Calcul du montant du congé payé
                        if SMJ2:
                            rec.smj = SMJ2
                            rec.allocation_conge = SMJ2 * rec.number_of_days_display
                        else:
                            rec.smj = 0
                            rec.allocation_conge = 0

    def get_allocation_conge(self):
        for rec in self:
            # SMJ2 = rec.get_smj_allocation()
            if rec.smj:
                SMJ2 = rec.smj
                if rec.first_holiday == 'yes':
                    conge_paye = SMJ2 * rec.number_of_days
                    rec.env['hr.employee'].search([('id', '=', rec.employee_id.id)]).write({
                        "date_retour_conge": rec.date_retour_conge
                    })
                    historique = rec.env['historique.retour_conge'].search(
                        [('leave_id', '=', rec.id), ('employee_id', '=', rec.employee_id.id)])
                    if historique:
                        data = {
                            "employee_id": rec.employee_id.id,
                            "leave_id": rec.id,
                            "request_date_from": rec.request_date_from,
                            "request_date_to": rec.request_date_to,
                            "number_of_days_display": rec.number_of_days_display,
                            "payroll_date": rec.payroll_date,
                            "date_retour_conge": rec.date_retour_conge,
                            "allocation_conge": conge_paye,
                            "nombre_mois_smj": rec.nombre_mois_smj,
                            "smj": SMJ2,
                        }
                        historique.write(data)
                    else:
                        data = {
                            "employee_id": rec.employee_id.id,
                            "leave_id": rec.id,
                            "request_date_from": rec.request_date_from,
                            "request_date_to": rec.request_date_to,
                            "number_of_days_display": rec.number_of_days_display,
                            "payroll_date": rec.payroll_date,
                            "date_retour_conge": rec.date_retour_conge,
                            "allocation_conge": conge_paye,
                            "nombre_mois_smj": rec.nombre_mois_smj,
                            "smj": SMJ2,
                        }
                        rec.env['historique.retour_conge'].create(data)
                if rec.first_holiday == 'no':
                    conge_paye = SMJ2 * rec.number_of_days
                    historique = rec.env['historique.retour_conge'].search(
                        [('leave_id', '=', rec.id), ('employee_id', '=', rec.employee_id.id)])
                    if historique:
                        data = {
                            "employee_id": rec.employee_id.id,
                            "leave_id": rec.id,
                            "request_date_from": rec.request_date_from,
                            "request_date_to": rec.request_date_to,
                            "number_of_days_display": rec.number_of_days_display,
                            "payroll_date": rec.payroll_date,
                            "date_retour_conge": rec.date_retour_conge,
                            "allocation_conge": conge_paye,
                            "nombre_mois_smj": rec.nombre_mois_smj,
                            "smj": SMJ2,
                        }
                        print(data)
                        historique.write(data)
                        rec.env['hr.employee'].search([('id', '=', rec.employee_id.id)]).write({
                            "date_retour_conge": rec.date_retour_conge
                        })
                    else:
                        data = {
                            "employee_id": rec.employee_id.id,
                            "leave_id": rec.id,
                            "request_date_from": rec.request_date_from,
                            "request_date_to": rec.request_date_to,
                            "number_of_days_display": rec.number_of_days_display,
                            "payroll_date": rec.payroll_date,
                            "date_retour_conge": rec.date_retour_conge,
                            "allocation_conge": conge_paye,
                            "nombre_mois_smj": rec.nombre_mois_smj,
                            "smj": SMJ2,
                        }
                        print(data)
                        rec.env['historique.retour_conge'].create(data)
                        rec.env['hr.employee'].search([('id', '=', rec.employee_id.id)]).write({
                            "date_retour_conge": rec.date_retour_conge
                        })

    def action_validate(self):
        if self.holiday_status_id.code == 'CONG':
            if self.date_retour_conge:
                if self.date_retour_conge < self.request_date_to:
                    raise ValidationError(_("La date retour doit être supérieur ou égale la date de fin de congé !"))
            self.get_allocation_conge()
        else:
            if self.number_of_days_display > self.holiday_status_id.number_of_days:
                raise ValidationError(_("Le nombre de jour de ce congé est fixé à %s jour(s)") % (self.holiday_status_id.number_of_days))
        current_employee = self.env.user.employee_id
        leaves = self._get_leaves_on_public_holiday()
        if leaves:
            raise ValidationError(_('The following employees are not supposed to work during that period:\n %s') % ','.join(leaves.mapped('employee_id.name')))

        if any(holiday.state not in ['confirm', 'validate1'] and holiday.validation_type != 'no_validation' for holiday in self):
            raise UserError(_('Time off request must be confirmed in order to approve it.'))

        self.write({'state': 'validate'})

        leaves_second_approver = self.env['hr.leave']
        leaves_first_approver = self.env['hr.leave']

        for leave in self:
            if leave.validation_type == 'both':
                leaves_second_approver += leave
            else:
                leaves_first_approver += leave

            if leave.holiday_type != 'employee' or\
                (leave.holiday_type == 'employee' and len(leave.employee_ids) > 1):
                if leave.holiday_type == 'employee':
                    employees = leave.employee_ids
                elif leave.holiday_type == 'category':
                    employees = leave.category_id.employee_ids
                elif leave.holiday_type == 'company':
                    employees = self.env['hr.employee'].search([('company_id', '=', leave.mode_company_id.id)])
                else:
                    employees = leave.department_id.member_ids

                conflicting_leaves = self.env['hr.leave'].with_context(
                    tracking_disable=True,
                    mail_activity_automation_skip=True,
                    leave_fast_create=True
                ).search([
                    ('date_from', '<=', leave.date_to),
                    ('date_to', '>', leave.date_from),
                    ('state', 'not in', ['cancel', 'refuse']),
                    ('holiday_type', '=', 'employee'),
                    ('employee_id', 'in', employees.ids)])

                if conflicting_leaves:
                    # YTI: More complex use cases could be managed in master
                    if leave.leave_type_request_unit != 'day' or any(l.leave_type_request_unit == 'hour' for l in conflicting_leaves):
                        raise ValidationError(_('You can not have 2 time off that overlaps on the same day.'))

                    # keep track of conflicting leaves states before refusal
                    target_states = {l.id: l.state for l in conflicting_leaves}
                    conflicting_leaves.action_refuse()
                    split_leaves_vals = []
                    for conflicting_leave in conflicting_leaves:
                        if conflicting_leave.leave_type_request_unit == 'half_day' and conflicting_leave.request_unit_half:
                            continue

                        # Leaves in days
                        if conflicting_leave.date_from < leave.date_from:
                            before_leave_vals = conflicting_leave.copy_data({
                                'date_from': conflicting_leave.date_from.date(),
                                'date_to': leave.date_from.date() + timedelta(days=-1),
                                'state': target_states[conflicting_leave.id],
                            })[0]
                            before_leave = self.env['hr.leave'].new(before_leave_vals)
                            before_leave._compute_date_from_to()

                            # Could happen for part-time contract, that time off is not necessary
                            # anymore.
                            # Imagine you work on monday-wednesday-friday only.
                            # You take a time off on friday.
                            # We create a company time off on friday.
                            # By looking at the last attendance before the company time off
                            # start date to compute the date_to, you would have a date_from > date_to.
                            # Just don't create the leave at that time. That's the reason why we use
                            # new instead of create. As the leave is not actually created yet, the sql
                            # constraint didn't check date_from < date_to yet.
                            if before_leave.date_from < before_leave.date_to:
                                split_leaves_vals.append(before_leave._convert_to_write(before_leave._cache))
                        if conflicting_leave.date_to > leave.date_to:
                            after_leave_vals = conflicting_leave.copy_data({
                                'date_from': leave.date_to.date() + timedelta(days=1),
                                'date_to': conflicting_leave.date_to.date(),
                                'state': target_states[conflicting_leave.id],
                            })[0]
                            after_leave = self.env['hr.leave'].new(after_leave_vals)
                            after_leave._compute_date_from_to()
                            # Could happen for part-time contract, that time off is not necessary
                            # anymore.
                            if after_leave.date_from < after_leave.date_to:
                                split_leaves_vals.append(after_leave._convert_to_write(after_leave._cache))

                    split_leaves = self.env['hr.leave'].with_context(
                        tracking_disable=True,
                        mail_activity_automation_skip=True,
                        leave_fast_create=True,
                        leave_skip_state_check=True
                    ).create(split_leaves_vals)

                    split_leaves.filtered(lambda l: l.state in 'validate')._validate_leave_request()

                values = leave._prepare_employees_holiday_values(employees)
                leaves = self.env['hr.leave'].with_context(
                    tracking_disable=True,
                    mail_activity_automation_skip=True,
                    leave_fast_create=True,
                    no_calendar_sync=True,
                    leave_skip_state_check=True,
                    # date_from and date_to are computed based on the employee tz
                    # If _compute_date_from_to is used instead, it will trigger _compute_number_of_days
                    # and create a conflict on the number of days calculation between the different leaves
                    leave_compute_date_from_to=True,
                ).create(values)

                leaves._validate_leave_request()

        leaves_second_approver.write({'second_approver_id': current_employee.id})
        leaves_first_approver.write({'first_approver_id': current_employee.id})

        employee_requests = self.filtered(lambda hol: hol.holiday_type == 'employee')
        employee_requests._validate_leave_request()
        if not self.env.context.get('leave_fast_create'):
            employee_requests.filtered(lambda holiday: holiday.validation_type != 'no_validation').activity_update()
        return True

