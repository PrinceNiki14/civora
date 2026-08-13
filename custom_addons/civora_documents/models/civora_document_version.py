# -*- coding: utf-8 -*-
from odoo import fields, models


class CivoraDocumentVersion(models.Model):
    """Historique des versions d'un document CIVORA.

    À chaque `upload_new_version` sur un document, une entrée est créée ici
    avec l'attachment correspondant. La version courante est celle dont le
    numéro correspond à `document_id.version_number`.
    """
    _name = 'civora.document.version'
    _description = "Version de document CIVORA"
    _order = 'version_number desc, id desc'

    document_id = fields.Many2one(
        'civora.document', string="Document",
        required=True, ondelete='cascade', index=True,
    )
    company_id = fields.Many2one(
        'res.company', string="Société",
        related='document_id.company_id', store=True, readonly=True,
    )
    version_number = fields.Integer(string="Numéro de version", required=True)
    attachment_id = fields.Many2one(
        'ir.attachment', string="Pièce jointe (snapshot)",
        ondelete='set null',
        help="Attachment de cette version — permet la restauration.",
    )
    change_note = fields.Char(string="Note de modification")
    author_id = fields.Many2one('res.users', string="Auteur")
    date_created = fields.Datetime(
        string="Date", default=fields.Datetime.now, required=True, readonly=True,
    )
    file_size = fields.Integer(
        related='attachment_id.file_size', store=True, readonly=True,
    )
