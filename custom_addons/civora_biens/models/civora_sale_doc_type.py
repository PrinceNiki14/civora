# -*- coding: utf-8 -*-
"""Documents juridiques exigibles lors de la vente d'un bien.

Le referentiel est modelise plutot que fige dans une selection : le droit
foncier ivoirien evolue, et une agence doit pouvoir ajouter une piece qui
lui est propre sans attendre une mise a jour du module.

Les neuf types livres correspondent aux pieces couramment demandees en
Cote d'Ivoire pour une transaction fonciere ou immobiliere.
"""
from odoo import api, fields, models


class CivoraSaleDocType(models.Model):
    _name = 'civora.sale.doc.type'
    _description = "Type de document juridique de vente"
    _order = 'sequence, name'

    name = fields.Char(string="Document", required=True, translate=True)
    code = fields.Char(
        string="Code", required=True,
        help="Identifiant technique (ex: acd, titre_foncier).",
    )
    description = fields.Text(string="Description")
    # Certaines pieces ne concernent que le foncier nu, d'autres que le bati.
    scope = fields.Selection([
        ('tous', "Tous les biens"),
        ('terrain', "Terrain uniquement"),
        ('bati', "Bâti uniquement"),
    ], string="Portée", default='tous', required=True)
    is_essential = fields.Boolean(
        string="Pièce maîtresse", default=False,
        help="Document sans lequel une vente est juridiquement fragile. "
             "Sert à alerter l'agence sur un dossier incomplet.",
    )
    sequence = fields.Integer(string="Séquence", default=10)
    active = fields.Boolean(string="Actif", default=True)
    company_id = fields.Many2one(
        'res.company', string="Société",
        help="Vide = référentiel partagé par toutes les sociétés.",
    )

    _code_uniq = models.Constraint(
        'unique (code, company_id)',
        "Ce code de document existe déjà pour cette société.",
    )

    @api.model
    def civora_doc_types(self):
        """Referentiel expose a l'ecran de saisie d'un bien."""
        recs = self.search([
            '|', ('company_id', '=', False),
            ('company_id', 'in', self.env.companies.ids),
        ])
        return [{
            'id': r.id,
            'name': r.name,
            'code': r.code,
            'scope': r.scope,
            'is_essential': r.is_essential,
        } for r in recs]
