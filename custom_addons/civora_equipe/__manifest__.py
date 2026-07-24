{
    "name": "CIVORA - Equipe",
    "version": "19.0.1.0.0",
    "category": "Real Estate",
    "summary": "Gestion de l'equipe et des agents de l'agence immobiliere",
    "author": "CIVORA",
    "depends": ["base", "web", "mail", "civora_core", "civora_agence", "civora_contacts"],
    "data": [
        "security/ir.model.access.csv",
        "security/civora_equipe_rules.xml",
        "views/civora_equipe_menu.xml",
        "data/civora_equipe_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "civora_equipe/static/src/team/team_screen.scss",
            "civora_equipe/static/src/team/member_drawer.scss",
            "civora_equipe/static/src/member_detail/member_360.scss",
            "civora_equipe/static/src/team/team_screen.js",
            "civora_equipe/static/src/team/member_drawer.js",
            "civora_equipe/static/src/member_detail/member_360.js",
            "civora_equipe/static/src/team/team_screen.xml",
            "civora_equipe/static/src/team/member_drawer.xml",
            "civora_equipe/static/src/member_detail/member_360.xml",
        ],
    },
    "application": False,
    "installable": True,
    "license": "LGPL-3",
    "demo": [
        "data/civora_equipe_demo.xml",
    ],
}
