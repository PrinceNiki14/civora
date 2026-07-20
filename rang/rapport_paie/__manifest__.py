##############################################################################
#
# Copyright (c) 2012 KERYATEC - jonathan.arra@keryatec.com
# Author: Jean Jonathan ARRA
#
# Fichier du module hr_cmu
# ##############################################################################
{
    "name": "Rapport de paie",
    "version": "1.0",
    "author": "Parfait ALLA",
    "depends": ["base", 'hr_payroll', 'hr'],
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
