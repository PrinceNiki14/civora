##############################################################################
#
# Copyright (c) 2012 BDO DIGITAL -
# Author: Parfait ALLA
#
# ##############################################################################
{
    "name": "Cotisation FDFP",
    "version": "1.0",
    "author": "Parfait ALLA",
    'category': 'Localization',
    "website": "yoboue.alla@gmail.com",
    "depends": ["base", 'hr_payroll', 'hr'],
    "description": """
    """,
    "init_xml": [],
    "demo_xml": [],
    "data": [
        "security/ir.model.access.csv",
        "wizards/hr_fdfp_view.xml",
        "reports/report_templates.xml",
        "reports/report_hr_fdfp.xml",
        "reports/raport_view.xml",
    ],
    "installable": True
}
