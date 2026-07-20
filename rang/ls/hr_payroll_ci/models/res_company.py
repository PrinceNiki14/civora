# -*- coding: utf-8 -*-
##############################################################################
##############################################################################


from odoo import models, fields

class res_company(models.Model):
    _inherit = 'res.company'

    num_cnps= fields.Char("Numéro CNPS", required=True)
    num_contribuable= fields.Char("Numéro Contribuable",required=True)