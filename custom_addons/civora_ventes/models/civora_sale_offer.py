# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CivoraSaleOffer(models.Model):
    _name = 'civora.sale.offer'
    _description = "Offre d'achat"
    _order = 'date desc'

    sale_id = fields.Many2one(
        'civora.sale',
        string="Dossier de vente",
        required=True,
        ondelete='cascade',
    )
    property_id = fields.Many2one(
        related='sale_id.property_id',
        store=True,
    )
    buyer_id = fields.Many2one(
        'res.partner',
        string="Acquéreur",
        required=True,
    )
    amount = fields.Integer(string="Montant offert (FCFA)", required=True)
    date = fields.Date(string="Date de l'offre", default=fields.Date.today)
    validity_date = fields.Date(string="Validité")
    state = fields.Selection([
        ('pending', 'En attente'),
        ('accepted', 'Acceptée'),
        ('refused', 'Refusée'),
        ('withdrawn', 'Retirée'),
    ], string="État", default='pending', required=True)
    notes = fields.Text(string="Commentaire")
    company_id = fields.Many2one(
        'res.company',
        string="Société",
        default=lambda self: self.env.company,
        required=True,
    )

    def action_accept(self):
        self.ensure_one()
        self.write({'state': 'accepted'})
        other_offers = self.sale_id.offer_ids.filtered(
            lambda o: o.id != self.id and o.state == 'pending'
        )
        other_offers.write({'state': 'refused'})
        self.sale_id.write({
            'buyer_id': self.buyer_id.id,
            'sale_amount': self.amount,
            'state': 'offre',
        })

    def action_refuse(self):
        self.ensure_one()
        self.write({'state': 'refused'})

    def action_withdraw(self):
        self.ensure_one()
        self.write({'state': 'withdrawn'})
