# -*- coding: utf-8 -*-
{
    'name': "CIVORA Contacts",
    'summary': "Contacts CIVORA : modele + ecran annuaire full-custom",
    'description': """
CIVORA Contacts
===============
- Modele : res.partner etendu (roles multiples, source, score IA, statut,
  agent, budget, RGPD...).
- Ecran : annuaire CIVORA full-custom (client action OWL, aucune vue Odoo),
  reutilisant le kit de composants de civora_core.
    """,
    'author': "NK SERVICE",
    'website': "https://service-odoo.com",
    'category': 'Real Estate/CRM',
    'version': '19.0.9.5.0',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'civora_core'],
    'post_init_hook': '_assign_company_to_civora_contacts',
    'data': [
        'security/ir.model.access.csv',
        'security/civora_contacts_rules.xml',
        'data/civora_contact_role_data.xml',
        'data/civora_contact_source_data.xml',
        'data/civora_contact_segment_data.xml',
        'data/civora_agent_role_data.xml',
        'views/civora_contacts_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'civora_contacts/static/src/contacts/contacts_screen.scss',
            'civora_contacts/static/src/contacts/contact_drawer.scss',
            'civora_contacts/static/src/contacts/contact_360.scss',
            'civora_contacts/static/src/contacts/contact_drawer.js',
            'civora_contacts/static/src/contacts/contact_drawer.xml',
            'civora_contacts/static/src/contacts/contact_360.js',
            'civora_contacts/static/src/contacts/contact_360.xml',
            'civora_contacts/static/src/contacts/contacts_screen.js',
            'civora_contacts/static/src/contacts/contacts_screen.xml',
        ],
    },
    'installable': True,
    'application': False,
}
