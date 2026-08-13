# -*- coding: utf-8 -*-
from odoo import fields, models


class CivoraVisitRequest(models.Model):
    """Demande de visite d'un bien, issue de la fiche publique."""
    _name = 'civora.visit.request'
    _description = "Demande de visite CIVORA"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

    property_id = fields.Many2one(
        'civora.property',
        string="Bien",
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True,
    )
    name = fields.Char(string="Nom du visiteur", required=True, tracking=True)
    phone = fields.Char(string="Téléphone", required=True)
    email = fields.Char(string="Email")
    preferred_date = fields.Date(
        string="Date souhaitée",
        help="Date de visite proposee par le prospect depuis la page publique. "
             "Evite un aller-retour telephonique pour caler le rendez-vous.",
    )
    message = fields.Text(string="Message")
    state = fields.Selection([
        ('new', "Nouvelle"),
        ('contacted', "Contacté"),
        ('scheduled', "Visite planifiée"),
        ('done', "Réalisée"),
        ('cancelled', "Annulée"),
    ], string="Statut", default='new', tracking=True)
    assigned_user_id = fields.Many2one(
        'res.users',
        string="Pris en charge par",
        tracking=True,
        help="Agent qui gère cette demande de visite.",
    )
    company_id = fields.Many2one(
        related='property_id.company_id',
        string="Societe",
        store=True,
        index=True,
    )
