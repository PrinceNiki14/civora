# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CivoraSale(models.Model):
    _name = 'civora.sale'
    _description = 'Dossier de vente immobilière'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string="Référence",
        readonly=True,
        copy=False,
        default='Nouveau',
    )
    property_id = fields.Many2one(
        'civora.property',
        string="Bien",
        required=True,
        tracking=True,
    )
    seller_id = fields.Many2one(
        'res.partner',
        string="Vendeur",
        tracking=True,
    )
    buyer_id = fields.Many2one(
        'res.partner',
        string="Acquéreur",
        tracking=True,
    )
    agent_id = fields.Many2one(
        'res.users',
        string="Agent responsable",
        default=lambda self: self.env.user,
        tracking=True,
    )
    state = fields.Selection([
        ('mandat', 'Mandat signé'),
        ('commercialisation', 'En commercialisation'),
        ('offre', 'Offre reçue'),
        ('compromis', 'Compromis signé'),
        ('acte', 'Acte en cours'),
        ('cloture', 'Clôturée'),
        ('annule', 'Annulée'),
    ], string="État", default='mandat', required=True, tracking=True)

    mandate_type = fields.Selection([
        ('exclusif', 'Exclusif'),
        ('simple', 'Simple'),
        ('delegue', 'Délégué'),
    ], string="Type de mandat", default='simple', tracking=True)
    mandate_date = fields.Date(string="Date du mandat")
    mandate_end_date = fields.Date(string="Fin du mandat")

    asking_price = fields.Integer(string="Prix demandé (FCFA)")
    sale_amount = fields.Integer(string="Prix de vente final (FCFA)", tracking=True)

    commission_rate = fields.Float(string="Taux de commission (%)", default=5.0)
    commission_amount = fields.Integer(
        string="Commission agence (FCFA)",
        compute='_compute_commission',
        store=True,
    )

    notary_name = fields.Char(string="Notaire")
    notary_phone = fields.Char(string="Téléphone notaire")

    compromis_date = fields.Date(string="Date du compromis", tracking=True)
    conditions_text = fields.Text(string="Conditions suspensives")
    acte_date = fields.Date(string="Date de l'acte", tracking=True)
    estimated_acte_date = fields.Date(string="Date acte prévisionnelle")

    offer_ids = fields.One2many('civora.sale.offer', 'sale_id', string="Offres")
    offer_count = fields.Integer(compute='_compute_offer_count')

    notes = fields.Text(string="Notes internes")

    company_id = fields.Many2one(
        'res.company',
        string="Société",
        default=lambda self: self.env.company,
        required=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = self.env['ir.sequence'].next_by_code('civora.sale') or 'Nouveau'
        return super().create(vals_list)

    @api.depends('sale_amount', 'commission_rate')
    def _compute_commission(self):
        for rec in self:
            rec.commission_amount = int(rec.sale_amount * (rec.commission_rate or 0) / 100)

    def _compute_offer_count(self):
        for rec in self:
            rec.offer_count = len(rec.offer_ids)

    def action_commercialisation(self):
        self.ensure_one()
        self.write({'state': 'commercialisation'})

    def action_offre(self):
        self.ensure_one()
        self.write({'state': 'offre'})

    def action_compromis(self):
        self.ensure_one()
        if not self.buyer_id:
            raise ValidationError("Veuillez renseigner l'acquéreur avant de passer au compromis.")
        self.write({'state': 'compromis'})

    def action_acte(self):
        self.ensure_one()
        if not self.compromis_date:
            raise ValidationError("Veuillez renseigner la date du compromis.")
        self.write({'state': 'acte'})

    def action_cloturer(self):
        self.ensure_one()
        if not self.acte_date:
            raise ValidationError("Veuillez renseigner la date de l'acte.")
        if not self.sale_amount:
            raise ValidationError("Veuillez renseigner le prix de vente final.")
        self.write({'state': 'cloture'})
        if self.property_id:
            self.property_id.write({'status': 'vendu'})

    def action_annuler(self):
        self.ensure_one()
        self.write({'state': 'annule'})
        if self.property_id and self.property_id.status == 'vendu':
            self.property_id.write({'status': 'disponible'})

    @api.model
    def get_sales_kpis(self):
        today = fields.Date.today()
        month_start = today.replace(day=1)
        domain_active = [('state', 'not in', ['cloture', 'annule']), ('company_id', 'in', self.env.companies.ids)]
        domain_closed_month = [
            ('state', '=', 'cloture'),
            ('acte_date', '>=', month_start),
            ('company_id', 'in', self.env.companies.ids),
        ]

        active = self.search_count(domain_active)
        mandats = self.search_count([('state', 'in', ['mandat', 'commercialisation'])] + domain_active[:1] + [('company_id', 'in', self.env.companies.ids)])
        closed = self.search(domain_closed_month)
        volume = sum(closed.mapped('sale_amount'))
        commission_total = sum(closed.mapped('commission_amount'))
        pending_offers = self.env['civora.sale.offer'].search_count([
            ('state', '=', 'pending'),
            ('company_id', 'in', self.env.companies.ids),
        ])

        return {
            'active': active,
            'mandats': mandats,
            'volume_month': volume,
            'commission_month': commission_total,
            'closed_month': len(closed),
            'pending_offers': pending_offers,
        }
