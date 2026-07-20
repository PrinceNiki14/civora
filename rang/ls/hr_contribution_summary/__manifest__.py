# -*- coding: utf-8 -*-
{
    "name": "Contribution summary",
    "version": "17.0.1.0.0",
    "author": "KERYATEC",
    'category': 'Human Resources',
    "website": "www.keryatec.com",
    "depends": ['base', "hr_payroll"],
    "description": """ 
        Gestion des résumé de cotisations tels que:
        - CNPS
        - ITS
        - Contribution National
        - IGR
        - CMU
        
    """,
    "data": [
        "security/rules_group.xml",
        "security/ir.model.access.csv",
        "views/hr_salary_rule_view.xml",
        "views/hr_contribution_summary_view.xml",
        "wizards/hrPayrollCotisationsummary_view.xml",
        "reports/report_menu_view.xml",
        "reports/report_payroll_contribution_summary.xml"
    ],
    "assets": {
        "web.report_assets_common": [
            "hr_contribution_summary/static/src/css/ivoire_payroll.css",
        ],
    },
    "installable": True,
    "license": "LGPL-3",
}
