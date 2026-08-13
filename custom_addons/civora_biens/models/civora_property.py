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

    name = fields.Char(
        string="Nom", required=True, index=True,
        compute='_compute_name', store=True, readonly=True, precompute=True,
        help="Composé automatiquement : type + nombre de pièces + quartier.",
    )
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
    maps_url = fields.Char(
        string="Lien Google Maps",
        help="Lien Google Maps ou OpenStreetMap complet. La position (lat/long) "
             "est extraite automatiquement quand le lien est colle dans le formulaire.",
    )

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

    # ── Documents juridiques (vente) ────────────────────────────────────
    sale_doc_ids = fields.Many2many(
        'civora.sale.doc.type', 'civora_property_sale_doc_rel',
        'property_id', 'doc_type_id', string="Documents juridiques",
        help="Pieces disponibles pour ce bien. Ne concerne que les biens en vente.",
    )
    sale_doc_count = fields.Integer(
        string="Documents fournis", compute='_compute_sale_docs', store=True)
    sale_docs_ok = fields.Boolean(
        string="Dossier juridique suffisant", compute='_compute_sale_docs', store=True,
        help="Au moins deux pieces, dont une piece maitresse (ACD, Titre Foncier "
             "ou Certificat de propriete). Un dossier incomplet expose l'agence "
             "autant que l'acquereur.",
    )

    @api.depends('sale_doc_ids', 'sale_doc_ids.is_essential', 'transaction')
    def _compute_sale_docs(self):
        for p in self:
            docs = p.sale_doc_ids
            p.sale_doc_count = len(docs)
            if p.transaction != 'vente':
                p.sale_docs_ok = False
                continue
            p.sale_docs_ok = bool(
                len(docs) >= 2 and any(d.is_essential for d in docs))

    # ══════════════════════════════════════════════════════════════════
    # Designation automatique
    # ══════════════════════════════════════════════════════════════════
    def _civora_build_name(self):
        """Compose le titre : type + nombre de pieces + quartier.

        On privilegie le QUARTIER a la ville : a Abidjan, la ville est la
        meme pour tout le portefeuille, et « Villa 5 pieces Abidjan » ne
        distingue rien. On retombe sur la ville si le quartier est absent.

        Cas particulier des unites d'immeuble : le numero d'appartement est
        conserve, sans quoi toutes les unites d'un meme batiment porteraient
        un titre identique et deviendraient impossibles a distinguer.
        """
        self.ensure_one()
        parts = []
        if self.property_type_id:
            parts.append(self.property_type_id.name or '')
        if self.rooms:
            parts.append("%d pièce%s" % (self.rooms, "s" if self.rooms > 1 else ""))

        unit_no = (self.unit_number or '').strip()
        if self.parent_id and unit_no:
            parts.append("Apt %s" % unit_no)
        else:
            place = (self.neighborhood or '').strip() or (self.city or '').strip()
            if place:
                parts.append(place)

        title = " ".join(p for p in parts if p).strip()
        # Le champ est requis : il ne doit jamais rester vide, meme sur un
        # bien tout juste esquisse.
        return title or "Bien à qualifier"

    @api.depends('property_type_id', 'property_type_id.name', 'rooms',
                 'neighborhood', 'city', 'unit_number', 'parent_id')
    def _compute_name(self):
        for prop in self:
            prop.name = prop._civora_build_name()

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
            # 'name' n'est plus ecrit ici : il est calcule a partir du type,
            # du nombre de pieces et du numero d'unite.
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
                # 'name' est calcule (cf. _compute_name)
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
    _ref_uniq = models.Constraint(
        'unique (ref, company_id)',
        "La reference du bien doit etre unique par societe.",
    )

    # ------------------------------------------------------------------
    # Reference automatique : PREFIX-00001 (padding 5)
    # ------------------------------------------------------------------
    _REF_PADDING = 5

    @api.model
    def _get_or_create_ref_sequence(self, ptype, company):
        """Retourne l'ir.sequence a utiliser pour generer la reference d'un bien
        du type et de la societe donnes. Cree la sequence si elle n'existe pas.
        """
        if not ptype or not company:
            return False
        code = 'civora.property.%s.%s' % (ptype.code or ptype.id, company.id)
        Seq = self.env['ir.sequence'].sudo()
        seq = Seq.with_context(active_test=False).search([('code', '=', code)], limit=1)
        prefix = (ptype.reference_prefix or 'REF').upper()
        if not seq:
            seq = Seq.create({
                'name': "CIVORA Bien - %s - %s" % (ptype.name or ptype.code or 'Type', company.name),
                'code': code,
                'prefix': '%s-' % prefix,
                'padding': self._REF_PADDING,
                'number_increment': 1,
                'number_next_actual': 1,
                'implementation': 'standard',
                'company_id': company.id,
            })
        else:
            # Assure la coherence du prefixe si l'agence a renomme.
            expected = '%s-' % prefix
            if seq.prefix != expected:
                seq.prefix = expected
            if seq.padding != self._REF_PADDING:
                seq.padding = self._REF_PADDING
        return seq

    @api.model_create_multi
    def create(self, vals_list):
        Type = self.env['civora.property.type'].sudo()
        Company = self.env['res.company'].sudo()
        for vals in vals_list:
            if vals.get('ref'):
                continue
            type_id = vals.get('property_type_id')
            company_id = vals.get('company_id') or self.env.company.id
            if not type_id:
                # Sans type, on ne peut pas generer : on laisse vide, l'utilisateur
                # pourra saisir manuellement ou re-editer le bien avec un type.
                continue
            ptype = Type.browse(type_id)
            company = Company.browse(company_id)
            if not ptype.exists() or not company.exists():
                continue
            seq = self._get_or_create_ref_sequence(ptype, company)
            if seq:
                vals['ref'] = seq.next_by_id()
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Suppression protegee (baux actifs / opportunites actives / unites-enfants)
    # ------------------------------------------------------------------
    def _get_blocking_counts(self):
        """Retourne pour chaque bien un dict des references bloquantes.

        Les modeles verifies ne sont pas dans les depends de civora_biens : on
        interroge dynamiquement pour ne pas creer de cycle de dependance.
        """
        self.ensure_one()
        counts = {'leases': 0, 'opportunities': 0, 'child_units': 0}

        # Baux actifs (civora_locations optionnel).
        if 'civora.lease' in self.env:
            Lease = self.env['civora.lease'].sudo()
            # Un bail est considere actif s'il n'est pas termine/annule.
            counts['leases'] = Lease.search_count([
                ('property_id', '=', self.id),
                ('state', 'not in', ['done', 'cancelled', 'termine', 'annule']),
            ])

        # Opportunites actives (civora_pipeline optionnel).
        if 'civora.opportunity' in self.env:
            Opp = self.env['civora.opportunity'].sudo()
            counts['opportunities'] = Opp.search_count([
                ('property_id', '=', self.id),
                ('is_won', '=', False),
                ('is_lost', '=', False),
            ])

        # Unites-enfants (immeuble contenant des lots).
        counts['child_units'] = self.search_count([('parent_id', '=', self.id)])
        return counts

    def action_delete_check(self):
        """Appele par l'ecran avant la suppression : renvoie un rapport clair.

        Retourne un dict :
          {
            'deletable': bool,
            'reason': str (message si non supprimable),
            'blocking': {'leases': N, 'opportunities': N, 'child_units': N}
          }
        """
        self.ensure_one()
        counts = self._get_blocking_counts()
        total = counts['leases'] + counts['opportunities'] + counts['child_units']
        if total == 0:
            return {'deletable': True, 'reason': '', 'blocking': counts}
        parts = []
        if counts['leases']:
            parts.append("%s bail(x) actif(s)" % counts['leases'])
        if counts['opportunities']:
            parts.append("%s opportunite(s) active(s)" % counts['opportunities'])
        if counts['child_units']:
            parts.append("%s unite(s) rattachee(s)" % counts['child_units'])
        reason = (
            "Ce bien ne peut pas etre supprime : "
            + ", ".join(parts)
            + ". Vous pouvez l'archiver a la place (le bien restera consultable mais "
            "sera masque des listes actives)."
        )
        return {'deletable': False, 'reason': reason, 'blocking': counts}

    def action_archive_property(self):
        """Archive un ou plusieurs biens (raccourci pour le drawer)."""
        for prop in self:
            prop.active = False
        return True

    def unlink(self):
        for prop in self:
            report = prop.action_delete_check()
            if not report['deletable']:
                from odoo.exceptions import UserError
                raise UserError(report['reason'])
        return super().unlink()
