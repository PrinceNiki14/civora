# Module new_fonction - Odoo 17

## Structure du module

```
new_fonction/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── models.py
├── controllers/
│   ├── __init__.py
│   └── controllers.py
├── views/
│   ├── views.xml
│   └── templates.xml
├── demo/
│   └── demo.xml
└── security/
    └── ir.model.access.csv
```

## Modifications pour Odoo 17

1. **__manifest__.py** :
   - Version mise à jour vers 17.0.1.0.0
   - Licence LGPL-3 ajoutée
   - Dépendances standard Odoo 17
   - Suppression des modules personnalisés non standards

2. **models.py** :
   - Imports nettoyés et simplifiés
   - Correction du modèle HrPayslip en HrPayrollStructure
   - Méthodes compatibles Odoo 17

3. **Structure des dossiers** :
   - Organisation modulaire standard
   - Séparation claire models/views/controllers

## Installation

1. Copier le dossier dans addons/
2. Mettre à jour la liste des apps
3. Installer le module
