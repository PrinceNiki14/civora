{
    "name": "Mise à jour HR de Odoo",
    "sequence": 1,
    "version": "17.0.1.0",
    "author": "Jean Jonathan ARRA",
    "category": "Localization",
    "depends": ["base", "hr", "hr_contract", "hr_payroll"],
    "description": """
    """,
    "data": [
        "security/ir.model.access.csv",
        "data/abatements_data.xml",
        "data/categories_employee_data.xml",
        "views/hr_category_employee_view.xml",
        "views/hr_category_salaire_view.xml",
        "views/res_company_view.xml",
        "views/res_partner_view.xml",
        "views/hr_employee_view.xml",
        "views/hrDepartmentView.xml",
        "views/hr_payroll_update.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "hr_update/static/src/scss/layout_style.scss",  # Sans le / au début et sans legacy
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
