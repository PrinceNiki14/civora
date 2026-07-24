# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CivoraReservation(models.Model):
    _name = 'civora.reservation'
    _description = 'Réservation saisonnière'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'checkin_date desc, id desc'
    _check_company_auto = True

    name = fields.Char(
        string="Référence", readonly=True, copy=False,
        default=lambda self: _('Nouveau'))
    property_id = fields.Many2one(
        'civora.property', string="Bien", required=True,
        check_company=True, tracking=True)
    guest_id = fields.Many2one(
        'res.partner', string="Voyageur", required=True, tracking=True)
    agent_id = fields.Many2one(
        'res.users', string="Agent", default=lambda self: self.env.user,
        tracking=True)
    owner_id = fields.Many2one(
        'res.partner', string="Propriétaire",
        related='property_id.owner_id', store=True, readonly=True)

    checkin_date = fields.Date(
        string="Arrivée", required=True, tracking=True)
    checkout_date = fields.Date(
        string="Départ", required=True, tracking=True)
    num_nights = fields.Integer(
        string="Nuitées", compute='_compute_num_nights', store=True)
    num_guests = fields.Integer(string="Voyageurs", default=1)

    tariff_night = fields.Integer(string="Tarif / nuit (FCFA)", required=True)
    total_amount = fields.Integer(
        string="Montant total (FCFA)",
        compute='_compute_total_amount', store=True)
    deposit_amount = fields.Integer(string="Caution (FCFA)")
    deposit_status = fields.Selection([
        ('pending', 'En attente'),
        ('collected', 'Encaissée'),
        ('returned', 'Restituée'),
        ('retained', 'Retenue'),
    ], string="Statut caution", default='pending')

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmée'),
        ('checkin', 'En séjour'),
        ('checkout', 'Terminée'),
        ('cancelled', 'Annulée'),
    ], string="Statut", default='draft', tracking=True, required=True)

    source = fields.Selection([
        ('direct', 'Direct'),
        ('airbnb', 'Airbnb'),
        ('booking', 'Booking.com'),
        ('whatsapp', 'WhatsApp'),
        ('referral', 'Référence'),
        ('other', 'Autre'),
    ], string="Source", default='direct')

    notes = fields.Text(string="Notes")
    access_instructions = fields.Text(string="Instructions d'accès")
    welcome_message_sent = fields.Boolean(string="Message d'accueil envoyé")

    review_ids = fields.One2many(
        'civora.reservation.review', 'reservation_id', string="Avis")
    cleaning_task_ids = fields.One2many(
        'civora.cleaning.task', 'reservation_id', string="Ménages")
    has_review = fields.Boolean(
        compute='_compute_has_review', store=True)
    guest_rating = fields.Float(
        string="Note voyageur",
        compute='_compute_has_review', store=True)

    company_id = fields.Many2one(
        'res.company', string="Société",
        default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id')

    @api.depends('checkin_date', 'checkout_date')
    def _compute_num_nights(self):
        for rec in self:
            if rec.checkin_date and rec.checkout_date:
                delta = rec.checkout_date - rec.checkin_date
                rec.num_nights = max(delta.days, 0)
            else:
                rec.num_nights = 0

    @api.depends('tariff_night', 'num_nights')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = rec.tariff_night * rec.num_nights

    @api.depends('review_ids', 'review_ids.rating')
    def _compute_has_review(self):
        for rec in self:
            reviews = rec.review_ids
            rec.has_review = bool(reviews)
            if reviews:
                rec.guest_rating = sum(r.rating for r in reviews) / len(reviews)
            else:
                rec.guest_rating = 0.0

    @api.constrains('checkin_date', 'checkout_date')
    def _check_dates(self):
        for rec in self:
            if rec.checkin_date and rec.checkout_date and rec.checkout_date <= rec.checkin_date:
                raise ValidationError(
                    _("La date de départ doit être postérieure à la date d'arrivée."))

    @api.constrains('checkin_date', 'checkout_date', 'property_id')
    def _check_overlap(self):
        for rec in self:
            if not (rec.checkin_date and rec.checkout_date and rec.property_id):
                continue
            domain = [
                ('id', '!=', rec.id),
                ('property_id', '=', rec.property_id.id),
                ('state', 'not in', ['cancelled', 'draft']),
                ('checkin_date', '<', rec.checkout_date),
                ('checkout_date', '>', rec.checkin_date),
            ]
            if self.search_count(domain):
                raise ValidationError(
                    _("Ce bien est déjà réservé sur cette période."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'civora.reservation') or _('Nouveau')
        return super().create(vals_list)

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_checkin(self):
        self.write({'state': 'checkin'})
        for rec in self:
            if rec.property_id:
                rec.property_id.write({'status': 'saisonnier'})

    def action_checkout(self):
        self.write({'state': 'checkout'})
        for rec in self:
            if rec.property_id:
                rec.property_id.write({'status': 'disponible'})
            self.env['civora.cleaning.task'].create({
                'reservation_id': rec.id,
                'property_id': rec.property_id.id,
                'date': rec.checkout_date,
                'state': 'a_planifier',
                'company_id': rec.company_id.id,
            })

    def action_cancel(self):
        self.write({'state': 'cancelled'})
        for rec in self:
            if rec.property_id and rec.state == 'checkin':
                rec.property_id.write({'status': 'disponible'})

    @api.model
    def get_seasonal_kpis(self):
        today = fields.Date.today()
        first_of_month = today.replace(day=1)
        active = self.search_count([
            ('state', 'in', ['confirmed', 'checkin']),
        ])
        checkins_today = self.search_count([
            ('checkin_date', '=', today),
            ('state', '=', 'confirmed'),
        ])
        checkouts_today = self.search_count([
            ('checkout_date', '=', today),
            ('state', '=', 'checkin'),
        ])
        month_reservations = self.search([
            ('state', 'in', ['confirmed', 'checkin', 'checkout']),
            ('checkin_date', '>=', first_of_month),
            ('checkin_date', '<=', today),
        ])
        revenue_month = sum(month_reservations.mapped('total_amount'))
        all_reviews = self.env['civora.reservation.review'].search([])
        avg_rating = 0.0
        review_count = len(all_reviews)
        if review_count:
            avg_rating = round(sum(all_reviews.mapped('rating')) / review_count, 1)
        cleaning_pending = self.env['civora.cleaning.task'].search_count([
            ('state', 'in', ['a_planifier', 'planifie']),
        ])
        return {
            'active': active,
            'checkins_today': checkins_today,
            'checkouts_today': checkouts_today,
            'revenue_month': revenue_month,
            'avg_rating': avg_rating,
            'review_count': review_count,
            'cleaning_pending': cleaning_pending,
        }
