# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CivoraProperty(models.Model):
    """Extension de civora.property par le module Locations.

    Ajoute le lien vers les baux et des indicateurs de revenu locatif REEL
    (issu des baux actifs), par opposition au champ theorique monthly_revenue.
    Ces champs alimentent la fiche 360 d'un immeuble.
    """
    _inherit = 'civora.property'

    lease_ids = fields.One2many('civora.lease', 'property_id', string="Baux")

    active_lease_id = fields.Many2one(
        'civora.lease', string="Bail actif", compute='_compute_active_lease',
        help="Bail actif le plus récent rattaché à ce bien.",
    )
    active_lease_rent = fields.Float(
        string="Loyer contractuel", compute='_compute_active_lease',
        help="Loyer du bail actif (0 si le bien n'est pas loué sous contrat).",
    )

    building_lease_revenue = fields.Float(
        string="Revenu locatif réel", compute='_compute_building_lease',
        help="Pour un immeuble : somme des loyers des baux actifs de ses unités.",
    )
    building_units_leased = fields.Integer(
        string="Unités sous bail actif", compute='_compute_building_lease',
    )

    building_collected = fields.Float(
        string="Loyers encaissés (cumul)", compute='_compute_building_collection',
        help="Pour un immeuble : total encaissé sur les baux actifs de ses unités.",
    )
    building_expected = fields.Float(
        string="Loyers attendus (cumul)", compute='_compute_building_collection',
        help="Pour un immeuble : total attendu sur les baux actifs de ses unités.",
    )
    building_collection_rate = fields.Float(
        string="Taux de recouvrement (%)", compute='_compute_building_collection',
        help="Part des loyers réellement encaissés sur les loyers attendus.",
    )
    building_arrears = fields.Float(
        string="Impayés (cumul)", compute='_compute_building_collection',
        help="Pour un immeuble : total des impayés sur les baux actifs de ses unités.",
    )

    @api.depends('lease_ids', 'lease_ids.state', 'lease_ids.rent', 'lease_ids.date_start')
    def _compute_active_lease(self):
        for prop in self:
            active = prop.lease_ids.filtered(lambda l: l.state == 'active')
            active = active.sorted('date_start', reverse=True)[:1]
            prop.active_lease_id = active.id if active else False
            prop.active_lease_rent = active.rent if active else 0.0

    @api.depends(
        'is_building', 'unit_ids',
        'unit_ids.lease_ids.state', 'unit_ids.lease_ids.rent',
    )
    def _compute_building_lease(self):
        for prop in self:
            if not prop.is_building:
                prop.building_lease_revenue = 0.0
                prop.building_units_leased = 0
                continue
            total = 0.0
            leased = 0
            for unit in prop.unit_ids:
                active = unit.lease_ids.filtered(lambda l: l.state == 'active')
                active = active.sorted('date_start', reverse=True)[:1]
                if active:
                    total += active.rent
                    leased += 1
            prop.building_lease_revenue = total
            prop.building_units_leased = leased

    @api.depends(
        'is_building', 'unit_ids',
        'unit_ids.lease_ids.state',
        'unit_ids.lease_ids.total_paid',
        'unit_ids.lease_ids.total_expected',
        'unit_ids.lease_ids.arrears_amount',
    )
    def _compute_building_collection(self):
        for prop in self:
            if not prop.is_building:
                prop.building_collected = 0.0
                prop.building_expected = 0.0
                prop.building_collection_rate = 0.0
                prop.building_arrears = 0.0
                continue
            collected = 0.0
            expected = 0.0
            arrears = 0.0
            for unit in prop.unit_ids:
                for lease in unit.lease_ids.filtered(lambda l: l.state == 'active'):
                    collected += lease.total_paid
                    expected += lease.total_expected
                    arrears += lease.arrears_amount
            prop.building_collected = collected
            prop.building_expected = expected
            prop.building_arrears = arrears
            prop.building_collection_rate = (
                min(100.0, round((collected / expected) * 100, 1)) if expected else 0.0
            )
