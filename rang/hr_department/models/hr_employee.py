# -*- encoding: utf-8 -*-
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from datetime import date
from odoo import fields, models, api, _


class HrrEmployee(models.Model):
    _inherit = "hr.employee"

    direction_generale_id = fields.Many2one('hr.department', 'Direction Générale', required=False, domain="[('type', '=', 'dg')]")
    direction_id = fields.Many2one('hr.department', 'Direction', required=False,
                                   domain="[('type', '=', 'direction'),('parent_id', '=', direction_generale_id)]")
    department_id = fields.Many2one('hr.department', 'Departement', required=False,
                                    domain="[('type', '=', 'department'),('parent_id', '=', direction_id)]")
    service_id = fields.Many2one('hr.department', 'Service', required=False,
                                 domain="[('type', '=', 'service'),('parent_id', '=', department_id)]")
    cellule_id = fields.Many2one('hr.department', 'Cellule', required=False,
                                 domain="[('type', '=', 'cellule'),('parent_id', '=', service_id)]")
