# -*- coding: utf-8 -*-
from odoo import fields, models

CIVORA_EVENT_TYPE = [
    ('visite', "Visite"),
    ('rdv', "Rendez-vous"),
    ('relance', "Relance"),
    ('signature', "Signature"),
    ('call', "Appel"),
    ('edl', "État des lieux"),
    ('checkin', "Check-in"),
    ('checkout', "Check-out"),
    ('maintenance', "Maintenance"),
    ('autre', "Autre"),
]
CIVORA_EVENT_STATUS = [
    ('planifie', "Planifié"),
    ('a_confirmer', "À confirmer"),
    ('confirme', "Confirmé"),
    ('realise', "Réalisé"),
    ('annule', "Annulé"),
]
CIVORA_EVENT_MODE = [
    ('physique', "Sur place"),
    ('visio', "Visio"),
    ('tel', "Téléphone"),
]


class CivoraEvent(models.Model):
    """Evenement d'agenda transversal (visite, RDV, signature, relance...)."""
    _name = 'civora.event'
    _description = "Événement CIVORA"
    _order = 'start, id'

    name = fields.Char(string="Titre", required=True, index=True)
    event_type = fields.Selection(CIVORA_EVENT_TYPE, string="Type", required=True, default='rdv', index=True)
    start = fields.Datetime(string="Début", required=True, index=True)
    stop = fields.Datetime(string="Fin")
    allday = fields.Boolean(string="Journée entière", default=False)
    status = fields.Selection(CIVORA_EVENT_STATUS, string="Statut", default='planifie', index=True)
    mode = fields.Selection(CIVORA_EVENT_MODE, string="Modalité")
    location = fields.Char(string="Lieu")
    notes = fields.Text(string="Notes")

    # --- Liens transversaux ---
    agent_id = fields.Many2one('res.users', string="Agent", default=lambda self: self.env.user)
    partner_id = fields.Many2one('res.partner', string="Contact", index=True)
    property_id = fields.Many2one('civora.property', string="Bien", index=True)
    opportunity_id = fields.Many2one('civora.opportunity', string="Opportunité", index=True)
    lead_id = fields.Many2one('civora.lead', string="Piste", index=True)
    visit_request_id = fields.Many2one('civora.visit.request', string="Demande de visite")

    company_id = fields.Many2one(
        'res.company', string="Societe", required=True, index=True,
        default=lambda self: self.env.company,
    )
