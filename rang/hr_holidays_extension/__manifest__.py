# -*- coding:utf-8 -*-

{
    "name": "Extension de congés",
    "version": "1.0",
    "author": "Jean Jonathan ARRA",
    'category': 'Localization',
    "depends": ["base","hr_holidays"],
    "description": """
     """,
    "data": [
        "data/cron_view.xml",
        'security/group_rules_view.xml',
        #'views/res_config_settings_view.xml',
        'views/hr_holidays_view.xml',
        #'views/hr_employee_view.xml',
    ],
    "installable": True
}

