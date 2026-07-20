# -*- coding:utf-8 -*-
import logging

from odoo import models, api, fields, exceptions, _
from dateutil.relativedelta import relativedelta
from collections import namedtuple
from datetime import datetime

from odoo.exceptions import UserError
from odoo.tools import float_round

_logger = logging.getLogger(__name__)

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    debut_rupture = fields.Date('Date rupture')
    debut_decompte = fields.Date('Début décompte')
    is_retraite = fields.Boolean('Retraité')
    is_deces = fields.Boolean('Décès')
    indemnite_licencement = fields.Float(store=True, readonly=True, string='Indemnité licencement',compute='_get_indemnite_licencement')
    indemnite_retraite = fields.Float(string='Indemnité retraite', store=True, readonly=True, compute='_get_indemnite_licencement')
    indemnite_deces = fields.Float(string='Indemnite décès', store=True, readonly=True, compute='_get_indemnite_deces')
    nombre_jour_attribue = fields.Float(store=True, readonly=True, compute='_compute_number_of_days_allocated', string='Nombre de jour(s) attribué(s)')
    taken_days_number = fields.Float(store=True, readonly=True, compute='_get_taken_days', string='Nombre de jour(s) pris')
    # remaining_leaves = fields.Float(compute='_compute_remaining_leaves', string='Remaining Legal Leaves',
    #                                 inverse='_inverse_remaining_leaves',
    #                                 help='Total number of legal leaves allocated to this employee, change this value to create allocation/leave request. '
    #                                      'Total based on all the leave types without overriding limit.')
    conge_exceptionnel = fields.Float(store=True, readonly=True, compute='_compute_conge_exceptionnel',
                                        string='Nombre Congés Exceptionnels pris')
    conge_non_exceptionnel = fields.Float(store=True, readonly=True, compute='_compute_conge_non_exceptionnel',
                                            string='Nombre Congés Non Exceptionnels pris')
    date_retour_conge = fields.Date(string="Date de rétour congé")
    date_depart_conge = fields.Date(string="Date de départ congé")
    ecart_conge = fields.Float(store=True, readonly=True, compute='_get_taken_days',
                                 digits=(16, 2), string='Ecart de congé')
    ecart_conge2 = fields.Float(digits=(16, 2), string='Ecart de congé')
    montant_moyen_mensuel = fields.Float(store=True, readonly=True, compute='_get_montant_by_periode_reference', digits=(16, 2), string="Montant mensuel moyen")
    montant_moyen_journalier = fields.Float(store=True, readonly=True, compute='_get_montant_moyen_journalier', digits=(16, 2), string="Montant journalier")

    allocation_conge = fields.Float(store=True, readonly=True, compute='_get_allocation_conge',
                                      digits=(16, 2),
                                      string='Allocation congé')
    allocation_conge2 = fields.Float(digits=(16, 2), string='Allocation congé 2')
    montant_alloue = fields.Float(store=True, readonly=True, compute='_get_taken_days', digits=(16, 2),string='Montant congé payé')
    jour_conge = fields.Float(store=True, readonly=True, compute='_get_jour_conge', string='Jour congé')
    conge_paye = fields.Boolean('Congé payé')
    indemnite_fin_cdd = fields.Float(string='Indemnite fin CDD', store=True, readonly=True,
                                       compute='_get_indemnite_fin_cdd')
    prime_gratification = fields.Float(store=True, readonly=True, compute='_compute_prime_gratification',
                                         digits=(16, 2), string='Prime gratification')
    marital = fields.Selection([
        ('single', 'Célibataire'),
        ('married', 'Marié'),
        ('cohabitant', 'Cohabitant légal'),
        ('widower', 'Veuf(ve)'),
        ('divorced', 'Divorcé(e)')
    ], string='État civil', groups="hr.group_hr_user", default='single', tracking=True)


    def main_function(self):
        _logger.info("Fonction principale pour le calcul des paramètres")
        employee_ids = self.env['hr.employee'].search([])
        for emp in employee_ids:
            emp.compute_all_function(emp)

    def compute_all_function(self, emp):
        _logger.info("Fonction après chaque employé")
        emp._get_allocation_conge()
        emp._compute_number_of_days_allocated()
        emp._compute_conge_exceptionnel()
        emp._compute_conge_non_exceptionnel()
        emp._get_taken_days()
        emp._get_jour_conge()
        emp._get_indemnite_licencement()
        emp._get_indemnite_fin_cdd()
        emp._get_indemnite_deces()
        #emp._get_end_contract()
        #emp._compute_cmu_amount()
        emp._compute_prime_gratification()
        emp._get_montant_by_periode_reference()
        emp._get_montant_moyen_journalier()


    def _compute_remaining_leaves(self):
        remaining = {}
        if self.ids:
            self._compute_number_of_days_allocated()
            self._get_allocation_conge()
            self._compute_number_of_days_allocated()
            self._compute_conge_exceptionnel()
            self._compute_conge_non_exceptionnel()
            self._get_taken_days()
            self._get_jour_conge()
            self._get_indemnite_licencement()
            self._get_indemnite_fin_cdd()
            self._get_indemnite_deces()
            self._compute_prime_gratification()
            self._get_montant_by_periode_reference()
            self._get_montant_moyen_journalier()
            remaining = self._get_remaining_leaves()
            print("remaining", remaining)
        for employee in self:
            value = float_round(remaining.get(employee.id, 0.0), precision_digits=2)
            employee.leaves_count = value
            employee.remaining_leaves = value

    @api.depends('debut_rupture', 'debut_decompte', 'is_retraite', 'is_deces')
    @api.onchange('debut_rupture', 'debut_decompte', 'is_retraite', 'is_deces')
    def _get_indemnite_licencement(self):
        for emp in self:
            if emp.debut_decompte and emp.debut_rupture and not emp.is_retraite:
                payslips = emp.env['hr.payslip'].search([('employee_id', '=', emp.id),('date_from', '>=', emp.debut_decompte),('date_from', '<=', emp.debut_rupture)])
                payslips_number = len(payslips)
                montant_net = 0.0
                for slip in payslips:
                    line_ids = slip.line_ids
                    montant = sum(line.total for line in line_ids if line.code == 'BASE_IMP')
                    montant_net += montant
                SNMM = montant_net / payslips_number if payslips_number else 0
                if emp.contract_id.an_anciennete:
                    year = emp.contract_id.an_anciennete
                    if 0 <= year <= 6:
                        amount = (SNMM * 30) / 100
                        emp.indemnite_licencement = amount
                        emp.write({'indemnite_retraite': 0.0})
                    elif 6 <= year <= 10:
                        emp.indemnite_licencement = ((SNMM * 30) / 100) + ((SNMM * 35) / 100)
                        emp.write({'indemnite_retraite': 0.0})
                    elif 10 < year:
                        emp.indemnite_licencement = ((SNMM * 30) / 100) + ((SNMM * 35) / 100) + ((SNMM * 40) / 100)
                        emp.write({'indemnite_retraite': 0.0})
            if emp.debut_decompte and emp.debut_rupture and emp.is_retraite:
                payslips = emp.env['hr.payslip'].search([('employee_id', '=', emp.id),('date_from', '>=', emp.debut_decompte),('date_from', '<=', emp.debut_rupture)])
                payslips_number = len(payslips)
                montant_net = 0
                for slip in payslips:
                    line_ids = slip.line_ids
                    montant = sum(line.total for line in line_ids if line.code == 'BASE_IMP')
                    montant_net += montant
                SNMM = montant_net / payslips_number if payslips_number else 0
                if emp.contract_id.an_anciennete:
                    year = emp.contract_id.an_anciennete
                    if 0 <= year <= 6:
                        emp.indemnite_retraite = (SNMM * 30) / 100
                        emp.write({'indemnite_licencement': 0.0})
                    elif 6 <= year <= 10:
                        emp.indemnite_retraite = ((SNMM * 30) / 100) + ((SNMM * 35) / 100)
                        emp.write({'indemnite_licencement': 0.0})
                    elif 10 < year:
                        emp.indemnite_retraite = ((SNMM * 30) / 100) + ((SNMM * 35) / 100) + ((SNMM * 40) / 100)
                        emp.write({'indemnite_licencement': 0.0})
            if not emp.debut_decompte and not emp.debut_rupture and not emp.is_retraite:
                emp.indemnite_licencement = 0
                emp.indemnite_retraite = 0

    @api.depends('contract_id', 'is_deces')
    @api.onchange('is_deces')
    def _get_indemnite_deces(self):
        for emp in self:
            #emp_id = emp.ids[0]
            #employee = emp.env['hr.employee'].search([('id', '=', emp.id)])
            #print(employee)
            if emp.contract_id.an_anciennete and emp.is_deces:
                year = emp.contract_id.an_anciennete
                wage = emp.contract_id.wage
                if 0 <= year <= 6:
                    emp.indemnite_deces = wage * 3
                elif 6 <= year <= 10:
                    emp.indemnite_deces = (wage * 4) + (wage * 3)
                elif 10 < year:
                    emp.indemnite_deces = (wage * 6) + (wage * 4) + (wage * 3)
            if emp.contract_id.an_anciennete and not emp.is_deces:
                emp.indemnite_deces = 0
            if not emp.contract_id.an_anciennete and not emp.is_deces:
                emp.indemnite_deces = 0
            if not emp.contract_id.an_anciennete and emp.is_deces:
                emp.indemnite_deces = 0

    def _compute_number_of_days_allocated(self):
        for data in self:
            hr_holidays = data.env['hr.leave.allocation'].search([('employee_id', '=', data.ids[0]), ('state', '=', 'validate')]).\
                filtered(lambda r: r.holiday_status_id.code == 'CONG')
            if hr_holidays:
                number_of_days_temp = 0
                for holy in hr_holidays:
                    number_of_days_temp += holy.number_of_days
                data.nombre_jour_attribue = number_of_days_temp
            else:
                data.nombre_jour_attribue = 0

    def _get_taken_days(self):
        for rec in self:
            #employee = rec.env['hr.employee'].search([('id', '=', rec.ids[0])])
            hr_holidays = rec.env['hr.leave'].search([('employee_id', '=', rec.id), ('state', '=', 'validate')]).\
            filtered(lambda r: r.holiday_status_id.code == 'CONG')
            days = rec.conge_exceptionnel
            if hr_holidays:
                number_of_days_temp = 0
                montant_conge = 0
                for holy in hr_holidays:
                    montant_conge += holy.montant_conge
                    number_of_days_temp += holy.number_of_days
                rec.taken_days_number = number_of_days_temp + ((days - 10) if days > 10 else 0)
                rec.montant_alloue = montant_conge
                rec.ecart_conge = rec.allocation_conge - rec.montant_alloue
                ecart_conge2 = rec.allocation_conge - rec.montant_alloue
                rec.write({'ecart_conge2': ecart_conge2})
            else:
                rec.taken_days_number = 0
                rec.montant_alloue = 0
                rec.ecart_conge = 0

    @api.depends("date_retour_conge","debut_rupture")
    @api.onchange("date_retour_conge","debut_rupture")
    def get_montant_moyen_journalier(self):
        slip_obj = self.env['hr.payslip']
        montant = 0
        for emp in self:
            #emp_id = emp.ids[0]
            if emp.contract_id.date_start and not emp.date_retour_conge:
                payslip = slip_obj.search([('employee_id', '=', emp.id), ('date_from', '>=', emp.contract_id.date_start)])
                # payslip = slip_obj.browse(slip_ids)
                if payslip != 0:
                    worked_days_number = list()
                    for slip in payslip:
                        worked_days_line_ids = slip.worked_days_line_ids
                        if worked_days_line_ids:
                            for line in worked_days_line_ids:
                                if 0 < line.number_of_days < 30:
                                    worked_days_number.append(line.number_of_days)
                                if line.number_of_days >= 30:
                                    worked_days_number.append(line.number_of_days)
                    for slip in payslip:
                        for line in slip.line_ids:
                            if line.code == 'BASE_IMP':
                                montant += line.total
                    nwd = sum(worked_days_number)
                    SMJ = round(montant / nwd) if nwd > 0 else 0.0
                    return SMJ
            elif emp.date_retour_conge and emp.contract_id.date_start and not emp.debut_rupture:
                payslips = slip_obj.search([('employee_id', '=', emp.id), ('date_from', '>=', emp.date_retour_conge)])
                payslip = slip_obj.browse(payslips)
                if payslip != 0:
                    worked_days_number = list()
                    for slip in payslip:
                        worked_days_line_ids = slip.worked_days_line_ids
                        if worked_days_line_ids:
                            for line in worked_days_line_ids:
                                if 0 < line.number_of_days < 30:
                                    worked_days_number.append(line.number_of_days)
                                if line.number_of_days >= 30:
                                    worked_days_number.append(line.number_of_days)
                    for slip in payslip:
                        for line in slip.line_ids:
                            if line.code == 'BASE_IMP':
                                montant += line.total
                    nwd = sum(worked_days_number)
                    SMJ = round(montant / nwd) if nwd > 0 else 0.0
                    return SMJ
            elif emp.contract_id.date_start and emp.contract_id.date_end:
                print(emp.date_retour_conge)
                payslips = slip_obj.search([('employee_id', '=', emp.id),
                                                   ('date_from', '>=', emp.contract_id.date_start),
                                                   ('date_from', '<=', emp.contract_id.date_end)])
                payslip = slip_obj.browse(payslips)
                if payslip != 0:
                    worked_days_number = list()
                    for slip in payslip:
                        worked_days_line_ids = slip.worked_days_line_ids
                        if worked_days_line_ids:
                            for line in worked_days_line_ids:
                                if 0 < line.number_of_days < 30:
                                    worked_days_number.append(line.number_of_days)
                                if line.number_of_days >= 30:
                                    worked_days_number.append(line.number_of_days)
                    for slip in payslip:
                        for line in slip.line_ids:
                            if line.code == 'BASE_IMP':
                                montant += line.total
                    nwd = sum(worked_days_number)
                    SMJ = round(montant / nwd) if nwd > 0 else 0.0
                    return SMJ
            elif emp.date_retour_conge and emp.debut_rupture:
                payslips = slip_obj.search([('employee_id', '=', emp.id),
                                                    ('date_from', '>=', emp.date_retour_conge),
                                                    ('date_from', '<=', emp.debut_rupture)])
                # payslip = slip_obj.browse(payslips)
                if payslips != 0:
                    worked_days_number = list()
                    for slip in payslips:
                        worked_days_line_ids = slip.worked_days_line_ids
                        if worked_days_line_ids:
                            for line in worked_days_line_ids:
                                if 0 < line.number_of_days < 30:
                                    worked_days_number.append(line.number_of_days)
                                if line.number_of_days >= 30:
                                    worked_days_number.append(line.number_of_days)
                    for slip in payslips:
                        for line in slip.line_ids:
                            if line.code == 'BASE_IMP':
                                montant += line.total
                    nwd = sum(worked_days_number)
                    SMJ = round(montant / nwd) if nwd > 0 else 0.0
                    return SMJ

    def _get_montant_moyen_journalier(self):
        res = 0
        for emp in self:
            res = emp.get_montant_moyen_journalier()
            emp.montant_moyen_journalier = res
        return res

    def _get_jour_conge(self):
        for emp in self:
            #emp_id = emp.ids[0]
            if emp.contract_id.date_start and not emp.date_retour_conge:
                payslip = self.env['hr.payslip'].search([('employee_id', '=', emp.id), ('date_from', '>=', emp.contract_id.date_start)])
                worked_days_number = list()
                if payslip:
                    print('ok for payslip')
                    for slip in payslip:
                        worked_days_line_ids = slip.worked_days_line_ids
                        if worked_days_line_ids:
                            for line in worked_days_line_ids:
                                if 0 < line.number_of_days < 30:
                                    worked_days_number.append(line.number_of_days)
                                if line.number_of_days >= 30:
                                    worked_days_number.append(line.number_of_days)
                    nwd = sum(worked_days_number)
                    jc = len(payslip) * 2.2
                    emp.jour_conge = jc / nwd if nwd else 0
                    print(emp.jour_conge)
            elif emp.date_retour_conge and emp.contract_id.date_start:
                payslip = self.env['hr.payslip'].search([('employee_id', '=', emp.id), ('date_from', '>=', emp.date_retour_conge)])
                worked_days_number = list()
                if payslip:
                    for slip in payslip:
                        worked_days_line_ids = slip.worked_days_line_ids
                        if worked_days_line_ids:
                            for line in worked_days_line_ids:
                                if 0 < line.number_of_days < 30:
                                    worked_days_number.append(line.number_of_days)
                                if line.number_of_days >= 30:
                                    worked_days_number.append(line.number_of_days)
                    nwd = sum(worked_days_number)
                    jc = len(payslip) * 2.2
                    emp.jour_conge = jc / nwd if nwd else 0

    def _get_allocation_conge(self):
        for emp in self:
            smm = emp.env['hr.employee'].search([('id', '=', emp.id)]).montant_moyen_mensuel
            jc = emp.env['hr.employee'].search([('id', '=', emp.id)]).jour_conge
            #employee = emp.env['hr.employee'].search([('id', '=', emp.id)])
            if emp.contract_id.date_start and not emp.date_retour_conge:
                emp.allocation_conge = round(smm * jc * 1.25)
                allocation_conge = round(smm * jc * 1.25)
                emp.write({'allocation_conge2': allocation_conge})
            elif emp.date_retour_conge and emp.contract_id.date_start and not emp.debut_rupture:
                emp.allocation_conge = round(smm * jc * 1.25)
                allocation_conge = round(smm * jc * 1.25)
                emp.write({'allocation_conge2': allocation_conge})

    def _compute_conge_exceptionnel(self):
        for rec in self:
            hr_holidays = rec.env['hr.leave'].search([('employee_id', '=', rec.id), ('state', '=', 'validate'),
                                                         ('conge_non_exceptionne', '=', False)]).filtered(
                lambda r: r.holiday_status_id.code != 'CONG')
            if hr_holidays:
                days = 0
                for holy in hr_holidays:
                    days += holy.number_of_days
                rec.conge_exceptionnel = days
            else:
                rec.conge_exceptionnel = 0

    def _compute_conge_non_exceptionnel(self):
        for rec in self:
            hr_holidays = rec.env['hr.leave'].search(
                [('employee_id', '=', rec.ids[0]), ('state', '=', 'validate'), ('conge_non_exceptionne', '=', True)]).filtered(
                lambda r: r.holiday_status_id.code == 'CONG_NON_EXCEPTIONNEL')
            if hr_holidays:
                days = 0
                for holy in hr_holidays:
                    days += holy.number_of_days
                rec.conge_non_exceptionnel = days
            else:
                rec.conge_non_exceptionnel = 0

    def get_montant_by_periode_reference(self):
        slip_obj = self.env['hr.payslip']
        montant = 0
        for emp in self:
            if emp.contract_id.date_start and not emp.date_retour_conge:
                payslip = slip_obj.search([('employee_id', '=', emp.id), ('date_from', '>=', emp.contract_id.date_start)])
                number = len(payslip)
                print(number)
                if payslip != 0:
                    for slip in payslip:
                        for line in slip.line_ids:
                            if line.code == 'BASE_IMP':
                                montant += line.total
                    SMM = round(montant)
                    return SMM
            elif emp.date_retour_conge and emp.contract_id.date_start and not emp.debut_rupture:
                print(emp.date_retour_conge)
                payslips = slip_obj.search([('employee_id', '=', emp.id), ('date_from', '>=', emp.date_retour_conge)])
                payslip = slip_obj.browse(payslips)
                number = len(payslip)
                if payslip != 0:
                    for slip in payslip:
                        for line in slip.line_ids:
                            if line.code == 'BASE_IMP':
                                montant += line.total
                    SMM = round(montant)
                    return SMM
            elif emp.contract_id.date_start and emp.contract_id.date_end:
                print(emp.date_retour_conge)
                payslips = slip_obj.search([('employee_id', '=', emp.id),
                                                   ('date_from', '>=', emp.contract_id.date_start),
                                                   ('date_from', '<=', emp.contract_id.date_end)])
                payslip = slip_obj.browse(payslips)
                number = len(payslip)
                if payslip != 0:
                    for slip in payslip:
                        for line in slip.line_ids:
                            if line.code == 'BASE_IMP':
                                montant += line.total
                    SMM = round(montant)
                    return SMM
            elif emp.date_retour_conge and emp.debut_rupture:
                payslips = slip_obj.search([('employee_id', '=', emp.id),
                                                    ('date_from', '>=', emp.date_retour_conge),
                                                    ('date_from', '<=', emp.debut_rupture)])
                payslip = slip_obj.browse(payslips)
                if payslip != 0:
                    for slip in payslip:
                        for line in slip.line_ids:
                            if line.code == 'BASE_IMP':
                                montant += line.total
                    SMM = round(montant)
                    return SMM

    def _get_montant_by_periode_reference(self):
        for emp in self:
            res = emp.get_montant_by_periode_reference()
            emp.montant_moyen_mensuel = res
            return res

    def _get_indemnite_fin_cdd(self):
        montant = 0
        for emp in self:
            #emp_id = emp.ids[0]
            employee = emp.env['hr.employee'].search([('id', '=', emp.id)])
            if emp.contract_id.date_start and emp.contract_id.date_end:
                smm = emp.env['hr.employee'].search([('id', '=', employee.id)]).montant_moyen_mensuel
                payslip = emp.env['hr.payslip'].search([('employee_id', '=', emp.id),
                                                        ('date_from', '>=', emp.contract_id.date_start),
                                                        ('date_from', '<=', emp.contract_id.date_end)
                                                        ])
                if payslip != 0:
                    for slip in payslip:
                        for line in slip.line_ids:
                            if line.code == 'BASE_IMP':
                                montant += line.total
                    if montant:
                        indemnite_fin_cdd2 = round(montant * 3) / 100
                        emp.indemnite_fin_cdd = round(montant * 3) / 100
                        _logger.info("Indemnité fin cdd %s", indemnite_fin_cdd2)
                        #employee.write({'indemnite_fin_cdd2': indemnite_fin_cdd2})
            if emp.contract_id.date_start and not emp.contract_id.date_end:
                emp.indemnite_fin_cdd = 0
            if not emp.contract_id.date_start and not emp.contract_id.date_end:
                emp.indemnite_fin_cdd = 0

    def _compute_prime_gratification(self):
        for rec in self:
            emp_id = rec.ids[0]
            employee = rec.env['hr.employee'].search([('id', '=', emp_id)])
            #res = float(rec.contract_id.taux)
            t = 75 / 100
            if rec.contract_id.date_start and rec.contract_id.date_end:
                payslip = rec.env['hr.payslip'].search([('employee_id', '=', rec.id),
                                                        ('date_from', '>=', rec.contract_id.date_start),
                                                        ('date_from', '<=', rec.contract_id.date_end)])
                if payslip != 0:
                    worked_days_number = list()
                    for slip in payslip:
                        worked_days_line_ids = slip.worked_days_line_ids
                        if worked_days_line_ids:
                            for line in worked_days_line_ids:
                                if 0 < line.number_of_days < 30:
                                    worked_days_number.append(line.number_of_days)
                                if line.number_of_days >= 30:
                                    worked_days_number.append(line.number_of_days)
                    nwd = sum(worked_days_number)
                    rec.prime_gratification = t * nwd / 360
                    prime = t * nwd / 360
                    employee.write({'prime_gratification': prime})
            if rec.contract_id.date_start and not rec.contract_id.date_end:
                payslip = rec.env['hr.payslip'].search([('employee_id', '=', rec.id),
                                                        ('date_from', '>=', rec.contract_id.date_start)])
                if payslip != 0:
                    worked_days_number = list()
                    for slip in payslip:
                        worked_days_line_ids = slip.worked_days_line_ids
                        if worked_days_line_ids:
                            for line in worked_days_line_ids:
                                if 0 < line.number_of_days < 30:
                                    worked_days_number.append(line.number_of_days)
                                if line.number_of_days >= 30:
                                    worked_days_number.append(line.number_of_days)
                    nwd = sum(worked_days_number)
                    rec.prime_gratification = t * nwd / 360
                    prime = t * nwd / 360
                    employee.write({'prime_gratification': prime})
