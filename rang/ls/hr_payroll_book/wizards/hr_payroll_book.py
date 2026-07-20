# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrPayrollBook(models.TransientModel):
    _name = "hr.payroll.book.wizard"
    _description = "HR Payroll Book Wizard"

    def _get_initial_data(self):
        active_model = self._context.get('active_model')
        active_ids = self._context.get('active_ids')
        employees = self.env['hr.employee'].search([('active', '=', True)])
        if active_ids and active_model:
            if active_model == 'hr.employee':
                employees = self.env['hr.employee'].browse(active_ids)
            else:
                employees = self.env[active_model].browse(active_ids).slip_ids.mapped('employee_id')
        return employees

    @api.constrains("date_from", "date_to")
    def _check_constraints_data(self):
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                raise UserError(_("La date de fin doit être toujours supérieure à la date de début."))

    @api.onchange("date_from", "date_to", "type_employe", "nature_employe")
    def onChangeData(self):
        _criteria = [('id', 'in', self.employee_ids.ids)] if self.employee_ids else []
        if self.type_employe != 'all':
            _criteria.append(('type', '=', self.type_employe))
        else:
            _criteria.append(('type', 'in', ('m', 'j', 'h')))
        if self.nature_employe != 'all':
            _criteria.append(('nature_employe', '=', self.nature_employe))
        else:
            _criteria.append(('nature_employe', 'in', ('local', 'expat')))
        emp_ids = self.env['hr.employee'].search(_criteria)
        if emp_ids:
            self.employee_ids = emp_ids
            if self.date_from and self.date_to:
                if self.date_from > self.date_to:
                    raise UserError(_("La date de fin doit être toujours supérieure à la date de début."))
                else:
                    payslips = self.env['hr.payslip'].search([
                        ('date_from', '>=', self.date_from),
                        ('date_to', '<=', self.date_to),
                        ('employee_id', 'in', emp_ids.ids)
                    ])
                    if payslips:
                        self.payslip_ids = payslips
                        self.employee_ids = payslips.mapped('employee_id')
                        rules = payslips.mapped('line_ids').filtered(
                            lambda r: r.appears_on_payroll
                        ).mapped('salary_rule_id')
                        if rules:
                            self.rule_ids = rules
        else:
            self.payslip_ids = False
            self.employee_ids = emp_ids
            self.rule_ids = False

    name = fields.Char("Libellé", required=True, default="/")
    date_from = fields.Date("Date début", required=True)
    date_to = fields.Date("Date fin", required=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    type_employe = fields.Selection([
        ('m', 'Mensuel'),
        ('j', 'Journalier'),
        ('h', 'Horaire'),
        ('all', 'Tous les employés')
    ], "Livre de paie pour ", default="all")
    nature_employe = fields.Selection([
        ('local', 'Les Locaux'),
        ('expat', 'Les expatriés'),
        ('all', 'Tous')
    ], "Nature de l'employé", default='all')
    employee_ids = fields.Many2many(
        'hr.employee',
        string="Employés concernés par la période",
        default=_get_initial_data
    )
    payslip_ids = fields.Many2many('hr.payslip', string="Liste des bulletins de la période")
    rule_ids = fields.Many2many('hr.salary.rule', string="Règles salariales")

    def getRuleForThisPeriode(self):
        """
        Cette fonction permet de récupérer les règles salariales de la période
        :return: dict avec les règles et les codes des règles salariales
        """
        if self.rule_ids:
            rules = {x.code: x.name for x in self.rule_ids}
            codes = [x.code for x in self.rule_ids]
            return {
                'rules': rules,
                'codes': codes
            }
        return {'rules': {}, 'codes': []}

    def compute_payroll(self):
        if self.employee_ids and self.payslip_ids and self.rule_ids:
            lines = []
            total = {}
            code = [rule.code for rule in self.rule_ids]
            if code:
                code_list = list(set(code))
            
            for emp in self.employee_ids:
                line = {
                    'name': emp.name,
                    'identification_id': emp.identification_id,
                }
                slips = self.payslip_ids.filtered(lambda s: s.employee_id.id == emp.id)
                if slips:
                    for rule in self.rule_ids:
                        amount = sum([x._get_salary_line_total(rule.code) for x in slips])
                        line[rule.code] = amount
                        if rule.code in total:
                            total[rule.code] += amount
                        else:
                            total[rule.code] = amount
                lines.append(line)
            return {
                "lines": lines,
                "total": total
            }
        return {"lines": [], "total": {}}

    def setData(self, datas, rules):
        for dt in datas:
            for key in rules.keys():
                if key not in dt:
                    dt[key] = 0
        return datas

    def _print_report(self, datas, type):
        self.ensure_one()
        datas['ids'] = self.ids
        datas['model'] = self._name
        datas['date_from'] = self.date_from
        datas['date_to'] = self.date_to
        datas['company_id'] = self.company_id.id
        if type == 'pdf':
            lines = self.setData(datas['lines'], datas['rules'])
            pages = [lines[x:x + 9] for x in range(0, len(lines), 9)]
            datas['pages'] = pages
            return (
                self.env["ir.actions.report"]
                .search([("report_name", "=", 'hr_payroll_book.report_payroll_wizard')], limit=1)
                .report_action(self, data=datas)
            )
        else:
            return self.env.ref('hr_payroll_book.report_hr_payroll_book_wizard_xlx').with_context(
                data=datas
            ).report_action(self, data=datas)

    def check_report(self):
        datas = self.compute_payroll()
        datas.update(self.getRuleForThisPeriode())
        return self._print_report(datas, 'pdf')

    def export_xls(self):
        datas = self.compute_payroll()
        datas.update(self.getRuleForThisPeriode())
        return self._print_report(datas, 'excel')
