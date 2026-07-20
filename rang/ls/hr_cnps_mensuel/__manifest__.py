# -*- coding: utf-8 -*-
{
    "name": "CNPS Mensuel",
    "version": "17.0.1.0",
    "author": "Jean-Jonathan ARRA",
    'category': 'Human Resources',
    "website": "",
    "depends": ['base', 'hr_payroll', 'report_xlsx'],
    "description": """ 
    Gestion de la CNPS mensuelle
    """,
    "data": [
        "security/ir.model.access.csv",
        "data/hr_cnps_settings.xml",
        "views/hrCnpsSettingsView.xml",
        "views/hrCnpsMonthlyView.xml",
        "reports/report_cnps_monthly.xml",
        "reports/report_menu.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
