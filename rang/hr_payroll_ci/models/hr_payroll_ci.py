# -*- encoding: utf-8 -*-

##############################################################################
#
# Copyright (c) 2014 Veone - support.veone.net
# Author: Veone
#
# Fichier du module hr_payroll_ci
# ##############################################################################  -->


from collections import defaultdict
from datetime import datetime, date, time
import pytz

from dateutil import relativedelta

from odoo.tools import format_date

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from odoo.loglevels import get_encodings, ustr, exception_to_unicode     # noqa
from odoo.tools.misc import get_lang


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    def format_amount_separator(self, amount, digits=0, separator=' '):
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

    def getInfosRubrique(self, rubrique, type):
        self.ensure_one()
        # for id in range(len(obj)):
        line = self.line_ids.filtered(lambda l: l.code == rubrique)
        total = 0.0
        if line:
            if type == 'taux':
                total = line.rate
            else:
                total = line.total
        result = self.format_amount_separator(total)
        return result

    def get_somme_rubrique(self, code):
        self.ensure_one()
        first_day = self.date_to.replace(day=1, month=1)
        slips = self.search([('date_from', '>=', first_day), ('date_to', '<=', self.date_to),
                             ('employee_id', '=', self.employee_id.id)])
        print(slips)
        _query = """
                SELECT 
                    sum(l.total) as total
                FROM 

                        (SELECT id FROM hr_employee WHERE (id = %(employee_id)s )) e
                        left join hr_payslip_line l on (l.employee_id = e.id and code = %(code)s and l.slip_id 
                        in (SELECT id FROM hr_payslip WHERE employee_id = %(employee_id)s AND 
                        date_from >= %(date_from)s AND date_to <= %(date_to)s))
                """
        _params = {
            'date_from': first_day,
            'date_to': self.date_to,
            'employee_id': self.employee_id.id,
            'code': code
        }

        self.env.cr.execute(_query, _params)
        result = self.env.cr.dictfetchone()
        if result['total'] is not None:
            return self.format_amount_separator(result['total'])
        return 0

    def getTauxByCode(self, rubrique):
        # for id in range(len(obj)):
        self.ensure_one()
        taux = 0.0
        lines = self.line_ids
        for line in lines:
            if line.code == rubrique:
                #print line.rate
                taux = line.rate
        print("{0:,.2f}".format(taux).replace(".", ","))
        return "{0:,.2f}".format(taux).replace(".", ",")
        #return taux

    # def write(self, vals):
    #     emp_obj = self.env['hr.employee']
    #     trouver = False
    #     for payslip in self:
    #         employee=payslip.employee_id
    #         list_payslips=employee.slip_ids
    #         date_from = fields.Datetime.from_string(payslip.date_from)
    #         date_to = fields.Datetime.from_string(payslip.date_to)
    #         Range = namedtuple('Range',['start','end'])
    #         r1=Range(start=date_from,end=date_to)
    #         new_list=[]
    #         if (len(list_payslips)!=1):
    #             for slip in list_payslips:
    #                 if slip.id != payslip.id :
    #                     new_list.append(slip)
    #             for slip in new_list:
    #                 old_date_from=fields.Datetime.from_string(slip.date_from)
    #                 old_date_to = fields.Datetime.from_string(slip.date_to)
    #                 r2=Range(start=old_date_from,end=old_date_to)
    #                 result = (min(r1.end, r2.end)  - max(r1.start,r2.start)).days + 1
    #         if trouver == True :
    #             raise ValidationError(_("L'employé possède déjà un bulletin pour cette période"))
    #         else :
    #             super(HrPayslip,self).write(vals)
    #     return True

    def _input_lines(self, contract_id, struct_id):
        input_lines = self.input_line_ids.browse([])
        if contract_id and struct_id:
            data_inputs = contract_id.get_inputs_payslip()
            print('data_inputs _input_lines', data_inputs)
            # Ajout de cmu automatiquement dans les inputs start
            # cmu_part = 0
            # for rec in self:
            #     cmu_part = rec.employee_id.cmu_part
            # type_line = self.env['hr.payslip.input.type'].search([('code', '=', 'CMU')], limit=1)
            # if cmu_part:
            #     val = {
            #         'input_type_id': type_line.id,
            #         'amount': cmu_part,
            #         'contract_id': contract_id.id,
            #     }
            #     data_inputs.append(val)
            for r in data_inputs:
                input_lines |= input_lines.new(r)
            if struct_id.input_line_type_ids:
                intups_data = []
                for type in struct_id.input_line_type_ids:
                    val = {
                        'input_type_id': type.id,
                        'amount': 0,
                        'contract_id': contract_id.id,
                        #'struct_id': struct_id.id
                    }
                    intups_data.append(val)
                for r in intups_data:
                    input_lines |= input_lines.new(r)
            return input_lines
        else:
            return [(5, False, False)]

    @api.onchange('employee_id', 'struct_id', 'contract_id', 'date_from', 'date_to')
    def _onchange_employee(self):
        if self.employee_id:
            inputs = self._input_lines(self.contract_id, self.struct_id)
            self.input_line_ids = inputs
        else:
            self.contract_id = False
            self.struct_id = False
            self.name = False
            self.worked_days_line_ids = False
            self.input_line_ids = False

    def _get_worked_day_lines(self):
        """
        :returns: a list of dict containing the worked days values that should be applied for the given payslip
        """
        res = []
        # fill only if the contract as a working schedule linked
        self.ensure_one()
        contract = self.contract_id
        worked_days = 30
        worked_hours = 173.33
        work_entry_type = self.env['hr.work.entry.type'].search([('code', '=', 'WORK100')])
        if work_entry_type:
            attendance_line = {
                'sequence': work_entry_type.sequence,
                'work_entry_type_id': work_entry_type.id,
                'number_of_days': worked_days,
                'number_of_hours': worked_hours,
                'rate': worked_days/30,
                'amount': 0,
            }
            res.append(attendance_line)
        return res

    @api.model
    def get_inputs(self, contracts, date_from, date_to):

        res = super(HrPayslip, self).get_inputs(contracts, date_from, date_to)
        print('res', res)
        for contract in contracts:
            inputs = contract.employee_id.getInputsPayroll(contract, date_from, date_to)
            print(inputs)
            res += inputs
        return res

    @api.depends('contract_id')
    def _get_anciennete(self):
        anciennete = {}
        # print self
        for slip in self:
            end_date = fields.Datetime.from_string(slip.date_to)
            start_date = fields.Datetime.from_string(slip.employee_id.start_date)
            tmp = relativedelta.relativedelta(end_date, start_date)
            print(tmp)

            slip.update({
                'payslip_an_anciennete': tmp.years,
                'payslip_mois_anciennete': tmp.months,
            })

    # def _getCumulOlder(self):
    #     first_date = fields.Date.to_string(self.date_from.replace(day=1, month=1))
        # print(self.employee_id)
        # _query = """
        #     SELECT
        #         e.id as employee,
        #         SUM(plbt.total) as cumul_brut,
        #         SUM(pl_cn.total) as cumul_cn,
        #         SUM(pl_igr.total) as cumul_igr,
        #         SUM(pl_is.total) as cumul_its
        #     FROM
        #         (SELECT * FROM hr_payslip WHERE date_from >= %(date_from)s AND date_to <= %(date_to)s AND employee_id = %(employee_id)s) p
        #             left join hr_employee e on (p.employee_id = e.id)
        #             left join hr_payslip_line plbt on (plbt.slip_id = p.id and  plbt.code = 'BRUT')
        #             left join hr_payslip_line pl_cn on (pl_cn.slip_id = p.id and pl_cn.code = 'CN')
        #             left join hr_payslip_line pl_igr on (pl_igr.slip_id = p.id and pl_igr.code = 'IGR')
        #             left join hr_payslip_line pl_is on (pl_is.slip_id = p.id and pl_is.code = 'ITS')
        #             left join hr_payslip_line pl_wkdays on (pl_wkdays.slip_id = p.id and pl_wkdays.code = 'TWDAYS')
        #     GROUP BY
        #         e.id
        # """
        #
        # _params = {
        #     'employee_id': self.employee_id.id,
        #     'date_from': first_date,
        #     'date_to': self.date_from
        # }
        #
        # self.env.cr.execute(_query, _params)
        # result = self.env.cr.dictfetchone()
        # if result:
        #     print('result', result)
        #     self.cumul_brut = result['cumul_brut']
        #     #return result
        #     return result['cumul_brut']
        # else:
        #     return {}

    def _getCumulOlder(self, code):
        self.ensure_one()
        first_day = self.date_to.replace(day=1, month=1)
        slips = self.search([('date_from', '>=', first_day), ('date_to', '<=', self.date_to),
                             ('employee_id', '=', self.employee_id.id)])
        print(slips)
        _query = """
                SELECT 
                    sum(l.total) as total
                FROM 

                        (SELECT id FROM hr_employee WHERE (id = %(employee_id)s )) e
                        left join hr_payslip_line l on (l.employee_id = e.id and code = %(code)s and l.slip_id 
                        in (SELECT id FROM hr_payslip WHERE employee_id = %(employee_id)s AND 
                        date_from >= %(date_from)s AND date_to <= %(date_to)s))
                """
        _params = {
            'date_from': first_day,
            'date_to': self.date_to,
            'employee_id': self.employee_id.id,
            'code': code
        }

        self.env.cr.execute(_query, _params)
        result = self.env.cr.dictfetchone()
        if result['total'] is not None:
            return result['total']
        return 0

    def _get_rubrique_total(self):
        self.cumul_brut = self._getCumulOlder('BRUT_TOTAL')
        self.cumul_igr = self._getCumulOlder('IGR')
        self.cumul_its = self._getCumulOlder('ITS')
        self.cumul_cn = self._getCumulOlder('CN')

    def getAcquiredOnPeriod(self):
        """
        This funciton permit to get acquired leaves days from a period
        :param type : take automaticly 01/01 to the current year
        :return: dict where the key is the employee id, and the value is the remain leaves
        """
        _query = """
            SELECT 
                CASE WHEN sum(a.number_of_days) IS Null THEN 0 ELSE sum(a.number_of_days) END AS allocation
            FROM 
                (SELECT * FROM hr_leave_type WHERE code = 'CONG') t
                    LEFT JOIN hr_leave_allocation a ON (a.holiday_status_id = t.id AND a.date_allocation <= %(date_to)s 
                    AND a.date_allocation >= %(date_from)s AND a.employee_id = %(employee_id)s)
            GROUP BY 
                a.employee_id
        """

        _params = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'employee_id': self.employee_id.id
        }

        self.env.cr.execute(_query, _params)
        res = self.env.cr.dictfetchone()
        if res:
            return res['allocation']
        else:
            return 0

    def getAcquiredLeave(self):
        """
        This funciton permit to get acquired leaves days from a period
        :param type : take automaticly 01/01 to the current year
        :return: dict where the key is the employee id, and the value is the remain leaves
        """
        _query = """
        SELECT 
            CASE WHEN sum(a.number_of_days) IS Null THEN 0 ELSE sum(a.number_of_days) END AS allocation, a.employee_id
        FROM 
            (SELECT * FROM hr_leave_type WHERE code = 'CONG') t
                LEFT JOIN hr_leave_allocation a ON (a.holiday_status_id = t.id AND a.date_allocation <= %(date_to)s AND a.employee_id = %(employee_id)s )
        GROUP BY 
            a.employee_id
        """

        _params = {
            'date_to': self.date_to,
            'employee_id': self.employee_id.id
        }

        self.env.cr.execute(_query, _params)
        res = self.env.cr.dictfetchone()
        if res:
            return res['allocation']
        else:
            return 0

    def getRemainingLeave(self, date_to):
        """
        This funciton permit to get acquired leaves days from a period
        :param type : take automaticly 01/01 to the current year
        :return: dict where the key is the employee id, and the value is the remain leaves
        attribution.create_date
        """
        # attribution = self.env['hr.leave.allocation'].search([('employee_id', '=',  self.employee_id.id),
        #                                                       ('date_to', '=', date_to)])
        # print(attribution)
        _query = """
            SELECT
                CASE WHEN sum(holidays.number_of_days) IS Null THEN 0 ELSE  sum(holidays.number_of_days) END AS holidays,
                CASE WHEN sum(attribution.number_of_days) IS Null THEN 0 ELSE  sum(attribution.number_of_days) END AS attribution,
                holidays.employee_id
            FROM
                hr_leave_type status
                left join hr_leave holidays ON (holidays.holiday_status_id=status.id AND 
                holidays.payroll_date <= %(date_to)s AND holidays.employee_id = %(employee_id)s)
                left join hr_leave_allocation attribution ON (attribution.holiday_status_id=status.id AND
                 attribution.date_allocation <= %(date_to)s AND attribution.employee_id = %(employee_id)s)
            WHERE 
                status.code='CONG'
            GROUP BY 
                holidays.employee_id
        """

        _params = {
            'date_to': date_to,
            'employee_id': self.employee_id.id
        }

        self.env.cr.execute(_query, _params)
        result = self.env.cr.dictfetchone()
        allocation = self.getAcquiredLeave()
        holidays = self.get_year_Leave()
        print(allocation, holidays)
        print('result', result)
        return allocation - holidays
        # if result:
        #     return result['attribution'] - result['holidays']
        # else:
        #     return 0

    def get_month_Leave(self):
        """
        This funciton permit to get acquired leaves days from a period
        :param type : take automaticly 01/01 to the current year
        :return: dict where the key is the employee id, and the value is the remain leaves
        """

        _query = """
            SELECT
                CASE WHEN sum(holidays.number_of_days) IS Null THEN 0 ELSE  sum(holidays.number_of_days) END AS holidays,
                holidays.employee_id
            FROM
                hr_leave_type status
                left join hr_leave holidays ON (holidays.holiday_status_id=status.id AND 
                holidays.payroll_date <= %(date_to)s AND holidays.payroll_date >= %(date_from)s
                AND holidays.employee_id = %(employee_id)s AND holidays.state='validate')

            WHERE 
                status.code='CONG'
            GROUP BY 
                holidays.employee_id
        """

        _params = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'employee_id': self.employee_id.id
        }

        self.env.cr.execute(_query, _params)
        result = self.env.cr.dictfetchone()
        if result:
            return result['holidays']
        else:
            return 0

    def get_year_Leave(self):
        """
        This funciton permit to get acquired leaves days from a period
        :param type : take automaticly 01/01 to the current year
        :return: dict where the key is the employee id, and the value is the remain leaves
        """

        _query = """
            SELECT
                CASE WHEN sum(holidays.number_of_days) IS Null THEN 0 ELSE  sum(holidays.number_of_days) END AS holidays,
                holidays.employee_id
            FROM
                hr_leave_type status
                left join hr_leave holidays ON (holidays.holiday_status_id=status.id AND 
                holidays.payroll_date <= %(date_to)s AND holidays.employee_id = %(employee_id)s AND holidays.state='validate')

            WHERE 
                status.code='CONG'
            GROUP BY 
                holidays.employee_id
        """

        _params = {
            'date_to': self.date_to,
            'employee_id': self.employee_id.id
        }

        self.env.cr.execute(_query, _params)
        result = self.env.cr.dictfetchone()
        if result:
            return result['holidays']
        else:
            return 0

    def get_allocation(self, date_to):
        """
        This funciton permit to get acquired leaves days from a period
        :param type : take automaticly 01/01 to the current year
        :return: dict where the key is the employee id, and the value is the remain leaves
        """

        _query = """
            SELECT
                CASE WHEN sum(attribution.number_of_days) IS Null THEN 0 ELSE  sum(attribution.number_of_days) END AS attribution,
                attribution.employee_id
            FROM
                hr_leave_type status
                left join hr_leave_allocation attribution ON (attribution.holiday_status_id=status.id AND
                 attribution.date_allocation <= %(date_to)s AND attribution.employee_id = %(employee_id)s AND attribution.state='validate')
            WHERE 
                status.code='CONG'
            GROUP BY 
                attribution.employee_id
        """

        _params = {
            'date_to': date_to,
            'employee_id': self.employee_id.id
        }

        self.env.cr.execute(_query, _params)
        result = self.env.cr.dictfetchone()
        if result:
            return result['attribution']
        else:
            return 0

    # def _compute_basic_net(self):
    #     for payslip in self:
    #         payslip.basic_wage = payslip._get_salary_line_total('BASE')
    #         payslip.net_wage = payslip._get_salary_line_total('NET')
    #         payslip.brut = payslip._get_salary_line_total('BRUT')
    #         payslip.brut_total = payslip._get_salary_line_total('BRUT_TOTAL')

    @api.depends('line_ids.total')
    def _compute_basic_net(self):
        line_values = (self._origin)._get_line_values(['BASIC', 'NET', 'BRUT', 'BRUT_TOTAL'])
        for payslip in self:
            payslip.basic_wage = line_values['BASIC'][payslip._origin.id]['total']
            payslip.net_wage = line_values['NET'][payslip._origin.id]['total']
            payslip.brut = line_values['BRUT'][payslip._origin.id]['total']
            payslip.brut_total = line_values['BRUT_TOTAL'][payslip._origin.id]['total']

    def get_back(self):
        for rec in self:
            rec.state = 'draft'

    @api.depends('contract_id')
    def _get_anciennete(self):
        anciennete = {}
        for slip in self:
            end_date = fields.Datetime.from_string(slip.date_to)
            start_date = fields.Datetime.from_string(slip.employee_id.start_date)
            tmp = relativedelta.relativedelta(end_date, start_date)
            slip.update({
                'payslip_an_anciennete': tmp.years,
                'payslip_mois_anciennete': tmp.months,
            })

    option_salaire = fields.Selection([('mois','Mensuel'),('jour','Journalier'),('heure','horaire')],
                         'Option salaire', readonly=False)
    reference_reglement = fields.Char('Reférence',required=False)
    payslip_an_anciennete = fields.Integer("Nombre d'année", compute='_get_anciennete')
    payslip_mois_anciennete = fields.Integer("Nombre de mois", compute='_get_anciennete')
    payment_method = fields.Selection([('espece','Espèces'),('virement','Virement bancaire'),('cheque','Chèques')],
                      string='Moyens de paiement',required=False, default='espece')
    cumul_brut = fields.Float('Cumul base impôt', compute='_get_rubrique_total')
    cumul_cn = fields.Float('Cumul CN payé', compute='_get_rubrique_total')
    cumul_igr = fields.Float('Cumul IGR payé', compute='_get_rubrique_total')
    cumul_its = fields.Float('Cumul ITS payé', compute='_get_rubrique_total')
    cumul_worked_days = fields.Float('Cumul jours travaillés')
    worked_days = fields.Float('Total jours fiscaux')
    number_of_month = fields.Integer('Nombre de mois', compute='get_cumul_base_impot')
    type = fields.Selection([('h', 'Horaire'), ('j', 'Journalier'), ('m', 'Mensuel')], 'Type',
                            related="employee_id.type")
    department_id = fields.Many2one('hr.department', 'Departement', related="employee_id.department_id")
    nature_employe = fields.Selection([('local', 'Local'), ('expat', 'Expatrié')], "Nature de l'employé",
                                      related='employee_id.nature_employe')
    base_daily = fields.Float("Base journalière")
    brut = fields.Float("Brut Simple", store=True, compute='_compute_basic_net')
    brut_total = fields.Float("Brut Total", store=True, compute='_compute_basic_net')
    fisc_days = fields.Integer('Jours fiscaux')
    worked_days_line_ids = fields.One2many('hr.payslip.worked_days', 'payslip_id',
                                           string='Payslip Worked Days', copy=True, readonly=False,
                                           states={'draft': [('readonly', False)], 'verify': [('readonly', False)]})


class HrPayslipLine(models.Model):
    '''
    Payslip Line
    '''

    _inherit = 'hr.payslip.line'

    """def _compute_total(self):
        if not self: return {}
        for line in self:
            self.total = float(line.quantity) * line.amount * line.rate / 100"""

    @api.depends('quantity', 'amount', 'rate')
    def _compute_total(self):
        if not self:return {}
        for line in self:
            line.total = float(line.quantity) * line.amount * line.rate / 100

    def _get_element(self):
        for line in self:
            line.date_from = line.slip_id.date_from
            line.date_to = line.slip_id.date_to

    amount = fields.Float('Amount', digits=(16, 2))
    quantity = fields.Float('Quantity', digits=(16, 9))
    rate = fields.Float(string='Rate (%)', digits=(16, 2), default=100)
    total = fields.Float(compute='_compute_total', string='Total', digits=(16, 0), store=True)
    date_from = fields.Date(string='Date From', compute='_get_element', store=True)
    date_to = fields.Date(string='Date To', compute='_get_element', store=True)


class hr_salary_rule(models.Model):
    _inherit = 'hr.salary.rule'
    _order = 'sequence'


class HrPayslipWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    @api.onchange('number_of_days', 'number_of_hours')
    def onChangeElementWD(self):
        if self.work_entry_type_id.code == 'WORK100':
            self.rate = (self.number_of_days / 30)
            self.number_of_hours = (self.number_of_days * 173.33) / 30

    def _computeRate(self):
        for wk_days in self:
            if wk_days.code == "WORK100":
                wk_days.rate = (wk_days.number_of_days / 30)
            else:
                wk_days.rate = 0

    rate = fields.Float('Taux', digits=(12, 9), compute='_computeRate')
    #rate = fields.Float('Taux', digits=(12, 4), compute='_computeRate')


class HrPayslipRun(models.Model):
    _inherit = "hr.payslip.run"

    def compute_sheet(self):
        self.ensure_one()
        if not self.env.context.get('active_id'):
            from_date = fields.Date.to_date(self.env.context.get('default_date_start'))
            end_date = fields.Date.to_date(self.env.context.get('default_date_end'))
            today = fields.date.today()
            first_day = today + relativedelta(day=1)
            last_day = today + relativedelta(day=31)
            if from_date == first_day and end_date == last_day:
                batch_name = from_date.strftime('%B %Y')
            else:
                batch_name = _('From %s to %s', format_date(self.env, from_date), format_date(self.env, end_date))
            payslip_run = self.env['hr.payslip.run'].create({
                'name': batch_name,
                'date_start': from_date,
                'date_end': end_date,
            })
        else:
            payslip_run = self.env['hr.payslip.run'].browse(self.env.context.get('active_id'))

        employees = self.with_context(active_test=False).employee_ids
        if not employees:
            raise UserError(_("You must select employee(s) to generate payslip(s)."))

        #Prevent a payslip_run from having multiple payslips for the same employee
        employees -= payslip_run.slip_ids.employee_id
        success_result = {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip.run',
            'views': [[False, 'form']],
            'res_id': payslip_run.id,
        }
        if not employees:
            return success_result

        payslips = self.env['hr.payslip']
        Payslip = self.env['hr.payslip']

        contracts = employees._get_contracts(
            payslip_run.date_start, payslip_run.date_end, states=['open', 'close']
        ).filtered(lambda c: c.active)
        contracts._generate_work_entries(payslip_run.date_start, payslip_run.date_end)
        work_entries = self.env['hr.work.entry'].search([
            ('date_start', '<=', payslip_run.date_end),
            ('date_stop', '>=', payslip_run.date_start),
            ('employee_id', 'in', employees.ids),
        ])
        self._check_undefined_slots(work_entries, payslip_run)

        if(self.structure_id.type_id.default_struct_id == self.structure_id):
            work_entries = work_entries.filtered(lambda work_entry: work_entry.state != 'validated')
            if work_entries._check_if_error():
                work_entries_by_contract = defaultdict(lambda: self.env['hr.work.entry'])

                for work_entry in work_entries.filtered(lambda w: w.state == 'conflict'):
                    work_entries_by_contract[work_entry.contract_id] |= work_entry

                for contract, work_entries in work_entries_by_contract.items():
                    conflicts = work_entries._to_intervals()
                    time_intervals_str = "\n - ".join(['', *["%s -> %s" % (s[0], s[1]) for s in conflicts._items]])
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Some work entries could not be validated.'),
                        'message': _('Time intervals to look for:%s', time_intervals_str),
                        'sticky': False,
                    }
                }

        default_values = Payslip.default_get(Payslip.fields_get())
        payslips_vals = []
        for contract in self._filter_contracts(contracts):
            values = dict(default_values, **{
                'name': _('New Payslip'),
                'employee_id': contract.employee_id.id,
                'payslip_run_id': payslip_run.id,
                'date_from': payslip_run.date_start,
                'date_to': payslip_run.date_end,
                'contract_id': contract.id,
                'struct_id': self.structure_id.id or contract.structure_type_id.default_struct_id.id,
            })
            payslips_vals.append(values)
        payslips = Payslip.with_context(tracking_disable=True).create(payslips_vals)
        payslips._compute_name()
        #payslips.compute_sheet()
        #payslip_run.state = 'verify'

        return success_result

