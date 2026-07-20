# -*- coding: utf-8 -*-
from odoo import fields, models


class CivoraContactRole(models.Model):
    """Role d'un contact (Proprietaire, Locataire, Acquereur...).

    Modele parametrable : l'agence peut ajouter/retirer des roles sans
    modification de code. Chaque role porte une couleur pour les badges
    de l'interface CIVORA.
    """
    _name = 'civora.contact.role'
    _description = "Role de contact CIVORA"
    _order = 'sequence, name'

    name = fields.Char(string="Nom", required=True, translate=True)
    code = fields.Char(
        string="Code",
        required=True,
        help="Identifiant technique unique (ex: proprietaire, locataire).",
    )
    color = fields.Char(
        string="Couleur",
        default="#626a75",
        help="Couleur du badge au format hexadecimal (ex: #00ab68).",
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
        "Le code du role doit etre unique.",
    )
