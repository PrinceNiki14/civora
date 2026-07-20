##############################################################################
#
# Copyright (c) 2012 Veone - jonathan.arra@gmail.com
# Author: Jean Jonathan ARRA
#
# Fichier du module hr_synthese
# ##############################################################################
{
    "name" : "Gestion des Congés",
    "version" : "1.0",
    "sequence":1,
    "author" : "Parfait ALLA",
    'category': 'Human Resources/Employees',
    "depends" : ["hr", "hr_holidays", "hr_contract_extension", "hr_payroll_ci", "hr_holidays_extension"],
    "description": """ Gestion des aspects liés aux congés
    """,
    "data": [
        "security/ir.model.access.csv",
        "views/hr_employee.xml",
        "views/hr_leave.xml",
    ],
    "installable": True
}
