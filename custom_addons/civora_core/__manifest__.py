# -*- coding: utf-8 -*-
{
    'name': "CIVORA Core",
    'summary': "Design system CIVORA (composants OWL) + Command Center full-custom",
    'description': """
CIVORA Core
===========
Socle du produit CIVORA 360 :
- tokens du design system (couleurs, ombres, typo)
- composants OWL reutilisables (StatCard, Insight, boutons, cartes)
- ecran d'accueil "Command Center" en client action (aucune vue Odoo)

Devient l'ecran d'accueil (remplace l'action "menu").
    """,
    'author': "NK SERVICE",
    'website': "https://service-odoo.com",
    'category': 'Real Estate',
    'version': '19.0.1.0.0',
    'license': 'LGPL-3',
    # web_enterprise fournit l'action "menu" (home) que l'on remplace
    'depends': ['web', 'web_enterprise'],
    'assets': {
        'web.assets_backend': [
            'civora_core/static/src/scss/civora_tokens.scss',
            'civora_core/static/src/scss/civora_scroll_fix.scss',
            'civora_core/static/src/components/civora_ui.scss',
            'civora_core/static/src/components/civora_kit.scss',
            'civora_core/static/src/components/civora_drawer.scss',
            'civora_core/static/src/components/civora_kit.js',
            'civora_core/static/src/components/civora_kit.xml',
            'civora_core/static/src/components/civora_drawer.js',
            'civora_core/static/src/components/civora_drawer.xml',
            'civora_core/static/src/components/civora_chart.js',
            'civora_core/static/src/components/civora_chart.xml',
            'civora_core/static/src/topbar/civora_topbar.scss',
            'civora_core/static/src/topbar/civora_navbar_patch.js',
            'civora_core/static/src/topbar/civora_user_menu.js',
            'civora_core/static/src/topbar/civora_topbar.js',
            'civora_core/static/src/topbar/civora_topbar.xml',
            'civora_core/static/src/components/civora_stat_card.js',
            'civora_core/static/src/components/civora_stat_card.xml',
            'civora_core/static/src/components/civora_insight.js',
            'civora_core/static/src/command_center/command_center.scss',
            'civora_core/static/src/command_center/command_center.js',
            'civora_core/static/src/command_center/command_center.xml',
            'civora_core/static/src/action_fix.js',
        ],
    },
    'installable': True,
    'application': False,
}
