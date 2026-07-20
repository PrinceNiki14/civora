# -*- coding: utf-8 -*-
{
    'name': "CIVORA Calendrier",
    'summary': "Agenda transversal (visites, RDV, signatures, relances)",
    'description': "Calendrier CIVORA relie aux contacts, biens, opportunites et pistes.",
    'author': "NK SERVICE",
    'website': "https://service-odoo.com",
    'category': 'Real Estate',
    'version': '19.0.3.0.0',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'civora_core', 'civora_contacts', 'civora_biens', 'civora_pipeline', 'civora_agence'],
    'data': [
        'security/ir.model.access.csv',
        'security/civora_calendar_rules.xml',
        'views/civora_calendar_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'civora_calendar/static/src/calendar/calendar_screen.scss',
            'civora_calendar/static/src/tabs/agenda_tab.scss',
            'civora_calendar/static/src/calendar/event_drawer.js',
            'civora_calendar/static/src/calendar/event_drawer.xml',
            'civora_calendar/static/src/calendar/calendar_screen.js',
            'civora_calendar/static/src/calendar/calendar_screen.xml',
            'civora_calendar/static/src/tabs/agenda_tab.js',
            'civora_calendar/static/src/tabs/agenda_tab.xml',
        ],
    },
    'installable': True,
    'application': False,
}
