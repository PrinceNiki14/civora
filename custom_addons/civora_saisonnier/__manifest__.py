# -*- coding: utf-8 -*-
{
    'name': "CIVORA - Saisonnier",
    'summary': "Gestion des locations saisonnières : réservations, check-in/out, ménages, tarifs et avis",
    'description': """
CIVORA — Module Saisonnier
==========================
Gestion complète des locations courte durée :
- Réservations avec pipeline (Brouillon → Confirmée → Check-in → Check-out)
- Calendrier de disponibilité
- Tarification saisonnière par bien
- Gestion des ménages post-départ
- Avis et notation des voyageurs
- KPIs : RevPAR, ADR, taux d'occupation, note moyenne
    """,
    'author': "NK SERVICE",
    'website': "https://service-odoo.com",
    'category': 'Real Estate',
    'version': '19.0.1.0.0',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'mail', 'civora_core', 'civora_contacts', 'civora_biens', 'civora_agence'],
    'data': [
        'security/ir.model.access.csv',
        'security/civora_saisonnier_rules.xml',
        'data/civora_reservation_sequence.xml',
        'views/civora_saisonnier_menu.xml',
        'data/civora_saisonnier_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'civora_saisonnier/static/src/reservations/reservations_screen.scss',
            'civora_saisonnier/static/src/reservations/reservation_drawer.scss',
            'civora_saisonnier/static/src/reservation_detail/reservation_360.scss',
            'civora_saisonnier/static/src/property_tab/property_saisonnier_tab.scss',
            'civora_saisonnier/static/src/reservations/reservations_screen.js',
            'civora_saisonnier/static/src/reservations/reservations_screen.xml',
            'civora_saisonnier/static/src/reservations/reservation_drawer.js',
            'civora_saisonnier/static/src/reservations/reservation_drawer.xml',
            'civora_saisonnier/static/src/reservation_detail/reservation_360.js',
            'civora_saisonnier/static/src/reservation_detail/reservation_360.xml',
            'civora_saisonnier/static/src/property_tab/property_saisonnier_tab.js',
            'civora_saisonnier/static/src/property_tab/property_saisonnier_tab.xml',
        ],
    },
    'installable': True,
    'application': False,
}
