from odoo import api, fields, models, _


class HrDepartment(models.Model):
    _inherit = "hr.department"

    type = fields.Selection([
        ('direction', 'Direction'),
        ('department', 'Departement'),
        ('service', 'Service')], "Type")
