# -*- coding: utf-8 -*-
{
    'name': "Personnalisation de bulletin de paye",
    'summary': "Ce module est conçu dans le but de personnaliser le bulletin de paye",
    'description': """
Ce module vient ajouter un nouveau modèle de bulletin qui sera utilisable à volonté
    """,
    'author': "Veone Technologie",
    'website': "https://www.veone.net",
    'category': 'Human Resources/Payroll',
    'version': '17.0.1.0.0',
    'depends': ['hr_payroll', 'hr'],
    'data': [
        'reports/template/layout_report_template_header.xml',
        'reports/template/layout_report_template_footer.xml',
        'reports/report_payslip_custom.xml',
        'reports/payslip_layout.xml',
        'reports/report_view.xml',
        'views/hr_employee_view.xml',
        'views/res_company_view.xml',
    ],
    'demo': [],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
