##############################################################################
# Fichier du module hr_emprunt
# ##############################################################################
{
    "name" : "Gestion des Emprunts",
    "version" : "1.0",
    'sequence': 1,
    "author" : "BDO DIGITAL (PARFAIT ALLA)",
    "category" : "Generic Modules/Human Resources",
    "depends" : ['hr', 'hr_contract_extension', 'hr_work_entry_contract_enterprise'],
    "description": """ Module permettant de gérer les emprunts des employés 
(Echeanciers, Remboursement, interfaçage avec le module de paie)
    """,
    "data": [
            "security/ir.model.access.csv",
            "views/hr_emprunt_view.xml",
    ],
    "installable": True
}
