# -*- coding: utf-8 -*-
from odoo import fields, models


class CivoraPropertyType(models.Model):
    """Type de bien (villa, appartement, bureau, studio...).

    Parametrable : chaque agence gere sa propre liste de types.
    """
    _name = 'civora.property.type'
    _description = "Type de bien CIVORA"
    _order = 'sequence, name'

    name = fields.Char(string="Nom", required=True, translate=True)
    code = fields.Char(string="Code", required=True, help="Identifiant technique (ex: villa, appartement).")
    color = fields.Char(string="Couleur", help="Couleur d'affichage (hex).")
    sequence = fields.Integer(string="Sequence", default=10)
    active = fields.Boolean(string="Actif", default=True)
    company_id = fields.Many2one(
        'res.company',
        string="Societe",
        index=True,
        default=lambda self: self.env.company,
        help="Societe proprietaire (prive par defaut). Les types de base (seeds) "
             "restent globaux (company_id vide) et visibles par toutes les societes.",
    )

    _code_uniq = models.Constraint(
        'unique (code, company_id)',
        "Le code du type de bien doit etre unique par societe.",
    )
