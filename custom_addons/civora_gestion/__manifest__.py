# -*- coding: utf-8 -*-
{
    'name': "CIVORA Gestion",
    'summary': "Propriétaires, Locataires, Acquéreurs",
    'description': """
CIVORA Gestion
==============
Ecrans de gestion relationnelle bases sur les contacts et les biens :
- Propriétaires : agregation du parc par proprietaire (biens, valeur, MRR, occupation).
- (a venir) Locataires, Acquereurs.

Aucun nouveau modele : agregation sur civora.property + res.partner.
    """,
    'author': "NK SERVICE",
    'website': "https://service-odoo.com",
    'category': 'Real Estate',
    'version': '19.0.7.0.0',
    'license': 'LGPL-3',
    'depends': ['web', 'civora_core', 'civora_contacts', 'civora_biens', 'civora_agence', 'civora_pipeline', 'civora_locations'],
    'data': [
        'views/civora_gestion_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'civora_gestion/static/src/owners/owners_screen.scss',
            'civora_gestion/static/src/owner_detail/owner_360.scss',
            'civora_gestion/static/src/buyers/buyers_screen.scss',
            'civora_gestion/static/src/owners/owners_screen.js',
            'civora_gestion/static/src/owners/owners_screen.xml',
            'civora_gestion/static/src/owner_detail/owner_360.js',
            'civora_gestion/static/src/owner_detail/owner_360.xml',
            'civora_gestion/static/src/tenants/tenants_screen.js',
            'civora_gestion/static/src/tenants/tenants_screen.xml',
            'civora_gestion/static/src/tenant_detail/tenant_360.js',
            'civora_gestion/static/src/tenant_detail/tenant_360.xml',
            'civora_gestion/static/src/buyers/buyers_screen.js',
            'civora_gestion/static/src/buyers/buyers_screen.xml',
            'civora_gestion/static/src/buyer_detail/buyer_360.js',
            'civora_gestion/static/src/buyer_detail/buyer_360.xml',
        ],
    },
    'installable': True,
    'application': False,
}
