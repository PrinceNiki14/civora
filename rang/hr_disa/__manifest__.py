##############################################################################
#
# Copyright (c) 2012 KERYATEC - jonathan.arra@keryatec.com
# Author: Jean Jonathan ARRA
#
# Fichier du module hr_cmu
# ##############################################################################
{
    "name": "DISA",
    "version": "1.0",
    "author": "PARFAIT ALLA",
    'category': 'Localization',
    "depends": ["base", 'hr_payroll', 'hr', 'report_xlsx'],
    "description": """
    """,
    "data": [
        "security/ir.model.access.csv",
        #"views/hr_employee_view.xml",
        "wizards/hr_disa_view.xml",
        "reports/report_view.xml",
    ],
    "installable": True
}
