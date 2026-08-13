# -*- coding: utf-8 -*-
{
    'name': "CIVORA Biens",
    'summary': "Biens CIVORA : referentiel du parc immobilier",
    'description': """
CIVORA Biens
============
- Modele : civora.property (bien immobilier) + civora.property.type (parametrable).
- Statut d'occupation (Disponible / Loue / Saisonnier), pricing, rentabilite,
  proprietaire (contact CIVORA), photo, multi-societe.
- Objet pivot du bloc Immobilier : reference par Locations, Saisonnier, Ventes,
  Proprietaires et Pipeline (modules ulterieurs).

Depend de civora_contacts (le proprietaire est un contact CIVORA).
    """,
    'author': "NK SERVICE",
    'website': "https://service-odoo.com",
    'category': 'Real Estate',
    'version': '19.0.19.2.0',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'mail', 'civora_core', 'civora_contacts', 'civora_agence'],
    'data': [
        'security/ir.model.access.csv',
        'security/civora_biens_rules.xml',
        'data/civora_property_type_data.xml',
        'data/civora_sale_doc_type_data.xml',
        'views/civora_biens_menu.xml',
        'views/public_property_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'civora_biens/static/lib/leaflet/leaflet.css',
            'civora_biens/static/lib/leaflet/leaflet.js',
            'civora_biens/static/src/properties/properties_screen.scss',
            'civora_biens/static/src/properties/property_drawer.scss',
            'civora_biens/static/src/properties/property_360.scss',
            'civora_biens/static/src/contact_tab/contact_biens_tab.scss',
            'civora_biens/static/src/components/civora_map.scss',
            'civora_biens/static/src/components/civora_map.js',
            'civora_biens/static/src/components/civora_map.xml',
            'civora_biens/static/src/properties/property_drawer.js',
            'civora_biens/static/src/properties/property_drawer.xml',
            'civora_biens/static/src/properties/unit_dialog.js',
            'civora_biens/static/src/properties/unit_dialog.xml',
            'civora_biens/static/src/properties/duplicate_units_dialog.js',
            'civora_biens/static/src/properties/duplicate_units_dialog.xml',
            'civora_biens/static/src/properties/property_360.js',
            'civora_biens/static/src/properties/property_360.xml',
            'civora_biens/static/src/properties/properties_screen.js',
            'civora_biens/static/src/properties/properties_screen.xml',
            'civora_biens/static/src/contact_tab/contact_biens_tab.js',
            'civora_biens/static/src/contact_tab/contact_biens_tab.xml',
        ],
    },
    'installable': True,
    'application': False,
}
