# -*- coding: utf-8 -*-
{
    'name': "CIVORA - Ventes Immobilières",
    'summary': "Gestion du cycle complet de vente : mandats, offres, compromis, acte et commissions",
    'description': """
CIVORA — Module Ventes Immobilières
====================================
Gestion complète du processus de vente immobilière :
- Dossiers de vente avec pipeline (Mandat → Commercialisation → Offre → Compromis → Acte → Clôturée)
- Gestion des offres d'achat multiples par bien
- Suivi compromis de vente et conditions suspensives
- Signature acte authentique et clôture
- Calcul automatique des commissions agence / agent
- KPIs : volume de ventes, mandats actifs, délai moyen, taux de conversion
    """,
    'author': "NK SERVICE",
    'website': "https://service-odoo.com",
    'category': 'Real Estate',
    'version': '19.0.1.0.0',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'mail', 'civora_core', 'civora_contacts', 'civora_biens', 'civora_agence'],
    'data': [
        'security/ir.model.access.csv',
        'security/civora_ventes_rules.xml',
        'data/civora_sale_sequence.xml',
        'views/civora_ventes_menu.xml',
        'data/civora_ventes_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'civora_ventes/static/src/sales/sales_screen.scss',
            'civora_ventes/static/src/sales/sale_drawer.scss',
            'civora_ventes/static/src/sale_detail/sale_360.scss',
            'civora_ventes/static/src/property_tab/property_ventes_tab.scss',
            'civora_ventes/static/src/sales/sales_screen.js',
            'civora_ventes/static/src/sales/sales_screen.xml',
            'civora_ventes/static/src/sales/sale_drawer.js',
            'civora_ventes/static/src/sales/sale_drawer.xml',
            'civora_ventes/static/src/sale_detail/sale_360.js',
            'civora_ventes/static/src/sale_detail/sale_360.xml',
            'civora_ventes/static/src/property_tab/property_ventes_tab.js',
            'civora_ventes/static/src/property_tab/property_ventes_tab.xml',
        ],
    },
    'installable': True,
    'application': False,
}
