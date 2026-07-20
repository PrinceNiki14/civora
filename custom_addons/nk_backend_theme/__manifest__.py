# -*- coding: utf-8 -*-
{
    'name': "NK Backend Theme",
    'summary': "Ecran d'accueil personnalise (Command Center) + habillage backend NK SERVICE",
    'description': """
NK SERVICE - Habillage du backend Odoo
=======================================
Brique A : remplace la grille d'applications par un tableau de bord d'accueil
personnalise ("Command Center") affichant des KPI reels tires d'Odoo,
tout en conservant l'acces aux applications.
    """,
    'author': "NK SERVICE",
    'website': "https://service-odoo.com",
    'category': 'Theme/Backend',
    'version': '19.0.1.2.0',
    'license': 'LGPL-3',
    # web_enterprise fournit l'action "menu" (home menu) que l'on surcharge
    'depends': ['web', 'web_enterprise'],
    'data': [
        'views/nk_layout.xml',
        'views/nk_login_templates.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            ('prepend', 'nk_backend_theme/static/src/scss/nk_variables.scss'),
        ],
        'web.assets_backend': [
            'nk_backend_theme/static/src/scss/nk_navbar.scss',
            'nk_backend_theme/static/src/scss/nk_list.scss',
            'nk_backend_theme/static/src/branding/nk_branding.js',
            'nk_backend_theme/static/src/sidebar/nk_sidebar.scss',
            'nk_backend_theme/static/src/sidebar/nk_sidebar_config.js',
            'nk_backend_theme/static/src/sidebar/nk_company_switcher.js',
            'nk_backend_theme/static/src/sidebar/nk_company_switcher.xml',
            'nk_backend_theme/static/src/sidebar/nk_sidebar.js',
            'nk_backend_theme/static/src/sidebar/nk_sidebar.xml',
        ],
        'web.assets_frontend': [
            'nk_backend_theme/static/src/branding/nk_login.scss',
        ],
    },
    'installable': True,
    'application': False,
}
