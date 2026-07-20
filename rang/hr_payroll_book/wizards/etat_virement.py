# -*- coding:utf-8 -*-
from num2words import num2words

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import format_amount
from itertools import groupby


class EtatVirement(models.TransientModel):
    _name = "ordre.virement"

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

    def _default_name(self):
        return "ORDRE DE VIREMENT DE %s" % self.env.company.name

    @api.onchange("date_from", "date_to", "lot_id")
    @api.depends("date_from", "date_to", "lot_id")
    def _on_change_data(self):
        if self.lot_id:
            self.date_from = self.lot_id.date_start
            self.date_to = self.lot_id.date_end
        if self.date_from and self.date_to and not self.lot_id:
            if self.date_from > self.date_to:
                raise UserError(_("La date de fin doit être toujours supérieure à la date de début."))
            payslips = self.env['hr.payslip'].search([('date_from', '>=', self.date_from),
                                                      ('date_to', '<=', self.date_to),
                                                      ])
            if payslips:
                self.payslip_ids = payslips
        if self.date_from and self.date_to and self.lot_id:
            if self.date_from > self.date_to:
                raise UserError(_("La date de fin doit être toujours supérieure à la date de début."))
            payslips = self.env['hr.payslip'].search([('date_from', '>=', self.date_from),
                                                      ('date_to', '<=', self.date_to),
                                                      ('payslip_run_id', '=', self.lot_id.id),
                                                      ])
            if payslips:
                self.payslip_ids = payslips

    def _get_amount_to_letter(self, amount):
        if amount:
            amount_text = num2words(amount, lang='fr')
            print(amount_text)
            return amount_text

    def _default_currency_id(self):
        return self.env.user.company_id.currency_id

    # def _default_objet(self):
    #     return "Ordre de virement pour accessoire de salaire du mois de %s "
    name = fields.Char("Objet", required=True)
    banque = fields.Char("Banque")
    attention_de = fields.Char("A l'attention de")
    date_from = fields.Date("Date début", required=True)
    date_to = fields.Date("Date fin", required=True)
    lot_id = fields.Many2one("hr.payslip.run", "Lot")
    payslip_ids = fields.Many2many('hr.payslip', string="Liste des bulletins de la période")
    salaire_ids = fields.One2many('ordre.virement_salaire.line', 'virement_id')
    accessoire_ids = fields.One2many('ordre.virement_accessoire.line', 'virement_id')
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self._default_currency_id())
    type_virement = fields.Selection([
        ('accessoire', 'Accessoire'),
        ('salaire', 'Salaire')], default="salaire", string="Type de virement")

    def compute_all(self):
        for rec in self:
            rec.env['ordre.virement_salaire.line'].search([]).sudo().unlink()
            rec.env['ordre.virement_accessoire.line'].search([]).sudo().unlink()
            if rec.payslip_ids:
                if rec.type_virement == 'salaire':
                    emp_list = []
                    for payslip in self.payslip_ids:
                        emp_data = {
                            'employee_id': payslip.employee_id.id,
                            'net_paie': payslip.net_wage,
                        }
                        emp_list.append(emp_data)
                    rec.salaire_ids = [(0, 0, d) for d in emp_list]
                if rec.type_virement == 'accessoire':
                    accessoire_data = []
                    line_ids = rec.payslip_ids.mapped("line_ids").filtered(lambda x: x.salary_rule_id.est_accessoire is True)
                    salary_rule_ids = line_ids.mapped("salary_rule_id")
                    #salary_rules = list(set(salary_rule_ids))
                    # salary_rules = list(set(salary_rule_ids))
                    salary_rules = []
                    for salary in salary_rule_ids:
                        salary_rules.append(salary.code)
                    for rule in list(set(salary_rules)):
                        rule_d = rec.env['hr.salary.rule'].search([('code', '=', rule),('est_accessoire', '=', True)], limit=1)
                        accessoire_list = []
                        for line in line_ids:
                            if line.salary_rule_id.code == rule:
                                accessoire_list.append(line)
                        if accessoire_list:
                            amount = 0
                            for line in accessoire_list:
                                amount += line.total
                            acc_data = {
                                'salary_rule_id': rule_d.id,
                                'net_paie': amount,
                            }
                            accessoire_data.append(acc_data)
                    print(accessoire_data)
                    rec.accessoire_ids = [(0, 0, d) for d in accessoire_data]
            else:
                rec.line_ids = []

    def _print_report(self, datas, type):
        self.ensure_one()
        # print(datas)
        if type == 'pdf':
            return (
                self.env["ir.actions.report"]
                .search(
                    [("report_name", "=", 'hr_payroll_book.report_ordre_virement')],
                    limit=1,
                ).report_action(self, data=datas)
            )
        else:
            return self.env.ref('hr_payroll_book.report_ordre_virement_xlsx_id').with_context(data=datas). \
                report_action(self, data=datas)

    def check_report(self):
        self.compute_all()
        datas = {'ids': self.ids,
                 'model': self._name,
                 'date_from': self.date_from,
                 'date_to': self.date_to,
                 # 'company_id': self.company_id,
                 }
        return self._print_report(datas, 'pdf')

    def export_xls(self):
        self.compute_all()
        datas = {'ids': self.ids,
                 'model': self._name,
                 'date_from': self.date_from,
                 'date_to': self.date_to,
                 'company_id': self.company_id.id,
                 'currency_id': self.currency_id.id,
                 }
        return self._print_report(datas, 'excel')


class EtatVirementSalaireLine(models.TransientModel):
    _name = "ordre.virement_salaire.line"

    employee_id = fields.Many2one("hr.employee")
    net_paie = fields.Integer()
    virement_id = fields.Many2one("ordre.virement")


class EtatVirementAccessoireLine(models.TransientModel):
    _name = "ordre.virement_accessoire.line"

    salary_rule_id = fields.Many2one("hr.salary.rule")
    net_paie = fields.Integer()
    virement_id = fields.Many2one("ordre.virement")


class HrSalaryRule(models.Model):
    _inherit = "hr.salary.rule"

    est_accessoire = fields.Boolean("Est accessoire")
    banque_id = fields.Many2one("res.bank", "Banque")
    code_banque = fields.Char("Code Banque")
    code_guichet = fields.Char("Code guichet")
    num_compte_bancaire = fields.Char("Compte")
    cle_rib = fields.Char("Clé RIB")

