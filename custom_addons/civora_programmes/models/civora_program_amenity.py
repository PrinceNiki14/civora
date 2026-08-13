# -*- coding: utf-8 -*-
from odoo import fields, models


class CivoraProgramAmenity(models.Model):
    """Prestation / equipement propose par un programme (piscine, salle de sport...)."""
    _name = 'civora.program.amenity'
    _description = "Prestation de programme CIVORA"
    _order = 'sequence, name'

    name = fields.Char(string="Prestation", required=True, translate=True)
    sequence = fields.Integer(string="Sequence", default=10)
    active = fields.Boolean(string="Actif", default=True)
    company_id = fields.Many2one(
        'res.company',
        string="Societe",
        help="Vide = prestation partagee par toutes les societes.",
    )
