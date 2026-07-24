# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import timedelta


class CivoraPropertySeasonal(models.Model):
    _inherit = 'civora.property'

    reservation_ids = fields.One2many(
        'civora.reservation', 'property_id', string="Réservations")
    seasonal_tariff_ids = fields.One2many(
        'civora.seasonal.tariff', 'property_id', string="Tarifs saisonniers")
    default_tariff_night = fields.Integer(
        string="Tarif par défaut / nuit (FCFA)")
    reservation_count = fields.Integer(
        compute='_compute_seasonal_stats', store=False)
    seasonal_revenue = fields.Integer(
        compute='_compute_seasonal_stats', store=False)
    seasonal_avg_rating = fields.Float(
        compute='_compute_seasonal_stats', store=False)
    seasonal_occupation_rate = fields.Float(
        compute='_compute_seasonal_stats', store=False)

    def _compute_seasonal_stats(self):
        for prop in self:
            reservations = prop.reservation_ids.filtered(
                lambda r: r.state not in ('cancelled', 'draft'))
            prop.reservation_count = len(reservations)
            prop.seasonal_revenue = sum(reservations.mapped('total_amount'))

            reviews = self.env['civora.reservation.review'].search([
                ('property_id', '=', prop.id)])
            if reviews:
                prop.seasonal_avg_rating = round(
                    sum(reviews.mapped('rating')) / len(reviews), 1)
            else:
                prop.seasonal_avg_rating = 0.0

            today = fields.Date.today()
            period_start = today - timedelta(days=90)
            period_days = 90
            booked_nights = sum(
                r.num_nights for r in reservations
                if r.checkin_date and r.checkin_date >= period_start)
            prop.seasonal_occupation_rate = round(
                (booked_nights / period_days * 100) if period_days else 0, 1)

    @api.model
    def get_seasonal_properties(self):
        props = self.search([
            ('transaction', '=', 'saisonnier'),
        ])
        result = []
        for p in props:
            p._compute_seasonal_stats()
            result.append({
                'id': p.id,
                'name': p.name,
                'ref': p.ref,
                'city': p.city or '',
                'neighborhood': p.neighborhood or '',
                'default_tariff_night': p.default_tariff_night,
                'reservation_count': p.reservation_count,
                'seasonal_revenue': p.seasonal_revenue,
                'seasonal_avg_rating': p.seasonal_avg_rating,
                'seasonal_occupation_rate': p.seasonal_occupation_rate,
            })
        return result
