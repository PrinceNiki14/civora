# -*- coding: utf-8 -*-
from odoo import api, fields, models


CIVORA_SIGNER_ROLE = [
    ('bailleur',     "Bailleur"),
    ('locataire',    "Locataire"),
    ('proprietaire', "Propriétaire"),
    ('agence',       "Agence"),
    ('mandant',      "Mandant"),
    ('mandataire',   "Mandataire"),
    ('caution',      "Caution"),
    ('temoin',      "Témoin"),
    ('autre',        "Autre"),
]

CIVORA_SIGNER_STATE = [
    ('pending', "En attente"),
    ('signed',  "Signé"),
    ('refused', "Refusé"),
    ('expired', "Expiré"),
]


class CivoraDocumentSigner(models.Model):
    """Signataire d'un document CIVORA.

    Simple tracking pour l'instant — la signature électronique intégrée
    (DocuSign, Yousign, etc.) viendra dans un incrément dédié.
    """
    _name = 'civora.document.signer'
    _description = "Signataire de document CIVORA"
    _order = 'sequence, id'

    document_id = fields.Many2one(
        'civora.document', string="Document",
        required=True, ondelete='cascade', index=True,
    )
    company_id = fields.Many2one(
        'res.company', string="Société",
        related='document_id.company_id', store=True, readonly=True,
    )
    sequence = fields.Integer(string="Ordre", default=10)
    partner_id = fields.Many2one(
        'res.partner', string="Contact",
        help="Si le signataire correspond à un contact CIVORA existant.",
    )
    name = fields.Char(string="Nom", required=True)
    email = fields.Char(string="Email")
    role = fields.Selection(
        CIVORA_SIGNER_ROLE, string="Rôle",
        default='autre', required=True,
    )
    state = fields.Selection(
        CIVORA_SIGNER_STATE, string="Statut",
        default='pending', required=True, tracking=True,
    )
    date_invited = fields.Datetime(
        string="Invité le", default=fields.Datetime.now, readonly=True,
    )
    date_signed = fields.Datetime(string="Signé le", readonly=True)
    note = fields.Char(string="Note")

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        for signer in self:
            if signer.partner_id:
                if not signer.name:
                    signer.name = signer.partner_id.name
                if not signer.email:
                    signer.email = signer.partner_id.email or ""

    def action_mark_signed(self):
        for s in self:
            s.write({
                'state': 'signed',
                'date_signed': fields.Datetime.now(),
            })
            # Audit
            self.env['civora.document.audit'].sudo().create({
                'document_id': s.document_id.id,
                'action': 'sign_done',
                'user_id': self.env.user.id,
                'detail': "Signature apposée : %s (%s)" % (s.name, dict(CIVORA_SIGNER_ROLE).get(s.role, s.role)),
            })
        return True

    def action_mark_refused(self):
        for s in self:
            s.write({'state': 'refused'})
            self.env['civora.document.audit'].sudo().create({
                'document_id': s.document_id.id,
                'action': 'sign_refused',
                'user_id': self.env.user.id,
                'detail': "Signature refusée : %s" % s.name,
            })
        return True
