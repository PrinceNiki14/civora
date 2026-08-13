# -*- coding: utf-8 -*-
"""Restitution du dépôt de garantie en fin de bail.

Enregistre la restitution de la caution au locataire à la sortie, avec :
- le montant total de caution reçu (calculé depuis les paiements type 'caution')
- les éventuelles retenues détaillées (dégradations, arriérés, ménage...)
- le montant net à restituer
- un workflow draft → validated → refunded
- une signature bailleur pour la preuve légale
"""
from odoo import api, fields, models
from odoo.exceptions import UserError


REFUND_STATE = [
    ('draft', "Brouillon"),
    ('validated', "Validée"),
    ('refunded', "Restituée"),
    ('cancelled', "Annulée"),
]

REFUND_REASON = [
    ('end_of_contract',  "Fin normale de contrat"),
    ('mutual_agreement', "Résiliation à l'amiable"),
    ('terminated_early', "Résiliation anticipée"),
]


class CivoraDepositRefund(models.Model):
    _name = 'civora.deposit.refund'
    _description = "Restitution du dépôt de garantie"
    _order = 'date desc, id desc'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string="Référence", required=True, copy=False, readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code(
            'civora.deposit.refund'
        ) or "RC/DRAFT",
    )
    lease_id = fields.Many2one(
        'civora.lease', string="Bail", required=True, ondelete='restrict', index=True,
    )
    tenant_id = fields.Many2one(
        related='lease_id.tenant_id', store=True, string="Locataire",
    )
    property_id = fields.Many2one(
        related='lease_id.property_id', store=True, string="Bien",
    )
    company_id = fields.Many2one(
        related='lease_id.company_id', store=True, string="Société", index=True,
    )
    currency_id = fields.Many2one(
        related='lease_id.currency_id', store=True, string="Devise",
    )

    date = fields.Date(
        string="Date de restitution", required=True,
        default=fields.Date.context_today,
    )
    reason = fields.Selection(
        REFUND_REASON, string="Motif", required=True, default='end_of_contract',
    )
    state = fields.Selection(
        REFUND_STATE, string="État", default='draft', required=True, tracking=True,
    )

    # Montants
    caution_received = fields.Monetary(
        string="Caution reçue au total",
        currency_field='currency_id',
        compute='_compute_caution_received', store=True,
        help="Somme des paiements de type 'caution' enregistrés sur ce bail.",
    )
    line_ids = fields.One2many(
        'civora.deposit.refund.line', 'refund_id', string="Retenues",
    )
    deductions_total = fields.Monetary(
        string="Total des retenues",
        currency_field='currency_id',
        compute='_compute_totals', store=True,
    )
    net_amount = fields.Monetary(
        string="Montant net à restituer",
        currency_field='currency_id',
        compute='_compute_totals', store=True,
    )

    # Signature bailleur
    sign_lessor = fields.Binary(
        string="Signature bailleur (PNG base64)",
        attachment=False, copy=False,
    )
    signed_at_lessor = fields.Datetime(
        string="Date signature bailleur", readonly=True, copy=False,
    )
    signed_by_lessor = fields.Char(
        string="Signataire bailleur", readonly=True, copy=False,
    )

    note = fields.Text(string="Note interne")

    # ── Computed ────────────────────────────────────────────────────────
    @api.depends('lease_id.payment_ids.amount',
                 'lease_id.payment_ids.payment_type',
                 'lease_id.payment_ids.status')
    def _compute_caution_received(self):
        for r in self:
            if not r.lease_id:
                r.caution_received = 0.0
                continue
            r.caution_received = sum(
                p.amount for p in r.lease_id.payment_ids
                if p.payment_type == 'caution'
                and p.status in ('paid', 'partial')
            )

    @api.depends('caution_received', 'line_ids.amount')
    def _compute_totals(self):
        for r in self:
            total_ded = sum(l.amount or 0.0 for l in r.line_ids)
            r.deductions_total = total_ded
            r.net_amount = max(0.0, (r.caution_received or 0.0) - total_ded)

    # ── Actions ─────────────────────────────────────────────────────────
    def action_validate(self):
        self.ensure_one()
        if self.state != 'draft':
            raise UserError("Seule une restitution en brouillon peut être validée.")
        if self.caution_received <= 0:
            raise UserError(
                "Aucune caution n'a été enregistrée pour ce bail. "
                "Impossible de valider la restitution."
            )
        self.write({'state': 'validated'})
        self.message_post(
            body="Restitution de caution validée. Montant net : %s %s." % (
                self.net_amount, self.currency_id.name or "",
            ),
            subtype_xmlid='mail.mt_note',
        )
        return True

    def action_mark_refunded(self):
        self.ensure_one()
        if self.state != 'validated':
            raise UserError(
                "La restitution doit être validée avant d'être marquée comme restituée."
            )
        self.write({'state': 'refunded'})
        self.message_post(
            body="Caution restituée au locataire.",
            subtype_xmlid='mail.mt_note',
        )
        return True

    def action_cancel(self):
        self.ensure_one()
        if self.state == 'refunded':
            raise UserError(
                "Une restitution déjà effectuée ne peut pas être annulée."
            )
        self.write({'state': 'cancelled'})
        return True

    def action_reset_to_draft(self):
        self.ensure_one()
        if self.state not in ('cancelled', 'validated'):
            raise UserError("Impossible de remettre en brouillon depuis cet état.")
        self.write({'state': 'draft'})
        return True

    def action_lessor_signed(self, sign_data_b64):
        """Enregistre la signature du bailleur sur la décharge de restitution."""
        self.ensure_one()
        if self.state not in ('draft', 'validated'):
            raise UserError("La signature n'est possible qu'en brouillon ou validé.")
        self.write({
            'sign_lessor': sign_data_b64,
            'signed_at_lessor': fields.Datetime.now(),
            'signed_by_lessor': self.env.user.name,
        })
        return True

    def get_signatures(self):
        """Retourne les signatures décodées (comme sur les contrats)."""
        self.ensure_one()
        return {
            'sign_lessor': self.sign_lessor.decode() if self.sign_lessor else False,
        }

    # ── Données pour l'UI ──────────────────────────────────────────────
    @api.model
    def get_for_lease(self, lease_id):
        """Retourne le refund associé au bail (le plus récent) + un flag."""
        refund = self.search(
            [('lease_id', '=', lease_id)],
            order='id desc', limit=1,
        )
        if not refund:
            return {'exists': False, 'refund': None}
        return {
            'exists': True,
            'refund': refund._to_dict(),
        }

    def _to_dict(self):
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.name,
            'date': str(self.date) if self.date else False,
            'reason': self.reason,
            'state': self.state,
            'caution_received': self.caution_received,
            'deductions_total': self.deductions_total,
            'net_amount': self.net_amount,
            'signed_at_lessor': str(self.signed_at_lessor) if self.signed_at_lessor else False,
            'signed_by_lessor': self.signed_by_lessor or "",
            'note': self.note or "",
            'lines': [
                {
                    'id': l.id,
                    'label': l.label,
                    'category': l.category,
                    'amount': l.amount,
                    'note': l.note or "",
                }
                for l in self.line_ids
            ],
        }

    @api.model
    def create_for_lease(self, lease_id, vals):
        """Crée un refund + ses lignes en un appel RPC."""
        lease = self.env['civora.lease'].browse(lease_id)
        if not lease.exists():
            raise UserError("Bail introuvable.")
        lines = vals.pop('lines', [])
        vals['lease_id'] = lease_id
        refund = self.create(vals)
        for line in lines:
            self.env['civora.deposit.refund.line'].create({
                'refund_id': refund.id,
                'label': line.get('label') or "Retenue",
                'category': line.get('category') or 'other',
                'amount': line.get('amount') or 0.0,
                'note': line.get('note') or False,
            })
        return refund._to_dict()

    def update_lines(self, lines):
        """Remplace les lignes de retenue (utilisé en édition)."""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError("Les retenues ne peuvent être modifiées qu'en brouillon.")
        self.line_ids.unlink()
        for line in lines:
            self.env['civora.deposit.refund.line'].create({
                'refund_id': self.id,
                'label': line.get('label') or "Retenue",
                'category': line.get('category') or 'other',
                'amount': line.get('amount') or 0.0,
                'note': line.get('note') or False,
            })
        return self._to_dict()


class CivoraDepositRefundLine(models.Model):
    _name = 'civora.deposit.refund.line'
    _description = "Retenue sur restitution de caution"
    _order = 'sequence, id'

    refund_id = fields.Many2one(
        'civora.deposit.refund', string="Restitution",
        required=True, ondelete='cascade', index=True,
    )
    sequence = fields.Integer(default=10)
    label = fields.Char(string="Motif de retenue", required=True)
    category = fields.Selection(
        [
            ('damages',   "Dégradations"),
            ('cleaning',  "Ménage / remise en état"),
            ('arrears',   "Arriérés de loyer"),
            ('utilities', "Charges impayées"),
            ('other',     "Autre"),
        ],
        string="Catégorie", default='damages', required=True,
    )
    amount = fields.Monetary(
        string="Montant", currency_field='currency_id', required=True,
    )
    currency_id = fields.Many2one(
        related='refund_id.currency_id', store=True,
    )
    note = fields.Char(string="Note")
