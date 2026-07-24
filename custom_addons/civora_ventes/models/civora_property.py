# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CivoraPropertySale(models.Model):
    _inherit = 'civora.property'

    sale_ids = fields.One2many('civora.sale', 'property_id', string="Dossiers de vente")
    sale_count = fields.Integer(compute='_compute_sale_stats')
    total_sales_volume = fields.Integer(string="Volume de ventes", compute='_compute_sale_stats')

    status = fields.Selection(
        selection_add=[('vendu', 'Vendu')],
        ondelete={'vendu': 'set default'},
    )

    def _compute_sale_stats(self):
        for prop in self:
            sales = prop.sale_ids
            prop.sale_count = len(sales)
            prop.total_sales_volume = sum(
                s.sale_amount for s in sales.filtered(lambda s: s.state == 'cloture')
            )

    @api.model
    def get_sale_properties(self):
        props = self.search_read(
            [('transaction', '=', 'vente'), ('company_id', 'in', self.env.companies.ids)],
            ['name', 'ref', 'city', 'neighborhood', 'price', 'surface',
             'bedrooms', 'bathrooms', 'status', 'property_type_id'],
            order='name asc',
        )
        return props
