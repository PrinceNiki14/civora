from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    cmu_part = fields.Integer(
        "Nombre de personnes à prendre en compte pour la CMU",
        compute="_compute_part_cmu",
        store=True
    )
    pay_for_women = fields.Selection(
        [('yes', 'Oui'), ('no', 'Non')],
        "Cotiser pour son époux(se)",
        default='no'
    )
    pay_for_children = fields.Selection(
        [('yes', 'Oui'), ('no', 'Non')],
        "Cotiser pour ses enfants",
        default='no'
    )
    cotisation_mugef_ci = fields.Selection(
        [('yes', 'Oui'), ('no', 'Non')],
        "Cotiser Mutuelle MUGEF-CI - CMU",
        default='no'
    )

    @api.depends("children", "pay_for_women", "marital", "pay_for_children")
    def _compute_part_cmu(self):
        for emp in self:
            part_cmu = 1
            if emp.pay_for_women == 'yes':
                part_cmu += 1
            if emp.pay_for_children == 'yes':
                part_cmu += emp.children
            emp.cmu_part = part_cmu

    def update_igr(self):
        employee_ids = self.env['hr.employee'].search([('company_id', '=', self.env.company.id)])
        for employee in employee_ids:
            child = 0
            if hasattr(employee, 'enfants_ids'):
                enfants_ids = employee.mapped('enfants_ids')
                if enfants_ids:
                    for enfant in enfants_ids:
                        if enfant.age <= 21:
                            child += 1
            employee.write({
                'children': child,
                'pay_for_children': 'no',
                'pay_for_women': 'no',
                'cmu_part': 1,
            })
