# -*- coding: utf-8 -*-
{
    'name': "new_fonction",

    'summary': "Module d'extensions pour les contrats RH et produits",

    'description': """
        Module d'extensions pour Odoo 17 incluant :
        - Gestion des entrées de travail pour les contrats
        - Notification des lots de paie
        - Validation des codes-barres par société
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    'category': 'Human Resources',
    'version': '17.0.1.0.0',
    'license': 'LGPL-3',

    'depends': [
        'base',
        'hr_contract',
        'hr_payroll',
        'hr_work_entry_contract',
        'product',
    ],

    'data': [
        'views/views.xml',
        'views/templates.xml',
    ],

    'demo': [
        'demo/demo.xml',
    ],

    'installable': True,
    'application': False,
    'auto_install': False,
}
