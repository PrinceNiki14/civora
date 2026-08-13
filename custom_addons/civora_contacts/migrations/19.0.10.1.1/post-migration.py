# -*- coding: utf-8 -*-
"""Migration one-shot v10.1.0.

- Crée un snapshot 'initial' dans civora.contact.role.history pour chaque
  contact CIVORA existant, avec la date de création du contact — donne un
  point de départ propre à la timeline d'historique des rôles.
- Recalcule le score IA pour tous les contacts CIVORA non verrouillés,
  pour peupler la ventilation dès l'installation.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})

    History = env['civora.contact.role.history']
    Partner = env['res.partner']

    # 1) Snapshot 'initial' pour tous les contacts CIVORA ayant des rôles
    contacts = Partner.search([('civora_is_contact', '=', True)])
    created = 0
    for p in contacts:
        # Skip si déjà un historique
        if History.search_count([('partner_id', '=', p.id)], limit=1):
            continue
        for role in p.civora_role_ids:
            History.create({
                'partner_id': p.id,
                'role_id': role.id,
                'action': 'initial',
                'date': p.create_date or env.cr.now(),
                'user_id': SUPERUSER_ID,
                'note': "État initial (migration v10.1.0)",
            })
            created += 1
    _logger.info("[CIVORA v10.1.0] %d entrées d'historique de rôles créées.", created)

    # 2) Recalcul initial des scores IA
    try:
        contacts.civora_compute_ai_score()
        _logger.info("[CIVORA v10.1.0] Scores IA recalculés pour %d contacts.", len(contacts))
    except Exception as e:
        _logger.warning("[CIVORA v10.1.0] Erreur recalcul scores : %s", e)
