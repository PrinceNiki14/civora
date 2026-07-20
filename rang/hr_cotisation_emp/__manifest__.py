##############################################################################
#
# Copyright (c) 2012 BDO DIGITAL - yoboue.alla@gmail.com
# Author: Parfait ALLA
# ##############################################################################
{
    "name": "Rapport Cotisation Employé/Employeur",
    "version": "1.0",
    "author": "Parfait ALLA",
    'category': 'Localization',
    "website": "yoboue.alla@gmail.com",
    "depends": ["base", 'hr_payroll', 'hr'],
    "data": [
        "security/ir.model.access.csv",
        "wizards/hr_cotisation_emp.xml",
        "reports/report_templates.xml",
        "reports/report_cotisation_emp.xml",
        "reports/raport_view.xml",
        #"views/hr_salary_rule_view.xml",
    ],
    "installable": True
}
