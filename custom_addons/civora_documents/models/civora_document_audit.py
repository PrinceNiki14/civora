# -*- coding: utf-8 -*-
from odoo import fields, models


CIVORA_AUDIT_ACTION = [
    ('create',        "Création"),
    ('view',          "Consultation"),
    ('download',      "Téléchargement"),
    ('share',         "Partage"),
    ('new_version',   "Nouvelle version"),
    ('state_change',  "Changement de statut"),
    ('sign_request',  "Invitation à signer"),
    ('sign_done',     "Signature apposée"),
    ('sign_refused',  "Signature refusée"),
    ('other',         "Autre"),
]


class CivoraDocumentAudit(models.Model):
    """Journal d'audit d'un document CIVORA.

    Trace toutes les actions significatives (création, consultation,
    téléchargement, partage, changement de version, signatures...) pour
    répondre aux exigences de conformité et de traçabilité.

    Journal immuable : pas de write ni unlink autorisés en dehors de l'admin.
    """
    _name = 'civora.document.audit'
    _description = "Événement d'audit CIVORA"
    _order = 'date desc, id desc'
    _rec_name = 'detail'

    document_id = fields.Many2one(
        'civora.document', string="Document",
        required=True, ondelete='cascade', index=True,
    )
    company_id = fields.Many2one(
        'res.company', string="Société",
        related='document_id.company_id', store=True, readonly=True,
    )
    action = fields.Selection(
        CIVORA_AUDIT_ACTION, string="Action",
        required=True, index=True,
    )
    user_id = fields.Many2one(
        'res.users', string="Utilisateur",
        default=lambda self: self.env.user, required=True,
    )
    detail = fields.Char(string="Détail")
    date = fields.Datetime(
        string="Date", default=fields.Datetime.now, required=True, readonly=True,
    )
