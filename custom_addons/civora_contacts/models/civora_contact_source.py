# -*- coding: utf-8 -*-
from odoo import fields, models


class CivoraContactSource(models.Model):
    """Source d'acquisition d'un contact (Portail, Reseau, Walk-in...).

    Parametrable : l'agence gere sa propre liste de canaux d'acquisition.
    """
    _name = 'civora.contact.source'
    _description = "Source de contact CIVORA"
    _order = 'sequence, name'

    name = fields.Char(string="Nom", required=True, translate=True)
    code = fields.Char(
        string="Code",
        required=True,
        help="Identifiant technique unique (ex: portail, reseau, walk_in).",
    )
    sequence = fields.Integer(string="Sequence", default=10)
    active = fields.Boolean(string="Actif", default=True)
    company_id = fields.Many2one(
        'res.company',
        string="Societe",
        index=True,
        default=lambda self: self.env.company,
        help="Societe proprietaire (prive par defaut). Les elements de base (seeds) "
             "restent globaux (company_id vide) et visibles par toutes les societes.",
    )

    _code_uniq = models.Constraint(
        'unique (code)',
        "Le code de la source doit etre unique.",
    )
