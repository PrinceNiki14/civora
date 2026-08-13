# -*- coding: utf-8 -*-
"""
civora.lease.clause  — Clause individuelle paramétrable d'un contrat de bail.
civora.lease.clause.set — Jeu de clauses prêt à l'emploi par type/société.

Placeholders supportés dans le corps des clauses :
  {{bailleur}}        → nom de la société (company_id.name)
  {{bailleur_adresse}} → adresse complète de la société
  {{bailleur_tel}}    → téléphone de la société
  {{bailleur_email}}  → e-mail de la société
  {{bailleur_rccm}}   → RCCM / registre société
  {{locataire}}       → nom du locataire (tenant_id.name)
  {{locataire_tel}}   → téléphone du locataire
  {{locataire_email}} → e-mail du locataire
  {{locataire_profession}} → profession du locataire (function field)
  {{proprietaire}}    → nom du propriétaire du bien
  {{bien}}            → désignation du bien (property_id.name)
  {{bien_adresse}}    → adresse du bien
  {{type_bail}}       → type de bail en clair
  {{date_debut}}      → date d'entrée formatée
  {{date_fin}}        → date de fin formatée
  {{duree_mois}}      → durée en mois
  {{duree_lettres}}   → durée en toutes lettres
  {{loyer}}           → loyer mensuel formaté
  {{charges}}         → charges mensuelles formatées
  {{total_mensuel}}   → loyer + charges formaté
  {{depot_garantie}}  → dépôt de garantie formaté
  {{total_entree}}    → total à verser à la signature
  {{loyer_lettres}}   → loyer en toutes lettres
  {{total_lettres}}   → total mensuel en toutes lettres
  {{frequence}}       → fréquence de paiement
  {{jour_paiement}}   → jour de paiement
  {{devise}}          → code devise
  {{nb_chambres}}     → nb chambres (si renseigné sur le bien)
  {{ref_contrat}}     → référence du contrat généré
  {{date_signature}}  → date d'émission du contrat
  {{ville}}           → ville de la société
"""
from odoo import api, fields, models
from odoo.exceptions import ValidationError

LEASE_TYPES = [
    ('residentiel', "Résidentiel"),
    ('commercial', "Commercial"),
]


class CivoraLeaseClause(models.Model):
    """Clause individuelle d'un contrat de bail CIVORA."""
    _name = 'civora.lease.clause'
    _description = "Clause de contrat de bail"
    _order = 'sequence, id'
    _check_company_auto = True

    name = fields.Char(string="Titre de la clause", required=True)
    numero = fields.Char(
        string="N° article",
        help="Ex : 01, 02, 03 … Sert à l'affichage dans le contrat.",
    )
    sequence = fields.Integer(string="Ordre", default=10)
    lease_type = fields.Selection(
        LEASE_TYPES,
        string="Type de bail",
        required=True,
        default='residentiel',
        help="Cette clause s'applique aux baux de ce type.",
    )
    body = fields.Html(
        string="Contenu",
        required=True,
        sanitize=True,
        sanitize_tags=True,
        help="Corps de la clause. Utilisez {{placeholder}} pour les données dynamiques.",
    )
    active = fields.Boolean(string="Active", default=True)
    company_id = fields.Many2one(
        'res.company', string="Société", required=True, index=True,
        default=lambda self: self.env.company,
    )
    set_ids = fields.Many2many(
        'civora.lease.clause.set',
        'clause_set_clause_rel',
        'clause_id', 'set_id',
        string="Jeux de clauses",
    )

    _sql_constraints = [
        ('name_company_type_unique',
         'UNIQUE(name, company_id, lease_type)',
         "Une clause avec ce titre existe déjà pour ce type de bail et cette société."),
    ]

    @api.constrains('body')
    def _check_body_not_empty(self):
        for clause in self:
            if not clause.body or not clause.body.strip():
                raise ValidationError("Le contenu de la clause ne peut pas être vide.")


class CivoraLeaseClauseSet(models.Model):
    """Jeu de clauses prêt à l'emploi — permet de pré-remplir un contrat en 1 clic."""
    _name = 'civora.lease.clause.set'
    _description = "Jeu de clauses de bail"
    _order = 'name'
    _check_company_auto = True

    name = fields.Char(string="Nom du jeu", required=True)
    lease_type = fields.Selection(
        LEASE_TYPES,
        string="Type de bail",
        required=True,
        default='residentiel',
    )
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Actif", default=True)
    company_id = fields.Many2one(
        'res.company', string="Société", required=True, index=True,
        default=lambda self: self.env.company,
    )
    clause_ids = fields.Many2many(
        'civora.lease.clause',
        'clause_set_clause_rel',
        'set_id', 'clause_id',
        string="Clauses",
        domain="[('lease_type', '=', lease_type), ('company_id', '=', company_id), ('active', '=', True)]",
    )
    clause_count = fields.Integer(
        string="Nb clauses",
        compute='_compute_clause_count',
    )

    @api.depends('clause_ids')
    def _compute_clause_count(self):
        for s in self:
            s.clause_count = len(s.clause_ids)
