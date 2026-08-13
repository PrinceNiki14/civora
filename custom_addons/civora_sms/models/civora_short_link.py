# -*- coding: utf-8 -*-
"""Raccourcisseur de liens interne.

Motivation directe : un lien de signature de contrat mesure environ
75 caractères. Ajouté au corps du message, il fait dépasser la limite de
160 caractères d'un SMS et déclenche la facturation d'un second segment.
Un code court ramène le lien à une trentaine de caractères.

Sécurité : le code court donne accès à la même ressource que l'URL
d'origine, il a donc la même valeur qu'un mot de passe. On tire 10
caractères dans un alphabet sans ambiguïté visuelle (ni O/0, ni I/l/1),
soit environ 5.10^15 combinaisons — hors de portée d'une énumération.
"""
import secrets

from odoo import api, fields, models

# Alphabet sans caractères confondables : un locataire peut avoir à
# recopier le lien à la main depuis son téléphone.
ALPHABET = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 10


class CivoraShortLink(models.Model):
    _name = 'civora.short.link'
    _description = "Lien court CIVORA"
    _order = 'create_date desc, id desc'
    _rec_name = 'code'

    code = fields.Char(string="Code", required=True, index=True, copy=False)
    target_url = fields.Char(string="URL cible", required=True)
    company_id = fields.Many2one(
        'res.company', string="Société", required=True, index=True,
        default=lambda self: self.env.company,
    )
    # Rattachement générique : permet de retrouver tous les liens d'un contrat.
    res_model = fields.Char(string="Modèle lié", index=True)
    res_id = fields.Integer(string="Enregistrement lié", index=True)

    hit_count = fields.Integer(string="Ouvertures", default=0, readonly=True)
    last_hit = fields.Datetime(string="Dernière ouverture", readonly=True)
    expiry = fields.Datetime(
        string="Expire le",
        help="Passée cette date, le lien court cesse de rediriger. "
             "Vide = pas d'expiration.",
    )
    active = fields.Boolean(default=True)

    _code_uniq = models.Constraint(
        'unique (code)', "Ce code court est déjà utilisé.")

    # ══════════════════════════════════════════════════════════════════
    @api.model
    def _generate_code(self):
        for _attempt in range(12):
            code = ''.join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))
            if not self.sudo().search_count([('code', '=', code)]):
                return code
        raise ValueError("Impossible de générer un code court unique.")

    @api.model
    def civora_shorten(self, url, res_model=None, res_id=None,
                       company=None, reuse=True):
        """Retourne l'URL courte correspondant à `url`.

        `reuse` évite de multiplier les codes quand un même lien est
        renvoyé plusieurs fois (relance d'un locataire, par exemple).
        """
        if not url:
            return url
        company = company or self.env.company
        Link = self.sudo()

        if reuse:
            existing = Link.search([
                ('target_url', '=', url),
                ('company_id', '=', company.id),
                ('active', '=', True),
            ], limit=1)
            if existing:
                return existing.civora_public_url()

        link = Link.create({
            'code': self._generate_code(),
            'target_url': url,
            'company_id': company.id,
            'res_model': res_model or False,
            'res_id': int(res_id) if res_id else False,
        })
        return link.civora_public_url()

    def civora_public_url(self):
        self.ensure_one()
        base = self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url', default='')
        return "%s/s/%s" % (base.rstrip('/'), self.code)

    def civora_register_hit(self):
        """Comptabilise une ouverture. Jamais bloquant pour la redirection."""
        self.ensure_one()
        try:
            self.sudo().write({
                'hit_count': self.hit_count + 1,
                'last_hit': fields.Datetime.now(),
            })
        except Exception:  # noqa: BLE001
            pass

    def civora_is_valid(self):
        self.ensure_one()
        if not self.active:
            return False
        if self.expiry and self.expiry < fields.Datetime.now():
            return False
        return True
