# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CivoraSeasonalTariff(models.Model):
    _name = 'civora.seasonal.tariff'
    _description = 'Tarif saisonnier'
    _order = 'date_start asc'
    _check_company_auto = True

    name = fields.Char(string="Libellé", required=True)
    property_id = fields.Many2one(
        'civora.property', string="Bien", required=True,
        check_company=True, ondelete='cascade')
    season = fields.Selection([
        ('basse', 'Basse saison'),
        ('moyenne', 'Moyenne saison'),
        ('haute', 'Haute saison'),
        ('fete', 'Fêtes / Événements'),
    ], string="Saison", required=True)
    date_start = fields.Date(string="Début", required=True)
    date_end = fields.Date(string="Fin", required=True)
    tariff_night = fields.Integer(
        string="Tarif / nuit (FCFA)", required=True)
    min_nights = fields.Integer(
        string="Nuitées minimum", default=1)
    company_id = fields.Many2one(
        'res.company', string="Société",
        default=lambda self: self.env.company, required=True)

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_end <= rec.date_start:
                raise ValidationError(
                    "La date de fin doit être postérieure à la date de début.")
