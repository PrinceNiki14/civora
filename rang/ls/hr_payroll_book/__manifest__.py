# -*- coding: utf-8 -*-
{
    "name": "Hr Payroll Book",
    "version": "17.0.1.0.0",
    "author": "KERYATEC",
    'category': 'Human Resources/Payroll',
    "website": "www.keryatec.com",
    "depends": ["hr_payroll", "report_xlsx", "web"],
    "description": """ 
    Livre de paie.
    """,
    "data": [
        "security/ir.model.access.csv",
        "wizards/hr_Payroll_book_view.xml",
        "views/report_payroll_wizard.xml",
        "views/hr_salary_rule_view.xml",
        "views/hr_payslip_view.xml",
        "reports/raport_view.xml",
        "wizards/hr_cmu_view.xml",
    ],
    "installable": True,
    'license': 'LGPL-3',
    'assets': {
        'web.report_assets_pdf': [
            'hr_payroll_book/static/src/css/report_form.css',
            'hr_payroll_book/static/src/css/report.css'
        ],
    },
}
