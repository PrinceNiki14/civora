# -*- coding: utf-8 -*-
from odoo import api, fields, models

CIVORA_LEAD_STATUS = [
    ('nouveau', "Nouveau"),
    ('a_qualifier', "À qualifier"),
    ('qualifie', "Qualifié"),
    ('rejete', "Rejeté"),
]
CIVORA_TRANSACTION = [
    ('vente', "Vente"),
    ('location', "Location"),
    ('saisonnier', "Saisonnier"),
]


class CivoraLead(models.Model):
    """Piste (lead) : interet entrant avant qualification."""
    _name = 'civora.lead'
    _description = "Piste CIVORA"
    _order = 'score desc, create_date desc'

    name = fields.Char(string="Titre", required=True, index=True)
    partner_id = fields.Many2one('res.partner', string="Contact")
    contact_name = fields.Char(string="Nom du contact")
    email = fields.Char(string="Email")
    phone = fields.Char(string="Téléphone")
    source_id = fields.Many2one('civora.contact.source', string="Source")
    status = fields.Selection(CIVORA_LEAD_STATUS, string="Statut", required=True, default='nouveau', index=True)
    score = fields.Integer(string="Score IA")
    transaction = fields.Selection(CIVORA_TRANSACTION, string="Recherche")
    budget_min = fields.Monetary(string="Budget min", currency_field='currency_id')
    budget_max = fields.Monetary(string="Budget max", currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency', string="Devise", required=True,
        default=lambda self: self.env.company.currency_id,
    )
    property_id = fields.Many2one('civora.property', string="Bien d'intérêt")
    agent_id = fields.Many2one('res.users', string="Agent")
    description = fields.Text(string="Description")
    opportunity_id = fields.Many2one('civora.opportunity', string="Opportunité créée", readonly=True)
    visit_request_id = fields.Many2one('civora.visit.request', string="Demande de visite d'origine")
    company_id = fields.Many2one(
        'res.company', string="Societe", required=True, index=True,
        default=lambda self: self.env.company,
    )

    def action_reject(self):
        for lead in self:
            lead.status = 'rejete'

    def action_qualify(self):
        """Qualifie la piste et cree l'opportunite associee."""
        Opp = self.env['civora.opportunity']
        for lead in self:
            if lead.opportunity_id:
                lead.status = 'qualifie'
                continue
            opp = Opp.create({
                'name': lead.name,
                'partner_id': lead.partner_id.id or False,
                'property_id': lead.property_id.id or False,
                'transaction': lead.transaction or False,
                'expected_amount': lead.budget_max or lead.budget_min or 0.0,
                'score': lead.score,
                'agent_id': lead.agent_id.id or False,
                'lead_id': lead.id,
                'description': lead.description or False,
                'company_id': lead.company_id.id,
            })
            lead.opportunity_id = opp.id
            lead.status = 'qualifie'
        return True

    @api.model
    def create_from_visit_requests(self):
        """Cree des pistes a partir des demandes de visite non encore converties."""
        VR = self.env['civora.visit.request']
        existing = self.search([('visit_request_id', '!=', False)]).mapped('visit_request_id').ids
        reqs = VR.search([('id', 'not in', existing)])
        count = 0
        for r in reqs:
            prop = r.property_id
            self.create({
                'name': "Visite : %s" % (prop.name or r.name or "bien"),
                'contact_name': r.name or False,
                'phone': r.phone or False,
                'email': r.email or False,
                'property_id': prop.id or False,
                'transaction': prop.transaction or False,
                'agent_id': prop.agent_id.id or False,
                'status': 'nouveau',
                'visit_request_id': r.id,
                'company_id': r.company_id.id or self.env.company.id,
            })
            count += 1
        return count
