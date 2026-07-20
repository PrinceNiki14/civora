from odoo import api, fields, models, _
from datetime import datetime
from dateutil import relativedelta


class HrContractCategory(models.Model):
    _name = 'hr.contract.category'
    _description = "Gestion des categories d'employee"
    _order = 'sequence'

    name = fields.Char('Désignation', required=True)
    code = fields.Char('Code', required=True)
    sequence = fields.Integer('Séquence', required=True)
    description = fields.Text('Description', required=False)
