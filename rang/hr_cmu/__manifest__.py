##############################################################################
#
# Copyright (c) 2012 KERYATEC - jonathan.arra@keryatec.com
# Author: Jean Jonathan ARRA
#
# Fichier du module hr_cmu
# ##############################################################################
{
    "name": "Couverture maladie universelle Côte d'Ivoire",
    "version": "1.0",
    "author": "Jean Jonathan ARRA(KERYATEC)",
    'category': 'Localization',
    "website": "http://www.keryatec.com",
    #"depends": ["base", 'hr_update', 'hr_payroll_ci'],
    "depends": ["base", 'hr_payroll', 'hr'],
    "description": """
    """,
    "init_xml": [],
    "demo_xml": [],
    "data": [
        "security/ir.model.access.csv",
        "views/hr_employee_view.xml",
        "wizards/hr_cmu_view.xml",
        "reports/report_templates.xml",
        "reports/report_hr_cmu.xml",
        "reports/raport_view.xml",
    ],
    "installable": True
}
