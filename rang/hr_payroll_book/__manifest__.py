# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 KERYATEC - support@keryatec.com
# Author: KERYATEC
#
# Fichier du module hr_payroll_book
# ##############################################################################
{
    "name": "Hr Payroll Book",
    "version": "1.0",
    "author": "KERYATEC",
    'category': 'Human Resources',
    "website": "www.keryatec.com",
    "depends": ["hr_payroll_ci", "report_xlsx", "web"],
    "description": """ 
    Livre de paie.
    """,
    "init_xml": [],
    "demo_xml": [],
    "data": [
        "security/ir.model.access.csv",
        #"views/asset_backend.xml",
        "wizards/hr_Payroll_book_view.xml",
        "views/report_payroll_wizard.xml",
        "views/hr_salary_rule_view.xml",
        "views/hr_payslip_view.xml",
        "reports/raport_view.xml",
    ],
    "installable": True,
    'assets': {
        'web.report_assets_pdf': [
            '/hr_payroll_book/static/src/css/report_form.css',
            '/hr_payroll_book/static/src/css/report.css'
        ],
    },
}
