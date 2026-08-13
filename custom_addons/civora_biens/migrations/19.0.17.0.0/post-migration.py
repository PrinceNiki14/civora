# -*- coding: utf-8 -*-
"""
Migration civora_biens 19.0.17.0.0 : generation des references sur les biens
existants qui n'en ont pas encore.

S'execute en POST, quand l'ORM est complet et que ir.sequence est disponible.

Regles :
  - Un bien avec un ref non vide reste tel quel.
  - Un bien sans ref et sans type reste sans ref (pas d'ambiguite).
  - Sinon on delegue a _get_or_create_ref_sequence(type, company) qui cree la
    sequence a la demande.
  - Le traitement est deterministe : biens ordonnes par id croissant, donc les
    plus anciens auront les numeros les plus bas.
"""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Property = env['civora.property'].sudo()
    to_fill = Property.with_context(active_test=False).search([
        ('ref', 'in', [False, '']),
        ('property_type_id', '!=', False),
        ('company_id', '!=', False),
    ], order='id asc')
    for prop in to_fill:
        seq = Property._get_or_create_ref_sequence(prop.property_type_id, prop.company_id)
        if seq:
            prop.ref = seq.next_by_id()
