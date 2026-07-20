##############################################################################
#
# Copyright (c) 2012 BDO DIGITAL -
# Author: Parfait ALLA
#
# ##############################################################################
{
    "name": "Cotisation CNPS",
    "version": "1.0",
    "author": "Parfait ALLA",
    'category': 'Localization',
    "website": "yoboue.alla@gmail.com",
    "depends": ["base", 'hr_payroll', 'hr'],
    "data": [
        "security/ir.model.access.csv",
        "wizards/hr_cnps_view.xml",
        "reports/report_templates.xml",
        "reports/report_hr_cnps.xml",
        "reports/raport_view.xml",
    ],
    "installable": True
}
