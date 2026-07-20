# -*- coding:utf-8 -*-


from odoo import api, models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    number_holidays_locaux = fields.Float('Employés locaux', related='company_id.number_holidays_locaux',readonly=False)
    number_holidays_expat = fields.Float('Employés expatriés', related='company_id.number_holidays_expat',readonly=False)