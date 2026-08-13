# -*- coding: utf-8 -*-
"""Exposition de la configuration SMS dans les Paramètres d'Odoo.

CIVORA masque Odoo pour les écrans métier, mais la configuration d'une
passerelle est une opération d'administration rare et technique : lui
dédier un écran OWL complet serait disproportionné.
"""
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    civora_sms_enabled = fields.Boolean(
        related='company_id.civora_sms_enabled', readonly=False)
    civora_sms_email = fields.Char(
        related='company_id.civora_sms_email', readonly=False)
    civora_sms_password = fields.Char(
        related='company_id.civora_sms_password', readonly=False)
    civora_sms_client_id = fields.Char(
        related='company_id.civora_sms_client_id', readonly=False)
    civora_sms_client_secret = fields.Char(
        related='company_id.civora_sms_client_secret', readonly=False)
    civora_sms_sender_id = fields.Char(
        related='company_id.civora_sms_sender_id', readonly=False)
    civora_sms_deaccent = fields.Boolean(
        related='company_id.civora_sms_deaccent', readonly=False)
