# -*- coding: utf-8 -*-
from odoo import api, fields, models

# Typologie du lot (alignee sur le selecteur de la modale "Nouveau lot").
CIVORA_LOT_TYPE = [
    ('studio', "Studio"),
    ('t1', "T1"),
    ('t2', "T2"),
    ('t3', "T3"),
    ('t4', "T4"),
    ('t5', "T5"),
    ('duplex', "Duplex"),
    ('villa', "Villa"),
    ('local', "Local"),
]

# Statut commercial du lot (pilote le plan de masse et les compteurs).
CIVORA_LOT_STATUS = [
    ('disponible', "Disponible"),
    ('optionne', "Optionne"),
    ('reserve', "Reserve"),
    ('vendu', "Vendu"),
    ('bloque', "Bloque"),
]

CIVORA_LOT_ORIENTATION = [
    ('nord', "Nord"),
    ('ne', "N-E"),
    ('est', "Est"),
    ('se', "S-E"),
    ('sud', "Sud"),
    ('so', "S-O"),
    ('ouest', "Ouest"),
    ('no', "N-O"),
]


class CivoraProgramLot(models.Model):
    """Lot d'un programme : appartement, duplex, villa ou local commercial."""
    _name = 'civora.program.lot'
    _description = "Lot de programme CIVORA"
    _order = 'building, floor, name'
    _check_company_auto = True

    program_id = fields.Many2one(
        'civora.program', string="Programme", required=True,
        ondelete='cascade', index=True,
    )
    name = fields.Char(string="N de lot", required=True, index=True)
    building = fields.Char(string="Batiment / ilot", default="A", index=True)
    floor = fields.Integer(string="Etage", default=0, help="0 = rez-de-chaussee.")
    lot_type = fields.Selection(CIVORA_LOT_TYPE, string="Type", default='t3', required=True)
    status = fields.Selection(
        CIVORA_LOT_STATUS, string="Statut", default='disponible', required=True, index=True,
    )

    # --- Surfaces & composition ---------------------------------------
    surface = fields.Float(string="Surface habitable (m2)")
    rooms = fields.Integer(string="Pieces")
    bathrooms = fields.Integer(string="Salles d'eau")
    balcony = fields.Float(string="Balcon (m2)")
    terrace = fields.Float(string="Terrasse (m2)")
    parking = fields.Integer(string="Parking (places)")

    # --- Exposition & vue ---------------------------------------------
    orientation = fields.Selection(CIVORA_LOT_ORIENTATION, string="Orientation")
    exposure = fields.Char(string="Exposition", help="Ex : traversant.")
    view = fields.Char(string="Vue", help="Ex : lagune, jardin.")

    # --- Prix & acquereur ---------------------------------------------
    currency_id = fields.Many2one(
        'res.currency', string="Devise", related='program_id.currency_id',
        store=True, readonly=True,
    )
    price = fields.Monetary(string="Prix", currency_field='currency_id')
    buyer_id = fields.Many2one('res.partner', string="Acquereur")
    buyer_name = fields.Char(string="Acquereur (libelle)")

    # --- Contenu ------------------------------------------------------
    features = fields.Text(
        string="Caracteristiques & prestations",
        help="Une caracteristique par ligne (dressing, cellier, etage noble...).",
    )
    photo_urls = fields.Text(string="Photos (URL)", help="Une URL par ligne.")
    notes = fields.Text(string="Notes")

    company_id = fields.Many2one(
        'res.company', string="Societe", related='program_id.company_id',
        store=True, index=True,
    )

    floor_label = fields.Char(string="Niveau", compute='_compute_floor_label', store=True)

    _name_uniq = models.Constraint(
        'unique (program_id, name)',
        "Deux lots d'un meme programme ne peuvent pas porter le meme numero.",
    )
    _price_positive = models.Constraint(
        'check (price >= 0)',
        "Le prix du lot ne peut pas etre negatif.",
    )

    @api.depends('floor')
    def _compute_floor_label(self):
        for rec in self:
            rec.floor_label = "RDC" if not rec.floor else "R+%s" % rec.floor
