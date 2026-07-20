# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools.translate import _
from odoo.exceptions import ValidationError


# Valeurs de consentement RGPD (alignees sur le front CIVORA).
CIVORA_CONSENT = [
    ('opt_in', "Opt-in"),
    ('opt_out', "Opt-out"),
    ('none', "—"),
]


class ResPartner(models.Model):
    """Extension CIVORA de res.partner.

    On etend le contact standard Odoo (socle invisible : nom, email, telephone,
    ville, adresse, societe, etiquettes, notes, comptabilite...) avec la couche
    metier CIVORA, alignee sur le modele du front (StoredContact) : role(s),
    source, score IA, statut, agent, prochaine action, budget, RGPD.

    Aucune vue Odoo : ces champs sont pilotes par les ecrans OWL de CIVORA.
    Correspondance avec les champs natifs reutilises :
      name / email / phone / city / street  -> natifs res.partner
      company                                -> company_name (natif)
      notes                                  -> comment (natif)
      tags                                   -> category_id (natif)
    """
    _inherit = 'res.partner'

    # --- Marqueur ------------------------------------------------------
    civora_is_contact = fields.Boolean(
        string="Contact CIVORA",
        default=False,
        index=True,
        help="Coche pour les contacts geres via l'application CIVORA.",
    )

    # --- Roles (multi) + role principal --------------------------------
    civora_role_ids = fields.Many2many(
        'civora.contact.role',
        'civora_partner_role_rel', 'partner_id', 'role_id',
        string="Roles",
        help="Un contact peut cumuler plusieurs roles (proprietaire, locataire...).",
    )
    civora_primary_role_id = fields.Many2one(
        'civora.contact.role',
        string="Role principal",
        ondelete='restrict',
        help="Role mis en avant pour l'affichage et le tri. Doit faire partie des roles.",
    )
    civora_role_names = fields.Char(
        string="Roles (libelle)",
        compute='_compute_civora_role_names',
        help="Liste des roles en texte, pour l'affichage.",
    )

    # --- Acquisition & segmentation ------------------------------------
    civora_source_id = fields.Many2one(
        'civora.contact.source',
        string="Source",
        ondelete='restrict',
        index=True,
        help="Canal d'acquisition du contact.",
    )
    civora_segment_ids = fields.Many2many(
        'civora.contact.segment',
        'civora_partner_segment_rel', 'partner_id', 'segment_id',
        string="Segments IA",
    )

    # --- Suivi commercial ----------------------------------------------
    civora_status = fields.Selection(
        [
            ('chaud', "Chaud"),
            ('actif', "Actif"),
            ('qualifie', "Qualifie"),
            ('a_risque', "A risque"),
            ('inactif', "Inactif"),
        ],
        string="Statut",
        index=True,
        help="Statut du contact dans le cycle CRM.",
    )
    civora_ai_score = fields.Integer(
        string="Score IA",
        default=0,
        help="Score d'engagement / valeur du contact, de 0 a 100.",
    )
    civora_agent_id = fields.Many2one(
        'res.users',
        string="Agent responsable",
        index=True,
    )
    civora_next_action = fields.Char(
        string="Prochaine action",
        help="Prochaine action commerciale prevue (ex: rappeler, envoyer offre).",
    )

    # --- Coordonnees & localisation complementaires --------------------
    civora_whatsapp = fields.Char(string="WhatsApp")
    civora_neighborhood = fields.Char(
        string="Quartier",
        help="Quartier / zone (ex: Cocody, Marcory, Plateau).",
    )

    # --- Budget --------------------------------------------------------
    civora_currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        default=lambda self: self.env.company.currency_id,
    )
    civora_budget = fields.Monetary(
        string="Budget",
        currency_field='civora_currency_id',
        help="Budget estime du contact (achat / location).",
    )

    # --- Consentements RGPD --------------------------------------------
    civora_consent_email = fields.Selection(
        CIVORA_CONSENT, string="Consentement email", default='none',
    )
    civora_consent_sms = fields.Selection(
        CIVORA_CONSENT, string="Consentement SMS", default='none',
    )
    civora_consent_whatsapp = fields.Selection(
        CIVORA_CONSENT, string="Consentement WhatsApp", default='none',
    )

    # --- Interactions (timeline 360°) ----------------------------------
    civora_interaction_ids = fields.One2many(
        'civora.interaction', 'contact_id',
        string="Interactions",
    )
    civora_interaction_count = fields.Integer(
        string="Nb interactions",
        compute='_compute_civora_interaction_count',
    )

    # --- Contraintes ---------------------------------------------------
    # Le score IA doit rester dans l'intervalle [0, 100].
    _civora_ai_score_range = models.Constraint(
        'CHECK(civora_ai_score >= 0 AND civora_ai_score <= 100)',
        "Le score IA doit etre compris entre 0 et 100.",
    )

    @api.depends('civora_role_ids', 'civora_role_ids.name')
    def _compute_civora_role_names(self):
        for partner in self:
            partner.civora_role_names = ", ".join(partner.civora_role_ids.mapped('name'))

    @api.model_create_multi
    def create(self, vals_list):
        # Cloisonnement strict : tout contact CIVORA cree sans societe est
        # rattache a la societe courante. "Contact CIVORA" = flag civora_is_contact
        # OU au moins un role CIVORA (acquereur, proprietaire, locataire...).
        # Les partenaires non-CIVORA gardent le comportement natif d'Odoo.
        for vals in vals_list:
            if vals.get('company_id'):
                continue
            has_role = bool(vals.get('civora_role_ids'))
            if vals.get('civora_is_contact') or has_role:
                vals['company_id'] = self.env.company.id
        return super().create(vals_list)

    @api.depends('civora_interaction_ids')
    def _compute_civora_interaction_count(self):
        for partner in self:
            partner.civora_interaction_count = len(partner.civora_interaction_ids)

    @api.constrains('civora_primary_role_id', 'civora_role_ids')
    def _check_civora_primary_role(self):
        for partner in self:
            if (
                partner.civora_primary_role_id
                and partner.civora_primary_role_id not in partner.civora_role_ids
            ):
                raise ValidationError(_(
                    "Le role principal doit faire partie des roles du contact."
                ))
