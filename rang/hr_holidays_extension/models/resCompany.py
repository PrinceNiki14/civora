# -*- coding:utf-8 -*-

from odoo import api, models, fields

class resCompany(models.Model):
    _inherit = 'res.company'

    holidays_based_to_calendar = fields.Boolean('Congés basés sur le nombre de jours calendaires')
    number_holidays_locaux = fields.Float('Nombre de jours de congés mensuels à attribuer employé nationaux',
                                          default='2.75')
    number_holidays_expat = fields.Float('Nombre de jours de congés mensuels à attribuer employé expatriés',
                                         default='5')


