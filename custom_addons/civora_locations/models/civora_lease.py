# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError

CIVORA_LEASE_TYPE = [
    ('residentiel', "Résidentiel"),
    ('commercial', "Commercial"),
]
CIVORA_LEASE_STATE = [
    ('draft', "Brouillon"),
    ('active', "Actif"),
    ('ended', "Résilié"),
]
CIVORA_LEASE_STATUS = [
    ('actif', "Actif"),
    ('retard', "Retard"),
    ('expire_bientot', "Expire bientôt"),
    ('resilie', "Résilié"),
]

# Seuil en-dessous duquel un bail est considere "en retard" (taux d'encaissement).
CIVORA_LEASE_ARREARS_THRESHOLD = 95.0
# Fenetre (en jours) avant echeance a partir de laquelle un bail est "a renouveler".
CIVORA_LEASE_RENEWAL_WINDOW_DAYS = 60


class CivoraLease(models.Model):
    """Bail : contrat de location reliant un locataire a un bien CIVORA.

    Remplace a terme le simple champ civora.property.tenant_id par une
    relation contractuelle complete (periode, loyer, depot, encaissements).
    """
    _name = 'civora.lease'
    _description = "Bail CIVORA"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'
    _rec_name = 'name'
    _check_company_auto = True

    name = fields.Char(string="N° de bail", copy=False, index=True, tracking=True,
                       default=lambda self: self._default_name())
    property_id = fields.Many2one(
        'civora.property',
        string="Bien",
        required=True,
        index=True,
        tracking=True,
        check_company=True,
        help="Bien loue par ce contrat.",
    )
    tenant_id = fields.Many2one(
        'res.partner',
        string="Locataire",
        required=True,
        index=True,
        tracking=True,
        domain=[('civora_is_contact', '=', True)],
    )
    owner_id = fields.Many2one(
        'res.partner',
        string="Propriétaire",
        related='property_id.owner_id',
        store=True,
        readonly=True,
    )
    lease_type = fields.Selection(
        CIVORA_LEASE_TYPE, string="Type de bail", default='residentiel', required=True,
    )
    state = fields.Selection(
        CIVORA_LEASE_STATE, string="Cycle de vie", default='active', required=True, tracking=True,
        help="Cycle de vie administratif du bail (independant du statut calcule).",
    )
    status = fields.Selection(
        CIVORA_LEASE_STATUS, string="Statut", compute='_compute_status', store=True,
        help="Statut affiche : deduit du cycle de vie, de l'echeance et du taux d'encaissement.",
    )

    currency_id = fields.Many2one(
        'res.currency', string="Devise", required=True,
        default=lambda self: self.env.company.currency_id,
    )
    rent = fields.Monetary(string="Loyer", currency_field='currency_id', required=True)
    charges = fields.Monetary(string="Charges", currency_field='currency_id')
    deposit = fields.Monetary(string="Dépôt de garantie", currency_field='currency_id')
    total_monthly = fields.Monetary(
        string="Total mensuel", currency_field='currency_id',
        compute='_compute_total_monthly', store=True,
    )

    date_start = fields.Date(string="Date d'entrée", required=True, default=fields.Date.context_today)
    date_end = fields.Date(string="Date de fin")
    payday = fields.Integer(string="Jour de paiement", default=1)
    notice_tenant = fields.Char(string="Préavis locataire", default="3 mois")
    notice_owner = fields.Char(string="Préavis bailleur", default="6 mois")
    indexation = fields.Char(string="Indexation", default="Annuelle · IRL")
    note = fields.Text(string="Notes internes")

    payment_ids = fields.One2many('civora.lease.payment', 'lease_id', string="Paiements")
    payment_count = fields.Integer(string="Nb paiements", compute='_compute_payment_stats', store=True)
    total_paid = fields.Monetary(
        string="Total encaissé", currency_field='currency_id',
        compute='_compute_payment_stats', store=True,
    )
    total_expected = fields.Monetary(
        string="Total attendu", currency_field='currency_id',
        compute='_compute_payment_stats', store=True,
    )
    payment_rate = fields.Float(
        string="Taux d'encaissement (%)", compute='_compute_payment_stats', store=True,
    )
    arrears_amount = fields.Monetary(
        string="Impayés", currency_field='currency_id',
        compute='_compute_payment_stats', store=True,
    )

    company_id = fields.Many2one(
        'res.company', string="Société", required=True, index=True,
        default=lambda self: self.env.company,
        help="Societe rattachee au bien (isolation multi-societe).",
    )

    @api.model
    def _default_name(self):
        seq = self.env['ir.sequence'].next_by_code('civora.lease')
        return seq or "/"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == "/":
                vals['name'] = self._default_name()
        leases = super().create(vals_list)
        # A la creation d'un bail actif, on marque le bien comme loue et on
        # synchronise le locataire courant (compatibilite avec les ecrans
        # existants qui lisent property.tenant_id).
        for lease in leases:
            if lease.state == 'active' and lease.property_id:
                update = {'status': 'loue'}
                if lease.tenant_id:
                    update['tenant_id'] = lease.tenant_id.id
                lease.property_id.write(update)
        return leases

    def write(self, vals):
        res = super().write(vals)
        # Si le bail passe en 'ended', on libere le bien (retour dispo).
        if vals.get('state') == 'ended':
            for lease in self:
                if lease.property_id and lease.property_id.status == 'loue':
                    lease.property_id.write({'status': 'disponible', 'tenant_id': False})
        # Sync locataire courant sur le bien tant que le bail est actif.
        if 'tenant_id' in vals:
            for lease in self:
                if lease.state == 'active' and lease.property_id:
                    lease.property_id.tenant_id = lease.tenant_id.id or False
        return res

    @api.depends('rent', 'charges')
    def _compute_total_monthly(self):
        for lease in self:
            lease.total_monthly = (lease.rent or 0.0) + (lease.charges or 0.0)

    @api.depends('payment_ids.amount', 'payment_ids.status', 'date_start', 'rent', 'charges')
    def _compute_payment_stats(self):
        today = fields.Date.context_today(self)
        for lease in self:
            payments = lease.payment_ids
            lease.payment_count = len(payments)
            lease.total_paid = sum(
                p.amount for p in payments if p.status in ('paid', 'partial')
            )
            months_elapsed = 1
            if lease.date_start and lease.date_start <= today:
                start = lease.date_start
                months_elapsed = max(
                    1, (today.year - start.year) * 12 + (today.month - start.month) + 1
                )
            lease.total_expected = months_elapsed * ((lease.rent or 0.0) + (lease.charges or 0.0))
            lease.payment_rate = (
                min(100.0, round((lease.total_paid / lease.total_expected) * 100, 1))
                if lease.total_expected else 100.0
            )
            lease.arrears_amount = max(0.0, lease.total_expected - lease.total_paid)

    @api.depends('state', 'date_end', 'payment_rate')
    def _compute_status(self):
        today = fields.Date.context_today(self)
        soon = today + timedelta(days=CIVORA_LEASE_RENEWAL_WINDOW_DAYS)
        for lease in self:
            if lease.state == 'ended':
                lease.status = 'resilie'
            elif lease.date_end and lease.date_end <= soon:
                lease.status = 'expire_bientot'
            elif lease.payment_rate < CIVORA_LEASE_ARREARS_THRESHOLD:
                lease.status = 'retard'
            else:
                lease.status = 'actif'

    def action_terminate(self):
        for lease in self:
            lease.state = 'ended'

    def action_reactivate(self):
        for lease in self:
            lease.state = 'active'

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for lease in self:
            if lease.date_end and lease.date_start and lease.date_end < lease.date_start:
                raise ValidationError("La date de fin doit être postérieure à la date d'entrée.")

    @api.constrains('payday')
    def _check_payday(self):
        for lease in self:
            if lease.payday and (lease.payday < 1 or lease.payday > 28):
                raise ValidationError(
                    "Le jour de paiement doit être compris entre 1 et 28 "
                    "(pour éviter les mois de 29 à 31 jours)."
                )

    _rent_positive = models.Constraint(
        'check (rent >= 0)',
        "Le loyer ne peut pas être négatif.",
    )
    _charges_positive = models.Constraint(
        'check (charges >= 0)',
        "Les charges ne peuvent pas être négatives.",
    )
    _deposit_positive = models.Constraint(
        'check (deposit >= 0)',
        "Le dépôt de garantie ne peut pas être négatif.",
    )
