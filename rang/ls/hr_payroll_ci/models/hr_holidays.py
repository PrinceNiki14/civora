# -*- coding:utf-8 -*-

from odoo import fields, models, api
from collections import namedtuple
from datetime import datetime


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    conge_non_exceptionne = fields.Boolean('Congé non exceptionnel')
    montant_conge = fields.Float('Montant')
    motif_conge = fields.Char('Motif de la demande')


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    code = fields.Char('Code', help="Code utilisé pour identifier le type de congé dans les calculs de paie")
