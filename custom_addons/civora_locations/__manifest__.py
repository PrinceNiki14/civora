# -*- coding: utf-8 -*-
{
    'name': "CIVORA Locations",
    'summary': "Gestion locative : baux, loyers, encaissements",
    'description': """
CIVORA Locations
=================
- Modele civora.lease (bail) : locataire, bien, loyer/charges/depot, periode,
  statut calcule (Actif / Retard / Expire bientot / Resilie).
- Modele civora.lease.payment (encaissement de loyer) : montant, mode, statut,
  origine (saisie manuelle ou paiement en ligne a venir).
- Ecran Baux (KPIs, liste filtrable) + Fiche Bail 360 (apercu, paiements).
- Active l'onglet "Bail" jusque-la en placeholder sur la fiche Locataire
  (civora_gestion) et contribue un onglet "Bail" sur la fiche Bien.

Depend de civora_biens (bien) et civora_contacts (locataire/proprietaire).
    """,
    'author': "NK SERVICE",
    'website': "https://service-odoo.com",
    'category': 'Real Estate',
    'version': '19.0.1.5.4',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'mail', 'civora_core', 'civora_contacts', 'civora_biens', 'civora_agence'],
    'data': [
        'security/ir.model.access.csv',
        'security/civora_locations_rules.xml',
        'data/civora_lease_sequence.xml',
        'reports/lease_receipt_report.xml',
        'views/civora_locations_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'civora_locations/static/src/leases/leases_screen.scss',
            'civora_locations/static/src/leases/lease_drawer.scss',
            'civora_locations/static/src/lease_detail/lease_360.scss',
            'civora_locations/static/src/property_tab/property_lease_tab.scss',
            'civora_locations/static/src/leases/lease_drawer.js',
            'civora_locations/static/src/leases/lease_drawer.xml',
            'civora_locations/static/src/leases/leases_screen.js',
            'civora_locations/static/src/leases/leases_screen.xml',
            'civora_locations/static/src/lease_detail/lease_360.js',
            'civora_locations/static/src/lease_detail/lease_360.xml',
            'civora_locations/static/src/property_tab/property_lease_tab.js',
            'civora_locations/static/src/property_tab/property_lease_tab.xml',
            'civora_locations/static/src/property_patch/property_360_patch.scss',
            'civora_locations/static/src/property_patch/property_360_patch.js',
            'civora_locations/static/src/property_patch/property_360_inherit.xml',
        ],
    },
    'installable': True,
    'application': False,
}
