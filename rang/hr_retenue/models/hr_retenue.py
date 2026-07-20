# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import format_amount, format_date
from itertools import groupby


class RapportCmu(models.Model):
    _inherit = "hr.salary.rule"

    type_rule = fields.Selection(selection_add=[('retenue', 'Retenue')])