# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CivoraReservationReview(models.Model):
    _name = 'civora.reservation.review'
    _description = 'Avis voyageur'
    _order = 'date desc'
    _check_company_auto = True

    reservation_id = fields.Many2one(
        'civora.reservation', string="Réservation",
        required=True, ondelete='cascade')
    guest_id = fields.Many2one(
        'res.partner', string="Voyageur",
        related='reservation_id.guest_id', store=True, readonly=True)
    property_id = fields.Many2one(
        'civora.property', string="Bien",
        related='reservation_id.property_id', store=True, readonly=True)

    rating = fields.Integer(
        string="Note globale", required=True, default=5)
    cleanliness_rating = fields.Integer(
        string="Propreté", default=5)
    location_rating = fields.Integer(
        string="Emplacement", default=5)
    comfort_rating = fields.Integer(
        string="Confort", default=5)
    value_rating = fields.Integer(
        string="Rapport qualité/prix", default=5)

    comment = fields.Text(string="Commentaire")
    internal_note = fields.Text(string="Note interne")
    date = fields.Date(
        string="Date", default=fields.Date.today, required=True)

    company_id = fields.Many2one(
        'res.company', string="Société",
        related='reservation_id.company_id', store=True, readonly=True)

    @api.constrains('rating', 'cleanliness_rating', 'location_rating',
                     'comfort_rating', 'value_rating')
    def _check_ratings(self):
        for rec in self:
            for field_name in ['rating', 'cleanliness_rating', 'location_rating',
                               'comfort_rating', 'value_rating']:
                val = getattr(rec, field_name)
                if val < 1 or val > 5:
                    raise models.ValidationError(
                        "Les notes doivent être comprises entre 1 et 5.")
