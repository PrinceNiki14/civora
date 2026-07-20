# -*- coding: utf-8 -*-
from odoo import fields, models


class CivoraPropertyImage(models.Model):
    """Photo d'un bien (galerie). La premiere photo (sequence) sert de couverture."""
    _name = 'civora.property.image'
    _description = "Photo de bien CIVORA"
    _order = 'sequence, id'

    property_id = fields.Many2one(
        'civora.property',
        string="Bien",
        required=True,
        ondelete='cascade',
        index=True,
    )
    name = fields.Char(string="Titre")
    sequence = fields.Integer(string="Sequence", default=10)
    image = fields.Image(string="Photo", required=True, max_width=1920, max_height=1920)
    image_512 = fields.Image(related='image', max_width=512, max_height=512, store=True)
    image_128 = fields.Image(related='image', max_width=128, max_height=128, store=True)
    company_id = fields.Many2one(
        related='property_id.company_id',
        string="Societe",
        store=True,
        index=True,
    )
