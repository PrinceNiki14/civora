# -*- coding: utf-8 -*-
from odoo import fields, models


class CivoraDocumentTag(models.Model):
    """Tag libre pour organiser les documents CIVORA.

    Les tags sont partagés entre sociétés (comme les tags Odoo natifs)
    pour permettre une taxonomie transverse. Ils peuvent être créés à la
    volée depuis l'écran Documents.
    """
    _name = 'civora.document.tag'
    _description = "Tag Document CIVORA"
    _order = 'name'

    name = fields.Char(string="Nom", required=True, translate=False)
    color = fields.Integer(string="Couleur", default=0)
    document_ids = fields.Many2many('civora.document', string="Documents")

    _sql_constraints = [
        ('name_unique', 'unique(name)', "Un tag portant ce nom existe déjà."),
    ]
