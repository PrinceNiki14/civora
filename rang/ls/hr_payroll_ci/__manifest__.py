{
    "name": "Payroll Côte d'Ivoire",
    "version": "17.0.1.0.0",
    "sequence": 1,
    "author": "Jean Jonathan ARRA",
    "category": "Human Resources/Payroll",
    "website": "http://www.siig.ci",
    "license": "LGPL-3",
    "depends": ["hr_payroll", "hr_contract", "hr_holidays"],
    "description": """
Synthèse de la paie
====================
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
        "data/service_cron.xml",
        "report/templates/layouts.xml",
        "views/report_payslip.xml",
        "wizards/hr_payroll_inverse_view.xml",
        "views/report_payslip_templates.xml",
        "views/hr_payroll_report.xml",
        "views/hr_menu_view.xml",
        "views/hr_payroll_ci.xml",
        "views/hr_salary_rule_views.xml",
        "views/hr_employee.xml",
        "views/res_company_view.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "hr_payroll_ci/static/src/css/ivoire_payroll.css",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
