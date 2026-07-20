##############################################################################
#
#
# Fichier du module hr_synthese
# ##############################################################################
{
    "name" : "Mise à jour HR de Odoo",
    "sequence":1,
    "version" : "1.0",
    "author" : "Jean Jonathan ARRA",
    'category': 'Localization',
    "depends" : ["base", 'hr', 'hr_contract', 'hr_payroll', 'hr_cmu'],
    "description": """
    """,
    "data":[
            "security/ir.model.access.csv",
            #"views/res_config_settings_views.xml",
            "data/abatements_data.xml",
            "data/categories_employee_data.xml",
            "views/hr_category_employee_view.xml",
            "views/hr_category_salaire_view.xml",
            "views/res_company_view.xml",
            "views/res_partner_view.xml",
            "views/hr_employee_view.xml",
            "views/hr_employee_new_view.xml",
            "views/hrDepartmentView.xml",
            "views/hr_payroll_update.xml",
            #"views/hr_payroll_template_form_view.xml",
            "first_last_name/hr_view.xml",
            "first_last_name/base_config_view.xml"
        ],
    "web.assets_backend": [
            "/hr_update/static/src/legacy/scss/layout_style.scss",
        ],
    "installable": True
}
