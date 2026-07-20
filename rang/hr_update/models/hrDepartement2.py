# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class HrDepartemet(models.Model):
    _inherit = "hr.department"

    type = fields.Selection(selection_add=[('dg', 'Direction Générale'), ('direction',), ('service',), ('cellule', 'Cellule')])
    code_ana = fields.Char("Code analytique")
