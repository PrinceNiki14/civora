# -*- coding: utf-8 -*-
from odoo import fields, models


class CivoraAgentRole(models.Model):
    """Fonction d'un agent CIVORA (agent immobilier, negociateur, gestionnaire...).

    Parametrable : chaque agence gere sa propre liste de fonctions.
    """
    _name = 'civora.agent.role'
    _description = "Fonction d'agent CIVORA"
    _order = 'sequence, name'

    name = fields.Char(string="Nom", required=True, translate=True)
    code = fields.Char(
        string="Code",
        required=True,
        help="Identifiant technique (ex: negociateur, gestionnaire).",
    )
    color = fields.Char(string="Couleur", help="Couleur d'affichage (hex).")
    sequence = fields.Integer(string="Sequence", default=10)
    active = fields.Boolean(string="Actif", default=True)
    company_id = fields.Many2one(
        'res.company',
        string="Societe",
        index=True,
        default=lambda self: self.env.company,
        help="Societe proprietaire (prive par defaut). Les fonctions de base "
             "(seeds) restent globales (company_id vide).",
    )

    # Unicite par societe (le meme code peut exister en global + par societe).
    _code_uniq = models.Constraint(
        'unique (code, company_id)',
        "Le code de la fonction doit etre unique par societe.",
    )
