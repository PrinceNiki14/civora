# -*- coding: utf-8 -*-
from odoo import api, fields, models

CIVORA_TRANSACTION = [
    ('vente', "Vente"),
    ('location', "Location"),
    ('saisonnier', "Saisonnier"),
]


class CivoraOpportunity(models.Model):
    """Opportunite commerciale (deal du pipeline)."""
    _name = 'civora.opportunity'
    _description = "Opportunite CIVORA"
    _order = 'stage_sequence, priority desc, id desc'

    name = fields.Char(string="Titre", required=True, index=True)
    partner_id = fields.Many2one('res.partner', string="Contact", index=True)
    property_id = fields.Many2one('civora.property', string="Bien", index=True)
    transaction = fields.Selection(CIVORA_TRANSACTION, string="Transaction")
    stage_id = fields.Many2one(
        'civora.pipeline.stage',
        string="Étape",
        index=True,
        default=lambda self: self._default_stage(),
        group_expand='_read_group_stage_ids',
    )
    stage_sequence = fields.Integer(related='stage_id.sequence', store=True)
    expected_amount = fields.Monetary(string="Montant estimé", currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency', string="Devise", required=True,
        default=lambda self: self.env.company.currency_id,
    )
    probability = fields.Float(string="Probabilité (%)")
    priority = fields.Integer(string="Priorité", default=0)
    score = fields.Integer(string="Score IA")
    agent_id = fields.Many2one('res.users', string="Agent")
    lead_id = fields.Many2one('civora.lead', string="Piste d'origine", index=True)
    description = fields.Text(string="Description")
    date_close = fields.Date(string="Clôture prévue")
    is_won = fields.Boolean(related='stage_id.is_won', store=True)
    is_lost = fields.Boolean(related='stage_id.is_lost', store=True)
    active = fields.Boolean(string="Actif", default=True)
    company_id = fields.Many2one(
        'res.company', string="Societe", required=True, index=True,
        default=lambda self: self.env.company,
    )

    @api.model
    def _default_stage(self):
        stage = self.env['civora.pipeline.stage'].search([], order='sequence, id', limit=1)
        return stage.id or False

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        return self.env['civora.pipeline.stage'].search([], order='sequence, id')

    _amount_positive = models.Constraint(
        'check (expected_amount >= 0)',
        "Le montant estime ne peut pas etre negatif.",
    )
