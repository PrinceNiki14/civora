# -*- coding: utf-8 -*-
from odoo import fields, models


class CivoraContactSegment(models.Model):
    """Segment IA d'un contact (Investisseur premium, Voyageur recurrent...).

    Sert a la segmentation marketing et au ciblage. Parametrable ; peut etre
    alimente automatiquement par l'IA plus tard.
    """
    _name = 'civora.contact.segment'
    _description = "Segment IA de contact CIVORA"
    _order = 'sequence, name'

    name = fields.Char(string="Nom", required=True, translate=True)
    code = fields.Char(
        string="Code",
        required=True,
        help="Identifiant technique unique.",
    )
    color = fields.Char(
        string="Couleur",
        default="#25afd2",
        help="Couleur du badge au format hexadecimal.",
    )
    description = fields.Text(string="Description")
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
        "Le code du segment doit etre unique.",
    )
