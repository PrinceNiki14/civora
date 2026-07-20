##############################################################################
#
#
# Fichier du module hr_synthese
# ##############################################################################
{
    "name" : "Mise à jour HR departement",
    "sequence":1,
    "version" : "1.0",
    "author" : "PARFAIT ALLA",
    'category': 'Localization',
    "depends" : ['hr'],
    "description": """
    """,
    "data":[
            "views/hr_employee_view.xml",
            "views/hrDepartmentView.xml",
        ],
    "web.assets_backend": [
            "/hr_update/static/src/legacy/scss/layout_style.scss",
        ],
    "installable": True
}
