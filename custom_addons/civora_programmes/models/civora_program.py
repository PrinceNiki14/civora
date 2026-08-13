# -*- coding: utf-8 -*-
from odoo import api, fields, models

# Nature juridique / commerciale du programme.
CIVORA_PROGRAM_TYPE = [
    ('neuf', "Neuf"),
    ('vefa', "VEFA"),
    ('lotissement', "Lotissement"),
]

# Cycle de vie du programme (aligne sur les filtres de l'ecran Programmes).
CIVORA_PROGRAM_STATUS = [
    ('etude', "Etude"),
    ('commercialisation', "Commercialisation"),
    ('travaux', "Travaux"),
    ('livre', "Livre"),
]


class CivoraProgram(models.Model):
    """Programme immobilier CIVORA (promotion neuve, VEFA ou lotissement).

    Objet pivot du bloc Promotion : porte le stock de lots, le planning de
    chantier, l'echeancier VEFA, les appels de fonds, les garanties, le dossier
    documentaire et les acteurs du projet.
    """
    _name = 'civora.program'
    _description = "Programme immobilier CIVORA"
    _order = 'name'
    _check_company_auto = True

    # --- Identite -----------------------------------------------------
    name = fields.Char(string="Nom du programme", required=True, index=True)
    ref = fields.Char(
        string="Reference", copy=False, index=True, readonly=True,
        default=lambda self: "Nouveau",
        help="Reference interne du programme (ex: PRG-101).",
    )
    slug = fields.Char(string="Slug", compute='_compute_slug', store=True, index=True)
    program_type = fields.Selection(
        CIVORA_PROGRAM_TYPE, string="Type de programme",
        required=True, default='vefa', index=True,
    )
    status = fields.Selection(
        CIVORA_PROGRAM_STATUS, string="Statut",
        required=True, default='etude', index=True,
    )
    active = fields.Boolean(string="Actif", default=True)

    developer = fields.Char(string="Promoteur", index=True)
    city = fields.Char(string="Ville", index=True)
    district = fields.Char(string="Quartier / zone")
    street = fields.Char(string="Adresse complete")
    architect = fields.Char(string="Architecte")
    contractor = fields.Char(string="Entreprise BTP")
    description = fields.Text(string="Description")

    # --- Composition --------------------------------------------------
    building_count = fields.Integer(string="Nombre de batiments", default=1)
    total_lots = fields.Integer(string="Total lots")
    sold_lots = fields.Integer(string="Lots vendus")
    reserved_lots = fields.Integer(string="Lots reserves")

    land_surface = fields.Float(string="Surface foncier (m2)")
    built_surface = fields.Float(string="Surface batie SHON (m2)")
    avg_price_sqm = fields.Monetary(string="Prix moyen / m2", currency_field='currency_id')

    # --- Finances -----------------------------------------------------
    currency_id = fields.Many2one(
        'res.currency', string="Devise", required=True,
        default=lambda self: self.env.company.currency_id,
    )
    total_value = fields.Monetary(
        string="Valeur totale du programme", currency_field='currency_id',
        help="CA potentiel du programme (valeur du stock complet).",
    )
    signed_revenue = fields.Monetary(
        string="Chiffre d'affaires signe", currency_field='currency_id',
    )

    # --- Calendrier & administratif -----------------------------------
    start_date = fields.Date(string="Date de demarrage")
    delivery_date = fields.Date(string="Livraison prevue")
    works_progress = fields.Integer(string="Avancement travaux (%)", default=0)
    building_permit = fields.Char(string="Permis de construire")
    notary_office = fields.Char(string="Office notarial")
    gfa_reference = fields.Char(string="Garantie financiere d'achevement (GFA)")

    # --- Prestations & acteurs ----------------------------------------
    amenity_ids = fields.Many2many(
        'civora.program.amenity', string="Prestations & equipements",
    )
    stakeholder_ids = fields.One2many(
        'civora.program.stakeholder', 'program_id', string="Acteurs du projet",
    )

    # --- Collections --------------------------------------------------
    lot_ids = fields.One2many('civora.program.lot', 'program_id', string="Lots")
    phase_ids = fields.One2many('civora.program.phase', 'program_id', string="Phases chantier")
    milestone_ids = fields.One2many('civora.program.milestone', 'program_id', string="Echeancier VEFA")
    call_ids = fields.One2many('civora.program.call', 'program_id', string="Appels de fonds")
    guarantee_ids = fields.One2many('civora.program.guarantee', 'program_id', string="Garanties")
    document_ids = fields.One2many('civora.program.document', 'program_id', string="Documents")

    # --- Parametres de commission -------------------------------------
    commission_rate = fields.Float(string="Taux de commercialisation (%)", default=4.0)
    reservation_fee = fields.Monetary(string="Frais de reservation", currency_field='currency_id')
    marketing_budget = fields.Monetary(string="Budget marketing", currency_field='currency_id')
    negotiator_share = fields.Float(string="Part negociateur (%)", default=35.0)
    closing_bonus = fields.Monetary(string="Bonus closing VEFA", currency_field='currency_id')
    internal_notes = fields.Text(string="Notes internes")

    company_id = fields.Many2one(
        'res.company', string="Societe", required=True, index=True,
        default=lambda self: self.env.company,
    )

    # --- Champs calcules : stock reel ---------------------------------
    lot_count = fields.Integer(string="Lots au stock", compute='_compute_lot_stats', store=True)
    lot_available = fields.Integer(string="Lots disponibles", compute='_compute_lot_stats', store=True)
    lot_optioned = fields.Integer(string="Lots optionnes", compute='_compute_lot_stats', store=True)
    lot_reserved = fields.Integer(string="Lots reserves (stock)", compute='_compute_lot_stats', store=True)
    lot_sold = fields.Integer(string="Lots vendus (stock)", compute='_compute_lot_stats', store=True)
    lot_blocked = fields.Integer(string="Lots bloques", compute='_compute_lot_stats', store=True)

    stock_value = fields.Monetary(
        string="Valeur totale du stock", currency_field='currency_id',
        compute='_compute_lot_stats', store=True,
    )
    sold_value = fields.Monetary(
        string="CA signe (stock)", currency_field='currency_id',
        compute='_compute_lot_stats', store=True,
    )
    optioned_value = fields.Monetary(
        string="CA optionne / reserve", currency_field='currency_id',
        compute='_compute_lot_stats', store=True,
    )

    commercial_progress = fields.Integer(
        string="Commercialisation (%)", compute='_compute_progress', store=True,
    )
    absorption_rate = fields.Integer(
        string="Taux d'absorption (%)", compute='_compute_progress', store=True,
    )
    realization_rate = fields.Integer(
        string="Taux de realisation (%)", compute='_compute_progress', store=True,
    )
    phase_progress = fields.Integer(
        string="Avancement moyen des phases (%)", compute='_compute_phase_progress', store=True,
    )

    _ref_uniq = models.Constraint(
        'unique (ref, company_id)',
        "La reference du programme doit etre unique par societe.",
    )
    _works_progress_range = models.Constraint(
        'check (works_progress >= 0 and works_progress <= 100)',
        "L'avancement des travaux doit etre compris entre 0 et 100.",
    )

    # ------------------------------------------------------------------
    # Calculs
    # ------------------------------------------------------------------
    @api.depends('name')
    def _compute_slug(self):
        for rec in self:
            base = (rec.name or "").strip().lower()
            out = []
            for ch in base:
                if ch.isalnum():
                    out.append(ch)
                elif ch in " -_'":
                    out.append('-')
            slug = ''.join(out)
            while '--' in slug:
                slug = slug.replace('--', '-')
            rec.slug = slug.strip('-') or False

    @api.depends('lot_ids', 'lot_ids.status', 'lot_ids.price')
    def _compute_lot_stats(self):
        for rec in self:
            lots = rec.lot_ids
            rec.lot_count = len(lots)
            rec.lot_available = len(lots.filtered(lambda l: l.status == 'disponible'))
            rec.lot_optioned = len(lots.filtered(lambda l: l.status == 'optionne'))
            rec.lot_reserved = len(lots.filtered(lambda l: l.status == 'reserve'))
            rec.lot_sold = len(lots.filtered(lambda l: l.status == 'vendu'))
            rec.lot_blocked = len(lots.filtered(lambda l: l.status == 'bloque'))
            rec.stock_value = sum(lots.mapped('price'))
            rec.sold_value = sum(lots.filtered(lambda l: l.status == 'vendu').mapped('price'))
            rec.optioned_value = sum(
                lots.filtered(lambda l: l.status in ('optionne', 'reserve')).mapped('price')
            )

    @api.depends('total_lots', 'sold_lots', 'reserved_lots',
                 'lot_count', 'lot_sold', 'lot_reserved', 'lot_optioned',
                 'stock_value', 'sold_value', 'total_value', 'signed_revenue')
    def _compute_progress(self):
        for rec in self:
            # Commercialisation : part des lots places sur le total annonce.
            total = rec.total_lots or rec.lot_count
            placed = (rec.sold_lots or 0) + (rec.reserved_lots or 0)
            if not (rec.sold_lots or rec.reserved_lots):
                placed = rec.lot_sold + rec.lot_reserved
            rec.commercial_progress = round(placed * 100.0 / total) if total else 0

            # Absorption : part des lots effectivement vendus.
            sold = rec.sold_lots or rec.lot_sold
            rec.absorption_rate = round(sold * 100.0 / total) if total else 0

            # Realisation : CA signe rapporte a la valeur du programme.
            base = rec.total_value or rec.stock_value
            signed = rec.signed_revenue or rec.sold_value
            rec.realization_rate = round(signed * 100.0 / base) if base else 0

    @api.depends('phase_ids', 'phase_ids.progress')
    def _compute_phase_progress(self):
        for rec in self:
            phases = rec.phase_ids
            rec.phase_progress = round(sum(phases.mapped('progress')) / len(phases)) if phases else 0

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('ref') or vals.get('ref') == "Nouveau":
                vals['ref'] = self.env['ir.sequence'].next_by_code('civora.program') or "PRG-000"
        return super().create(vals_list)

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        for rec, vals in zip(self, vals_list):
            vals.setdefault('name', rec.name)
            vals['ref'] = "Nouveau"
        return vals_list

    # ------------------------------------------------------------------
    # Actions metier
    # ------------------------------------------------------------------
    def action_seed_standard_schedule(self):
        """Initialise l'echeancier VEFA usuel (5 / 35 / 70 / 95 / 100 %)."""
        self.ensure_one()
        if self.milestone_ids:
            return False
        standard = [
            ("Signature / réservation", 5),
            ("Achèvement des fondations", 35),
            ("Mise hors d'eau", 70),
            ("Achèvement des travaux", 95),
            ("Livraison", 100),
        ]
        Milestone = self.env['civora.program.milestone']
        for idx, (label, pct) in enumerate(standard, start=1):
            Milestone.create({
                'program_id': self.id,
                'name': label,
                'sequence': idx,
                'cumulative_pct': pct,
            })
        return True


class CivoraProgramStakeholder(models.Model):
    """Acteur du projet : maitrise d'ouvrage, architecte, BET, notaire..."""
    _name = 'civora.program.stakeholder'
    _description = "Acteur de programme CIVORA"
    _order = 'sequence, id'

    program_id = fields.Many2one(
        'civora.program', string="Programme", required=True,
        ondelete='cascade', index=True,
    )
    sequence = fields.Integer(string="Sequence", default=10)
    role = fields.Char(string="Role", required=True)
    name = fields.Char(string="Nom & prenom")
    phone = fields.Char(string="Telephone")
    email = fields.Char(string="Email")
    partner_id = fields.Many2one('res.partner', string="Contact CIVORA")
    company_id = fields.Many2one(
        'res.company', string="Societe", related='program_id.company_id', store=True,
    )
