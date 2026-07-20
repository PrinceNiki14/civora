from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'
    _description = "Contact avec NCC"

    ncc = fields.Char(
        string='NCC',
        help="Numéro de Compte Contribuable du client au format 1845265C"
    )
