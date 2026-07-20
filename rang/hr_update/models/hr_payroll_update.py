# -*- encoding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.osv import expression

class HrPayrollStructureType(models.Model):
    _inherit = 'hr.payroll.structure.type'

    company_id = fields.Many2one('res.company', "Entité", default=lambda self: self.env.company)


class Contract(models.Model):
    _inherit = 'hr.contract'

    structure_type_id = fields.Many2one('hr.payroll.structure.type', string="Salary Structure Type",
                                            domain="[('company_id', '=', company_id)]")

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            print(self.company_id)
            structure_types = self.env['hr.payroll.structure.type'].search([
                ('company_id', '=', self.company_id.id),
            ])
            if structure_types:
                self.structure_type_id = structure_types[0]
            elif self.structure_type_id not in structure_types:
                self.structure_type_id = False


class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    company_id = fields.Many2one('res.company', "Entité", default=lambda self: self.env.company)
    type_employee = fields.Selection([('F', 'Fonctionnaire'), ('NF', 'Non Fonctionnaire')], "Type d'agent")

    @api.depends('department_id', 'type_employee')
    @api.onchange('department_id', 'type_employee')
    def _compute_employee_ids(self):
        for wizard in self:
            print('type_employee', self.type_employee)
            domain = wizard._get_available_contracts_domain()
            if wizard.department_id:
                domain = expression.AND([
                    domain,
                    [('department_id', 'child_of', self.department_id.id)]
                ])
            if wizard.type_employee:
                domain = expression.AND([
                    domain,
                    [('type_employee', '=',self.type_employee)]
                ])
            wizard.employee_ids = self.env['hr.employee'].search(domain)


class HrPayrollStructure(models.Model):
    _inherit = "hr.payroll.structure"

    company_id = fields.Many2one("res.company", "Sosiété", default=lambda self: self.env.company)


class ContractHistory(models.Model):
    _inherit = 'hr.contract.history'

    def hr_contract_view_form_new_action(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('hr_contract.action_hr_contract')

        action.update({
            'context': {
                'default_employee_id': self.employee_id.id,
                'default_expatried': True if self.employee_id.nature_employe == 'expat' else False
            },
            'view_mode': 'form',
            'view_id': self.env.ref('hr_contract.hr_contract_view_form').id,
            'views': [(self.env.ref('hr_contract.hr_contract_view_form').id, 'form')],
        })
        return action


class HrSalaryRule(models.Model):
    _inherit = "hr.salary.rule"

    #company_id = fields.Many2one('res.company', 'Société', related="struct_id.company_id", store=True)
    company_id = fields.Many2one('res.company', "Entité", default=lambda self: self.env.company)
    type_cotisation = fields.Boolean("Cotisation employé/Employeur")
    linked_to = fields.Many2one("hr.salary.rule", "Rubrique lié à")


class HrWorkLocation(models.Model):
    _inherit = "hr.work.location"

