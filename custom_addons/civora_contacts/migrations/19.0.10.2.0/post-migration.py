# -*- coding: utf-8 -*-
"""Migration one-shot v10.2.0.

Crée une entrée 'initial' dans civora.consent.log pour chaque
consentement non-'none' des contacts CIVORA existants — donne un point
de départ propre au journal RGPD.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})

    Log = env['civora.consent.log']
    Partner = env['res.partner']

    contacts = Partner.search([('civora_is_contact', '=', True)])
    created = 0
    CHANNELS = {
        'civora_consent_email': 'email',
        'civora_consent_sms': 'sms',
        'civora_consent_whatsapp': 'whatsapp',
    }
    for p in contacts:
        # Skip si déjà un log
        if Log.search_count([('partner_id', '=', p.id)], limit=1):
            continue
        for field, channel in CHANNELS.items():
            v = getattr(p, field, None)
            if v and v != 'none':
                Log.create({
                    'partner_id': p.id,
                    'channel': channel,
                    'old_value': 'none',
                    'new_value': v,
                    'date': p.create_date or env.cr.now(),
                    'user_id': SUPERUSER_ID,
                    'source': 'system',
                    'note': "État initial (migration v10.2.0)",
                })
                created += 1
    _logger.info("[CIVORA v10.2.0] %d entrées initiales de consentement créées.", created)
