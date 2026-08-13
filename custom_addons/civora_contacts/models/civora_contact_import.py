# -*- coding: utf-8 -*-
from odoo import api, fields, models


CIVORA_IMPORT_STATE = [
    ('draft',    "Brouillon"),
    ('preview',  "Aperçu"),
    ('running',  "En cours"),
    ('done',     "Terminé"),
    ('error',    "Erreur"),
]


class CivoraContactImport(models.Model):
    """Traçabilité des imports CSV/Excel de contacts.

    Chaque import crée une entrée ici avec :
    - Le fichier brut d'origine (attachment)
    - Les colonnes détectées + mapping
    - Le résumé (N ajoutés, N doublons, N erreurs)
    - La liste des IDs des contacts créés
    """
    _name = 'civora.contact.import'
    _description = "Import de contacts CIVORA"
    _order = 'create_date desc'

    name = fields.Char(
        string="Nom du fichier", required=True,
    )
    state = fields.Selection(
        CIVORA_IMPORT_STATE, string="État",
        required=True, default='draft', index=True,
    )
    file_data = fields.Binary(string="Fichier CSV/Excel", attachment=True)
    file_name = fields.Char(string="Nom original")
    # Structure du mapping : {"col_fichier": "champ_civora", ...}
    mapping_json = fields.Text(string="Mapping (JSON)")
    # Résumé
    total_rows = fields.Integer(string="Lignes totales", default=0)
    imported_count = fields.Integer(string="Contacts créés", default=0)
    duplicates_count = fields.Integer(string="Doublons évités", default=0)
    errors_count = fields.Integer(string="Erreurs", default=0)
    error_log = fields.Text(string="Journal des erreurs")
    # IDs créés (Text = liste JSON, pour permettre "voir les contacts créés")
    created_partner_ids = fields.Text(string="IDs contacts créés (JSON)")
    # Meta
    user_id = fields.Many2one(
        'res.users', string="Importé par",
        default=lambda self: self.env.user, required=True,
    )
    company_id = fields.Many2one(
        'res.company', string="Société",
        default=lambda self: self.env.company, required=True,
    )
