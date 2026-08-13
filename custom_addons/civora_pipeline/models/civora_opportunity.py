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
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'stage_sequence, priority desc, id desc'

    _check_company_auto = True

    name = fields.Char(string="Titre", required=True, index=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string="Contact", index=True, tracking=True)
    property_id = fields.Many2one('civora.property', string="Bien", index=True, tracking=True)
    transaction = fields.Selection(CIVORA_TRANSACTION, string="Transaction", tracking=True)
    stage_id = fields.Many2one(
        'civora.pipeline.stage',
        string="Étape",
        index=True,
        default=lambda self: self._default_stage(),
        group_expand='_read_group_stage_ids',
        tracking=True,
    )
    stage_sequence = fields.Integer(related='stage_id.sequence', store=True)
    expected_amount = fields.Monetary(string="Montant estimé", currency_field='currency_id', tracking=True)
    currency_id = fields.Many2one(
        'res.currency', string="Devise", required=True,
        default=lambda self: self.env.company.currency_id,
    )
    probability = fields.Float(string="Probabilité (%)", tracking=True)
    priority = fields.Integer(string="Priorité", default=0)
    score = fields.Integer(string="Score IA", tracking=True)
    agent_id = fields.Many2one('res.users', string="Agent", tracking=True)
    lead_id = fields.Many2one('civora.lead', string="Piste d'origine", index=True)
    description = fields.Text(string="Description")
    date_close = fields.Date(string="Clôture prévue", tracking=True)
    is_won = fields.Boolean(related='stage_id.is_won', store=True)
    is_lost = fields.Boolean(related='stage_id.is_lost', store=True)
    active = fields.Boolean(string="Actif", default=True)
    # Dates de suivi analytique (cf. daysOld cote front + reporting).
    date_stage_updated = fields.Datetime(
        string="Dernier changement d'etape",
        help="Horodatage du dernier passage a une nouvelle etape.",
    )
    date_won = fields.Datetime(
        string="Date de gain",
        help="Horodatage du passage dans une etape marquee « Gagnée ».",
    )
    date_lost = fields.Datetime(
        string="Date de perte",
        help="Horodatage du passage dans une etape marquee « Perdue ».",
    )
    company_id = fields.Many2one(
        'res.company', string="Societe", required=True, index=True,
        default=lambda self: self.env.company,
    )

    @api.model
    def _default_stage(self):
        company_id = self.env.context.get('default_company_id') or self.env.company.id
        stage = self.env['civora.pipeline.stage'].search(
            [('company_id', '=', company_id)],
            order='sequence, id', limit=1,
        )
        return stage.id or False

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        company_ids = self.env.companies.ids or [self.env.company.id]
        return self.env['civora.pipeline.stage'].search(
            [('company_id', 'in', company_ids)],
            order='sequence, id',
        )

    _amount_positive = models.Constraint(
        'check (expected_amount >= 0)',
        "Le montant estime ne peut pas etre negatif.",
    )

    # ------------------------------------------------------------------
    # CRUD : gestion des dates de suivi
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        now = fields.Datetime.now()
        for vals in vals_list:
            vals.setdefault('date_stage_updated', now)
        opps = super().create(vals_list)
        # Initialise date_won / date_lost si l'opportunite naît deja dans une
        # etape finale (peu probable mais coherent).
        for opp in opps:
            if opp.stage_id.is_won and not opp.date_won:
                opp.date_won = opp.date_stage_updated
            if opp.stage_id.is_lost and not opp.date_lost:
                opp.date_lost = opp.date_stage_updated
        return opps

    def write(self, vals):
        # Recuperer l'ancien stage_id pour chaque record avant super().
        old_stages = {opp.id: opp.stage_id for opp in self} if 'stage_id' in vals else {}
        res = super().write(vals)
        if 'stage_id' in vals:
            now = fields.Datetime.now()
            for opp in self:
                old = old_stages.get(opp.id)
                new = opp.stage_id
                if old and new and old.id == new.id:
                    continue
                # Horodater le changement.
                opp.date_stage_updated = now
                # Gain / perte : on horodate a l'entree, on efface a la sortie.
                if new.is_won:
                    if not opp.date_won:
                        opp.date_won = now
                else:
                    if opp.date_won:
                        opp.date_won = False
                if new.is_lost:
                    if not opp.date_lost:
                        opp.date_lost = now
                else:
                    if opp.date_lost:
                        opp.date_lost = False
        return res
