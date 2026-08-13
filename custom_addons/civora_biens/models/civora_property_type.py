# -*- coding: utf-8 -*-
import re
import unicodedata
from odoo import api, fields, models


def _slugify_prefix(text, length=3):
    """Genere un prefixe technique (lettres majuscules) depuis un libelle.

    Ex: "Villa" -> "VIL", "Appartement" -> "APP", "Local commercial" -> "LOC".
    Ne renvoie que des caracteres ASCII alphabetiques.
    """
    base = unicodedata.normalize('NFKD', text or '').encode('ascii', 'ignore').decode()
    base = re.sub(r'[^a-zA-Z]', '', base).upper()
    return (base[:length] or 'REF').ljust(length, 'X')[:length] if base else 'REF'


class CivoraPropertyType(models.Model):
    """Type de bien (villa, appartement, bureau, studio...).

    Parametrable : chaque agence gere sa propre liste de types.
    """
    _name = 'civora.property.type'
    _description = "Type de bien CIVORA"
    _order = 'sequence, name'

    name = fields.Char(string="Nom", required=True, translate=True)
    code = fields.Char(string="Code", required=True, help="Identifiant technique (ex: villa, appartement).")
    reference_prefix = fields.Char(
        string="Préfixe référence",
        size=5,
        required=True,
        help="Prefixe utilise pour generer les references automatiques des biens de ce type. "
             "Ex: VIL pour Villa. 3 a 5 lettres majuscules. La numerotation est independante "
             "pour chaque societe.",
    )
    color = fields.Char(string="Couleur", help="Couleur d'affichage (hex).")
    sequence = fields.Integer(string="Sequence", default=10)
    active = fields.Boolean(string="Actif", default=True)
    company_id = fields.Many2one(
        'res.company',
        string="Societe",
        index=True,
        default=lambda self: self.env.company,
        help="Societe proprietaire (prive par defaut). Les types de base (seeds) "
             "restent globaux (company_id vide) et visibles par toutes les societes.",
    )

    _code_uniq = models.Constraint(
        'unique (code, company_id)',
        "Le code du type de bien doit etre unique par societe.",
    )

    # ------------------------------------------------------------------
    # CRUD : normalisation du prefixe
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Auto-genere le prefixe si absent, sinon normalise (majuscules, ASCII).
            prefix = vals.get('reference_prefix')
            if not prefix:
                vals['reference_prefix'] = _slugify_prefix(vals.get('name') or vals.get('code') or '', 3)
            else:
                vals['reference_prefix'] = _slugify_prefix(prefix, 5) if len(prefix) > 5 else \
                    re.sub(r'[^A-Z]', '', prefix.upper()) or _slugify_prefix(vals.get('name') or '', 3)
        return super().create(vals_list)

    def write(self, vals):
        if 'reference_prefix' in vals and vals['reference_prefix']:
            v = vals['reference_prefix']
            vals['reference_prefix'] = _slugify_prefix(v, 5) if len(v) > 5 else \
                (re.sub(r'[^A-Z]', '', v.upper()) or v)
        return super().write(vals)
