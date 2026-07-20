# -*- coding: utf-8 -*-
from odoo import fields, models


class CivoraPipelineStage(models.Model):
    """Etape du pipeline commercial (colonnes du kanban). Parametrable."""
    _name = 'civora.pipeline.stage'
    _description = "Etape de pipeline CIVORA"
    _order = 'sequence, id'

    name = fields.Char(string="Nom", required=True, translate=True)
    code = fields.Char(string="Code", required=True)
    sequence = fields.Integer(string="Sequence", default=10)
    is_won = fields.Boolean(string="Gagnée", help="Etape finale marquant une affaire gagnée.")
    is_lost = fields.Boolean(string="Perdue", help="Etape finale marquant une affaire perdue.")
    fold = fields.Boolean(string="Repliée", help="Colonne repliée par defaut dans le kanban.")
    active = fields.Boolean(string="Actif", default=True)
    company_id = fields.Many2one(
        'res.company',
        string="Societe",
        index=True,
        default=lambda self: self.env.company,
        help="Societe proprietaire (prive). Les etapes de base (seeds) restent globales.",
    )

    _code_uniq = models.Constraint(
        'unique (code, company_id)',
        "Le code de l'etape doit etre unique par societe.",
    )
