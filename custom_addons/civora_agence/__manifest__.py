# -*- coding: utf-8 -*-
{
    'name': "CIVORA Agence",
    'summary': "Apps coquilles (placeholders) de la suite immobiliere CIVORA 360",
    'description': """
CIVORA Agence - coquilles
=========================
Cree les applications de la suite immobiliere (Biens, Programmes, Locations,
Proprietaires, etc.) sous forme de coquilles vides affichant un ecran
"Bientot disponible". Elles apparaissent dans la sidebar en attendant le
developpement des vrais modules ; il suffira alors de retirer la coquille
correspondante ici.
    """,
    'author': "NK SERVICE",
    'website': "https://service-odoo.com",
    'category': 'Real Estate',
    'version': '19.0.1.0.0',
    'license': 'LGPL-3',
    'depends': ['web'],
    'data': [
        'views/civora_agence_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'civora_agence/static/src/placeholder/civora_placeholder.scss',
            'civora_agence/static/src/placeholder/civora_placeholder.js',
            'civora_agence/static/src/placeholder/civora_placeholder.xml',
        ],
    },
    'installable': True,
    'application': False,
}
