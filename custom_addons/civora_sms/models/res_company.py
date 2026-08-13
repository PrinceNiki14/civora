# -*- coding: utf-8 -*-
"""Identifiants HSMS portés par la société.

Choix délibéré : ces champs ne sont PAS dans ir.config_parameter.
CIVORA est vendu en white-label et exploité en multi-société — chaque
agence dispose de son propre compte HSMS et surtout de son propre
sender ID. Un locataire de Cocody doit voir le nom de son agence sur son
téléphone, pas celui de l'éditeur.
"""
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    civora_sms_enabled = fields.Boolean(
        string="Activer les SMS", default=False,
        help="Tant que cette case est décochée, aucun SMS ne part : les "
             "messages restent en file et peuvent être relancés.",
    )
    civora_sms_email = fields.Char(string="HSMS · Email du compte")
    civora_sms_password = fields.Char(string="HSMS · Mot de passe")
    civora_sms_client_id = fields.Char(string="HSMS · Client ID")
    civora_sms_client_secret = fields.Char(string="HSMS · Client Secret")
    civora_sms_sender_id = fields.Char(
        string="Nom d'expéditeur", size=11,
        help="Affiché sur le téléphone du destinataire. 11 caractères "
             "maximum, sans espace ni accent — contrainte des opérateurs.",
    )
    civora_sms_deaccent = fields.Boolean(
        string="Retirer les accents", default=True,
        help="Un seul caractère accentué fait basculer le SMS en codage "
             "UCS-2 : la limite passe de 160 à 70 caractères par segment, "
             "et la facture double. Laissez coché sauf raison précise.",
    )

    def civora_sms_service(self):
        """Instancie le service HSMS de cette société."""
        self.ensure_one()
        from ..services.hsms_service import HSMSService
        return HSMSService(self)

    def civora_sms_is_ready(self):
        self.ensure_one()
        return bool(self.civora_sms_enabled) and self.civora_sms_service().is_configured()
