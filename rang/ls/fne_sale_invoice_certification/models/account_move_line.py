from odoo import models, fields


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    _description = "Ligne de facture avec ID FNE"

    fne_item_id = fields.Char(
        string='ID Article FNE',
        readonly=True,
        help="Identifiant unique de l'article dans le système FNE (utilisé pour les avoirs)"
    )
    
    

class ResPartner(models.Model):
    _inherit = 'res.partner'
    

    ncc = fields.Char(
        string='ncc',
        help="NCC"
    )

