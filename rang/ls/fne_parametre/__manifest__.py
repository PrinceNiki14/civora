{
    'name': 'FNE - Paramètres',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Configuration FNE Côte d\'Ivoire',
    'description': '''
        Module de configuration pour la certification FNE
        (Facture Normalisée Électronique) de la DGI Côte d'Ivoire.
    ''',
    'author': 'Votre Société',
    'website': 'https://www.votresociete.com',
    'depends': ['base', 'account'],
    'external_dependencies': {
        'python': ['requests'],
    },
    'data': [
        'data/fne_config_data.xml',
        'views/account_move_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
