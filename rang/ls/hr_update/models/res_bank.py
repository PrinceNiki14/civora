from odoo import api, fields, exceptions, models, _


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    code_guichet = fields.Char('Code guichet', required=False)
    rib = fields.Char('Clé RIB', required=False)
