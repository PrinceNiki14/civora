# -*- coding: utf-8 -*-
##############################################################################
##############################################################################


from odoo import models, fields

class res_company(models.Model):
    _inherit = 'res.company'

    logo_cgrae = fields.Image("Logo CGRAE", copy=False, attachment=True)