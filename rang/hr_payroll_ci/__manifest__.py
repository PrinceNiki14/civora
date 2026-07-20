##############################################################################
#
# Copyright (c) 2012 Veone - jonathan.arra@gmail.com
# Author: Jean Jonathan ARRA
#
# Fichier du module hr_synthese
# ##############################################################################
{
    "name" : "Payroll Côte d'Ivoire",
    "version" : "1.0",
    "sequence":1,
    "author" : "Jean Jonathan ARRA",
    'category': 'Localization',
    "website" : "http://www.siig.ci",
    "depends" : ["hr_payroll", "hr_contract_extension", "hr_holidays_extension"],
    #"depends" : ["hr_payroll", "hr_contract_extension", "hr_holidays_extension"],
    "description": """ Synthèse de la paie
    - livre de paie mensuelle et périodique
    - Synthèse de paie des employés
    - interfaçage avec la gestion des contrats des employés
    """,
    "data": [
        "security/hr_security.xml",
        "security/ir.model.access.csv",
        "data/categorie_salariale.xml",
        "data/hr_template_data.xml",
        "data/hr_work_entry_type.xml",
        "data/hr_leave_type.xml",
        #"data/service_cron.xml",
        "report/templates/layouts.xml",
        "views/report_payslip.xml",
        "wizards/hr_payroll_inverse_view.xml",
        "views/report_payslip_templates.xml",
        "views/hr_payroll_report.xml",
        "views/hr_menu_view.xml",
        "views/hr_payroll_ci.xml",
        "views/hr_salary_rule_views.xml",
        #"views/hr_employee.xml",
        #"views/hr_holidays.xml",
    ],
    "installable": True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
