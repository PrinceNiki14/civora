# -*- coding: utf-8 -*-
import uuid

from odoo import api, fields, models
from odoo.exceptions import ValidationError

# Statut d'occupation du bien (workflow simple).
CIVORA_PROPERTY_STATUS = [
    ('disponible', "Disponible"),
    ('loue', "Loué"),
    ('saisonnier', "Saisonnier"),
]


class CivoraProperty(models.Model):
    """Bien immobilier du parc CIVORA (appartement, villa, bureau, studio...).

    Objet pivot du bloc Immobilier : reference par Locations, Saisonnier,
    Ventes, PropRietaires et Pipeline (via des modules ulterieurs).
    """
    _name = 'civora.property'
    _description = "Bien immobilier CIVORA"
    _order = 'name'
    _check_company_auto = True

    name = fields.Char(string="Nom", required=True, index=True)
    ref = fields.Char(string="Référence", copy=False, index=True, help="Référence interne (ex: BIEN-001).")
    property_type_id = fields.Many2one('civora.property.type', string="Type", index=True)
    transaction = fields.Selection([
        ('vente', "À vendre"),
        ('location', "À louer"),
        ('saisonnier', "Location saisonnière"),
    ], string="Transaction")
    mandate_type = fields.Selection([
        ('exclusif', "Exclusif"),
        ('simple', "Simple"),
        ('delegue', "Délégué"),
    ], string="Mandat")
    status = fields.Selection(
        CIVORA_PROPERTY_STATUS,
        string="Statut",
        required=True,
        default='disponible',
        index=True,
    )

    # --- Localisation ---
    city = fields.Char(string="Ville")
    neighborhood = fields.Char(string="Quartier")
    street = fields.Char(string="Adresse")
    latitude = fields.Float(string="Latitude", digits=(10, 7))
    longitude = fields.Float(string="Longitude", digits=(10, 7))

    # --- Caracteristiques ---
    surface = fields.Float(string="Surface (m²)")
    rooms = fields.Integer(string="Pièces")
    bedrooms = fields.Integer(string="Chambres")
    bathrooms = fields.Integer(string="Salles de bain")
    year_built = fields.Integer(string="Année de construction")

    # --- Pricing / rentabilite ---
    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    price = fields.Monetary(
        string="Prix",
        currency_field='currency_id',
        help="Prix de vente ou valeur du bien.",
    )
    monthly_revenue = fields.Monetary(
        string="Revenu mensuel",
        currency_field='currency_id',
        help="Loyer / revenu mensuel genere par le bien.",
    )
    yield_rate = fields.Float(
        string="Rentabilité (%)",
        compute='_compute_yield_rate',
        store=True,
        help="Rendement annuel brut = revenu mensuel x 12 / prix.",
    )

    # --- Relations ---
    owner_id = fields.Many2one(
        'res.partner',
        string="Propriétaire",
        domain=[('civora_is_contact', '=', True)],
        help="Propriétaire du bien (contact CIVORA).",
    )
    agent_id = fields.Many2one(
        'res.users',
        string="Agent référent",
        help="Agent en charge du bien (notifié des demandes de visite).",
    )
    tenant_id = fields.Many2one(
        'res.partner',
        string="Locataire actuel",
        domain=[('civora_is_contact', '=', True)],
        help="Locataire occupant actuellement le bien (le bail complet viendra avec le module Locations).",
    )

    # --- Media / contenu ---
    image_ids = fields.One2many('civora.property.image', 'property_id', string="Photos")
    image_128 = fields.Image(
        string="Vignette",
        compute='_compute_cover',
        store=True,
        max_width=128,
        max_height=128,
    )
    image_512 = fields.Image(
        string="Couverture",
        compute='_compute_cover',
        store=True,
        max_width=512,
        max_height=512,
    )
    description = fields.Text(string="Description")
    note = fields.Text(string="Notes internes")

    active = fields.Boolean(string="Actif", default=True)

    # --- Conditions de location / saisonnier ---
    rental_deposit = fields.Char(string="Caution")
    rental_charges = fields.Char(string="Charges")
    rental_min_stay = fields.Char(string="Durée minimale")
    rental_advance = fields.Char(string="Avance")
    rental_agency_fees = fields.Char(string="Frais d'agence")

    # --- Conditions de vente ---
    sale_negotiable = fields.Char(string="Négociation")
    sale_notary = fields.Char(string="Frais de notaire")
    sale_payment = fields.Char(string="Modalités de paiement")
    sale_handover = fields.Char(string="Remise des clés")

    # --- Immeuble & unités ---
    # Un bien peut etre soit un immeuble (is_building=True, contient des unites
    # via unit_ids), soit une unite rattachee a un immeuble (parent_id defini),
    # soit un bien autonome (ni l'un ni l'autre).
    is_building = fields.Boolean(string="Immeuble (avec unités)", default=False)
    floors_count = fields.Integer(string="Nombre d'étages")
    total_units = fields.Integer(string="Nombre d'unités prévues")
    parent_id = fields.Many2one(
        'civora.property',
        string="Immeuble parent",
        ondelete='set null',
        index=True,
        check_company=True,
        domain=[('is_building', '=', True)],
        help="Si renseigné, ce bien est une unité de cet immeuble.",
    )
    unit_ids = fields.One2many('civora.property', 'parent_id', string="Unités")
    unit_count = fields.Integer(string="Nb unités", compute='_compute_unit_count')
    units_occupied = fields.Integer(
        string="Unités occupées", compute='_compute_unit_count',
        help="Nombre d'unités louées ou en saisonnier (immeuble uniquement).",
    )
    occupancy_rate = fields.Float(
        string="Taux d'occupation (%)", compute='_compute_unit_count',
        help="Part des unités occupées sur le total des unités rattachées.",
    )
    floor = fields.Integer(string="Étage")
    unit_number = fields.Char(string="N° d'unité")

    # --- Partage public ---
    access_token = fields.Char(string="Jeton de partage", copy=False, index=True, readonly=True)
    is_shared = fields.Boolean(string="Partage public actif", default=False, copy=False)
    company_id = fields.Many2one(
        'res.company',
        string="Societe",
        required=True,
        index=True,
        default=lambda self: self.env.company,
        help="Societe proprietaire du bien (isolation multi-societe).",
    )

    @api.depends('monthly_revenue', 'price')
    def _compute_yield_rate(self):
        for prop in self:
            prop.yield_rate = (prop.monthly_revenue * 12.0 / prop.price * 100.0) if prop.price else 0.0

    @api.depends('image_ids.image', 'image_ids.sequence')
    def _compute_cover(self):
        for prop in self:
            first = prop.image_ids.sorted(lambda r: (r.sequence, r.id))[:1]
            cover = first.image if first else False
            prop.image_128 = cover
            prop.image_512 = cover

    @api.depends('unit_ids', 'unit_ids.status')
    def _compute_unit_count(self):
        for prop in self:
            units = prop.unit_ids
            prop.unit_count = len(units)
            occupied = len(units.filtered(lambda u: u.status in ('loue', 'saisonnier')))
            prop.units_occupied = occupied
            prop.occupancy_rate = round((occupied / len(units)) * 100, 1) if units else 0.0

    @api.constrains('parent_id', 'is_building')
    def _check_building_hierarchy(self):
        for prop in self:
            # Une unite ne peut pas etre son propre parent, ni creer un cycle.
            if prop.parent_id:
                if prop.parent_id == prop:
                    raise ValidationError("Un bien ne peut pas être sa propre unité.")
                ancestor = prop.parent_id
                seen = set()
                while ancestor:
                    if ancestor.id in seen:
                        break
                    if ancestor == prop:
                        raise ValidationError(
                            "Hiérarchie d'immeuble invalide : cycle détecté entre les biens."
                        )
                    seen.add(ancestor.id)
                    ancestor = ancestor.parent_id
                # Le parent doit reellement etre un immeuble.
                if not prop.parent_id.is_building:
                    raise ValidationError(
                        "Le bien parent doit être marqué comme immeuble pour héberger des unités."
                    )
            # Un immeuble ne peut pas etre lui-meme une unite d'un autre bien.
            if prop.is_building and prop.parent_id:
                raise ValidationError(
                    "Un immeuble ne peut pas être en même temps une unité d'un autre immeuble."
                )

    # --- Partage public ------------------------------------------------
    def _ensure_share_token(self):
        self.ensure_one()
        if not self.access_token:
            self.access_token = uuid.uuid4().hex
        return self.access_token

    def _share_url(self):
        self.ensure_one()
        if not self.access_token:
            return ""
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url') or ""
        return base + "/civora/bien/" + self.access_token

    def _is_publicly_accessible(self):
        """Un bien est consultable publiquement s'il est partage lui-meme,
        ou s'il s'agit d'une unite dont l'immeuble parent est partage
        (acces herite : departager l'immeuble coupe l'acces aux unites)."""
        self.ensure_one()
        if self.is_shared:
            return True
        if self.parent_id and self.parent_id.is_shared:
            return True
        return False

    def _public_units(self):
        """Unites d'un immeuble a exposer sur la fiche publique.
        Toutes les unites sont listees quand l'immeuble est partage."""
        self.ensure_one()
        if not self.is_building:
            return self.browse()
        return self.unit_ids.sorted(lambda u: (u.floor or 0, u.unit_number or "", u.name or ""))

    @api.model
    def share_get(self, prop_id):
        prop = self.browse(prop_id).exists()
        if not prop:
            return {}
        return {"is_shared": prop.is_shared, "url": prop._share_url()}

    @api.model
    def share_set(self, prop_id, enable):
        prop = self.browse(prop_id).exists()
        if not prop:
            return {}
        if enable:
            prop._ensure_share_token()
            prop.is_shared = True
            # Pre-genere un token pour chaque unite afin que les liens
            # "Voir la fiche" / "Partager" fonctionnent immediatement.
            if prop.is_building:
                for unit in prop.unit_ids:
                    unit._ensure_share_token()
        else:
            prop.is_shared = False
        return {"is_shared": prop.is_shared, "url": prop._share_url()}

    # --- Immeuble : creation d'unites ---------------------------------
    def _inherited_unit_vals(self):
        """Valeurs heritees du parent (immeuble) pour une nouvelle unite."""
        self.ensure_one()
        return {
            'parent_id': self.id,
            'company_id': self.company_id.id,
            'city': self.city,
            'neighborhood': self.neighborhood,
            'street': self.street,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'owner_id': self.owner_id.id if self.owner_id else False,
            'agent_id': self.agent_id.id if self.agent_id else False,
        }

    @api.model
    def create_unit(self, building_id, vals):
        """Cree une unite rattachee a un immeuble, en heritant de sa
        localisation et de son proprietaire/agent. Appele depuis l'UI OWL."""
        building = self.browse(building_id).exists()
        if not building or not building.is_building:
            raise ValidationError("L'immeuble parent est introuvable ou invalide.")
        unit_number = (vals.get('unit_number') or "").strip()
        payload = building._inherited_unit_vals()
        payload.update({
            'name': vals.get('name') or (
                "%s — Apt %s" % (building.name, unit_number) if unit_number else building.name
            ),
            'ref': vals.get('ref') or (
                "%s-%s" % (building.ref, unit_number) if building.ref and unit_number else False
            ),
            'unit_number': unit_number or False,
            'floor': vals.get('floor') or 0,
            'bedrooms': vals.get('bedrooms') or 0,
            'bathrooms': vals.get('bathrooms') or 0,
            'surface': vals.get('surface') or 0,
            'price': vals.get('price') or 0,
            'monthly_revenue': vals.get('monthly_revenue') or 0,
            'transaction': vals.get('transaction') or False,
            'status': vals.get('status') or 'disponible',
            'description': vals.get('description') or False,
        })
        unit = self.create([payload])
        return unit.id

    @api.model
    def duplicate_units(self, building_id, template_id, options):
        """Genere en masse plusieurs unites a partir d'une unite modele.
        options = {count, start_number, increment, per_floor}."""
        building = self.browse(building_id).exists()
        if not building or not building.is_building:
            raise ValidationError("L'immeuble parent est introuvable ou invalide.")
        template = self.browse(template_id).exists()
        if not template:
            raise ValidationError("Sélectionnez une unité modèle à dupliquer.")
        count = int(options.get('count') or 0)
        if count <= 0 or count > 100:
            raise ValidationError("Le nombre d'unités doit être compris entre 1 et 100.")
        start = int(options.get('start_number') or 101)
        increment = int(options.get('increment') or 1)
        per_floor = int(options.get('per_floor') or 0)

        created_ids = []
        for i in range(count):
            num = start + i * increment
            unit_number = str(num)
            floor = (num // 100) if per_floor > 0 else template.floor
            payload = building._inherited_unit_vals()
            payload.update({
                'name': "%s — Apt %s" % (building.name, unit_number),
                'ref': "%s-%s" % (building.ref, unit_number) if building.ref else False,
                'unit_number': unit_number,
                'floor': floor,
                'bedrooms': template.bedrooms,
                'bathrooms': template.bathrooms,
                'surface': template.surface,
                'price': template.price,
                'monthly_revenue': template.monthly_revenue,
                'transaction': template.transaction,
                'status': 'disponible',
            })
            unit = self.create([payload])
            created_ids.append(unit.id)
        return created_ids

    _price_positive = models.Constraint(
        'check (price >= 0)',
        "Le prix ne peut pas etre negatif.",
    )
    _revenue_positive = models.Constraint(
        'check (monthly_revenue >= 0)',
        "Le revenu mensuel ne peut pas etre negatif.",
    )
