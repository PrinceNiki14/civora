# -*- coding: utf-8 -*-
from odoo import api, fields, models

CIVORA_GUARANTEE_TYPE = [
    ('gfa', "GFA - Garantie financiere d'achevement"),
    ('do', "DO - Dommages-ouvrage"),
    ('rc', "RC - Responsabilite civile pro"),
    ('biennale', "Biennale (2 ans)"),
    ('decennale', "Decennale (10 ans)"),
    ('trc', "TRC - Tous risques chantier"),
    ('autre', "Autre"),
]

CIVORA_DOCUMENT_TYPE = [
    ('permis', "Permis de construire"),
    ('plan', "Plan"),
    ('brochure', "Brochure"),
    ('notice', "Notice descriptive"),
    ('garantie', "Garantie / assurance"),
    ('contrat', "Contrat"),
    ('autre', "Autre"),
]


class CivoraProgramGuarantee(models.Model):
    """Couverture contractuelle du programme (GFA, DO, RC, decennale...)."""
    _name = 'civora.program.guarantee'
    _description = "Garantie de programme CIVORA"
    _order = 'date_end, id'

    program_id = fields.Many2one(
        'civora.program', string="Programme", required=True,
        ondelete='cascade', index=True,
    )
    guarantee_type = fields.Selection(
        CIVORA_GUARANTEE_TYPE, string="Type", required=True, default='gfa',
    )
    issuer = fields.Char(string="Emetteur (banque / assureur)", required=True)
    policy_number = fields.Char(string="N de police")
    currency_id = fields.Many2one(
        'res.currency', string="Devise", related='program_id.currency_id', store=True,
    )
    amount = fields.Monetary(string="Montant garanti", currency_field='currency_id')
    date_start = fields.Date(string="Date d'effet")
    date_end = fields.Date(string="Date d'expiration")
    notes = fields.Text(string="Notes")
    company_id = fields.Many2one(
        'res.company', string="Societe", related='program_id.company_id', store=True,
    )

    days_to_expiry = fields.Integer(
        string="Jours avant echeance", compute='_compute_expiry',
    )
    is_expiring = fields.Boolean(
        string="Arrive a echeance", compute='_compute_expiry', store=True,
        help="Vrai si la couverture expire dans moins de 90 jours.",
    )

    @api.depends('date_end')
    def _compute_expiry(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.date_end:
                delta = (rec.date_end - today).days
                rec.days_to_expiry = delta
                rec.is_expiring = 0 <= delta <= 90
            else:
                rec.days_to_expiry = 0
                rec.is_expiring = False


class CivoraProgramDocument(models.Model):
    """Piece du dossier documentaire du programme."""
    _name = 'civora.program.document'
    _description = "Document de programme CIVORA"
    _order = 'create_date desc, id desc'

    program_id = fields.Many2one(
        'civora.program', string="Programme", required=True,
        ondelete='cascade', index=True,
    )
    name = fields.Char(string="Nom du document", required=True)
    document_type = fields.Selection(
        CIVORA_DOCUMENT_TYPE, string="Type", default='autre', required=True,
    )
    datas = fields.Binary(string="Fichier", attachment=True)
    file_name = fields.Char(string="Nom du fichier")
    url = fields.Char(string="Lien externe")
    notes = fields.Text(string="Notes")
    company_id = fields.Many2one(
        'res.company', string="Societe", related='program_id.company_id', store=True,
    )
