# -*- coding: utf-8 -*-
from odoo import api, fields, models

CIVORA_PHASE_STATUS = [
    ('planifiee', "Planifiee"),
    ('en_cours', "En cours"),
    ('terminee', "Terminee"),
    ('en_retard', "En retard"),
]

CIVORA_CALL_STATUS = [
    ('emis', "Emis"),
    ('encaisse', "Encaisse"),
    ('retard', "En retard"),
    ('annule', "Annule"),
]


class CivoraProgramPhase(models.Model):
    """Phase du planning de chantier (terrassement, gros oeuvre, finitions...)."""
    _name = 'civora.program.phase'
    _description = "Phase de chantier CIVORA"
    _order = 'sequence, id'

    program_id = fields.Many2one(
        'civora.program', string="Programme", required=True,
        ondelete='cascade', index=True,
    )
    name = fields.Char(string="Libelle", required=True)
    sequence = fields.Integer(string="Ordre", default=1)
    date_start = fields.Date(string="Date debut")
    date_end_planned = fields.Date(string="Date prevue fin")
    date_end_real = fields.Date(string="Date reelle achevement")
    progress = fields.Integer(string="Avancement (%)", default=0)
    status = fields.Selection(
        CIVORA_PHASE_STATUS, string="Statut", default='planifiee', required=True,
    )
    is_milestone = fields.Boolean(
        string="Jalon-cle", default=False,
        help="Cette phase est un jalon contractuel : elle peut declencher un appel de fonds.",
    )
    notes = fields.Text(string="Notes")
    company_id = fields.Many2one(
        'res.company', string="Societe", related='program_id.company_id', store=True,
    )

    milestone_ids = fields.One2many(
        'civora.program.milestone', 'phase_id', string="Echeances liees",
    )

    @api.onchange('progress')
    def _onchange_progress(self):
        for rec in self:
            if rec.progress >= 100 and rec.status != 'terminee':
                rec.status = 'terminee'
            elif 0 < rec.progress < 100 and rec.status == 'planifiee':
                rec.status = 'en_cours'


class CivoraProgramMilestone(models.Model):
    """Echeance de la grille VEFA : % cumule du prix appele a un jalon donne."""
    _name = 'civora.program.milestone'
    _description = "Echeance VEFA CIVORA"
    _order = 'sequence, cumulative_pct, id'

    program_id = fields.Many2one(
        'civora.program', string="Programme", required=True,
        ondelete='cascade', index=True,
    )
    name = fields.Char(string="Libelle", required=True)
    sequence = fields.Integer(string="Ordre", default=1)
    cumulative_pct = fields.Float(
        string="% cumule appele", required=True, default=0.0,
        help="Pourcentage cumule du prix du lot appele a ce jalon.",
    )
    phase_id = fields.Many2one(
        'civora.program.phase', string="Lie au jalon chantier",
        ondelete='set null',
        help="Phase de chantier qui declenche cette echeance.",
    )
    notes = fields.Text(string="Notes")
    issued = fields.Boolean(string="Emis", default=False, readonly=True)
    call_ids = fields.One2many('civora.program.call', 'milestone_id', string="Appels emis")
    company_id = fields.Many2one(
        'res.company', string="Societe", related='program_id.company_id', store=True,
    )

    step_pct = fields.Float(string="% de l'echeance", compute='_compute_step_pct')

    @api.depends('cumulative_pct', 'sequence', 'program_id.milestone_ids.cumulative_pct')
    def _compute_step_pct(self):
        for rec in self:
            siblings = rec.program_id.milestone_ids.sorted(
                key=lambda m: (m.sequence, m.cumulative_pct)
            )
            previous = 0.0
            for milestone in siblings:
                if milestone.id == rec.id:
                    break
                previous = milestone.cumulative_pct
            rec.step_pct = max(0.0, rec.cumulative_pct - previous)

    def action_issue_calls(self):
        """Genere un appel de fonds par lot vendu pour cette echeance."""
        self.ensure_one()
        Call = self.env['civora.program.call']
        lots = self.program_id.lot_ids.filtered(lambda l: l.status == 'vendu')
        created = Call.browse()
        for lot in lots:
            exists = Call.search_count([
                ('milestone_id', '=', self.id), ('lot_id', '=', lot.id),
            ])
            if exists:
                continue
            created |= Call.create({
                'program_id': self.program_id.id,
                'milestone_id': self.id,
                'lot_id': lot.id,
                'partner_id': lot.buyer_id.id or False,
                'amount': lot.price * (self.step_pct / 100.0),
                'date_issue': fields.Date.context_today(self),
                'status': 'emis',
            })
        if created:
            self.issued = True
        return len(created)


class CivoraProgramCall(models.Model):
    """Appel de fonds emis a un acquereur pour un jalon donne."""
    _name = 'civora.program.call'
    _description = "Appel de fonds CIVORA"
    _order = 'date_issue desc, id desc'

    program_id = fields.Many2one(
        'civora.program', string="Programme", required=True,
        ondelete='cascade', index=True,
    )
    milestone_id = fields.Many2one(
        'civora.program.milestone', string="Echeance", ondelete='cascade', index=True,
    )
    lot_id = fields.Many2one(
        'civora.program.lot', string="Lot", ondelete='cascade', index=True,
    )
    partner_id = fields.Many2one('res.partner', string="Acquereur")
    currency_id = fields.Many2one(
        'res.currency', string="Devise", related='program_id.currency_id', store=True,
    )
    amount = fields.Monetary(string="Montant appele", currency_field='currency_id')
    amount_paid = fields.Monetary(string="Montant encaisse", currency_field='currency_id')
    date_issue = fields.Date(string="Date d'emission", default=fields.Date.context_today)
    date_due = fields.Date(string="Echeance")
    status = fields.Selection(
        CIVORA_CALL_STATUS, string="Statut", default='emis', required=True, index=True,
    )
    notes = fields.Text(string="Notes")
    company_id = fields.Many2one(
        'res.company', string="Societe", related='program_id.company_id', store=True,
    )

    def action_mark_paid(self):
        for rec in self:
            rec.write({'status': 'encaisse', 'amount_paid': rec.amount})
        return True
