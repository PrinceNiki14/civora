##############################################################################
#
# Copyright (c) 2012 KERYATEC - jonathan.arra@keryatec.com
# Author: Jean Jonathan ARRA
#
# Fichier du module hr_cmu
# ##############################################################################
{
    "name": "CGRAE",
    "version": "1.0",
    "author": "Parfait ALLA",
    'category': 'Localization',
    "website": "yoboue.alla@gmail.com",
    "depends": ["base", 'hr_payroll', 'hr'],
    "description": """
    """,
    "data": [
        "security/ir.model.access.csv",
        "views/views.xml",
        "wizards/hr_cgrae.xml",
        "reports/report_templates.xml",
        "reports/report_hr_cgrae.xml",
        "reports/report_view.xml",
    ],
    "installable": True
}
