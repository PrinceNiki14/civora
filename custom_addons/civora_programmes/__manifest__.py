# -*- coding: utf-8 -*-
{
    'name': "CIVORA Programmes",
    'summary': "Programmes immobiliers CIVORA : promotion, VEFA et lotissement",
    'description': """
CIVORA Programmes
=================
Bloc Promotion du produit CIVORA 360 :
- civora.program : programme immobilier (Neuf / VEFA / Lotissement)
- civora.program.lot : stock de lots (plan de masse interactif, grille, tableau)
- civora.program.phase : planning de chantier et jalons contractuels
- civora.program.milestone / .call : echeancier VEFA et appels de fonds
- civora.program.guarantee : GFA, dommages-ouvrage, RC, decennale
- civora.program.document : dossier documentaire
- civora.program.stakeholder : acteurs du projet

Ecrans full-custom OWL (aucune vue Odoo) : liste des programmes et fiche 360
a neuf onglets, alignes sur le design system CIVORA.
    """,
    'author': "NK SERVICE",
    'website': "https://service-odoo.com",
    'category': 'Real Estate',
    'version': '19.0.1.0.0',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'mail', 'civora_core', 'civora_contacts', 'civora_agence'],
    'data': [
        'security/ir.model.access.csv',
        'security/civora_programmes_rules.xml',
        'data/civora_program_sequence.xml',
        'data/civora_program_amenity_data.xml',
        'views/civora_programmes_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'civora_programmes/static/src/programs/programs_screen.scss',
            'civora_programmes/static/src/programs/program_360.scss',
            'civora_programmes/static/src/programs/program_dialog.js',
            'civora_programmes/static/src/programs/program_dialog.xml',
            'civora_programmes/static/src/programs/lot_dialog.js',
            'civora_programmes/static/src/programs/lot_dialog.xml',
            'civora_programmes/static/src/programs/lot_drawer.js',
            'civora_programmes/static/src/programs/lot_drawer.xml',
            'civora_programmes/static/src/programs/record_dialogs.js',
            'civora_programmes/static/src/programs/record_dialogs.xml',
            'civora_programmes/static/src/programs/program_360.js',
            'civora_programmes/static/src/programs/program_360.xml',
            'civora_programmes/static/src/programs/programs_screen.js',
            'civora_programmes/static/src/programs/programs_screen.xml',
        ],
    },
    'installable': True,
    'application': False,
}
