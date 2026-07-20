# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class HrDepartemet(models.Model):
    _inherit = "hr.department"
    _rec_name = 'name'

    # type = fields.Selection([
    #     ('dg', 'Direction Générale'),
    #     ('direction', 'Direction'),
    #     ('department', 'Departement'),
    #     ('service', 'Service')], "Type")
    type = fields.Selection([
        ('dg', 'Direction Générale'),
        ('direction', 'Direction'),
        ('department', 'Departement'),
        ('service', 'Service'),
        ('cellule', 'Cellule')
    ], "Type")
    company_id = fields.Many2one('res.company', string='Company', index=True)
    parent_id = fields.Many2one('hr.department', string='Parent Department', index=True)
    manager_id = fields.Many2one('hr.employee', string='Manager', tracking=True, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")


