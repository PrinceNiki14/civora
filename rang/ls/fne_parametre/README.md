# FNE Paramètres - Module Odoo 17

## Migration V16 → V17

### Changements effectués:

1. **Manifest (__manifest__.py)**
   - Version mise à jour: 17.0.1.0.0
   - Licence LGPL-3 conservée
   - Images correctement déclarées
   - Dépendances vérifiées (base, account)

2. **Modèle (res_config_settings.py)**
   - Ajout du champ _description obligatoire en Odoo 17
   - Correction de l'encodage UTF-8 (caractères corrompus)
   - self.env.company utilisé (compatible Odoo 17)
   - Fonctions get_values() et set_values() maintenues

3. **Vues XML (account_move_views.xml)**
   - Structure compatible Odoo 17
   - Encodage UTF-8 corrigé
   - Xpath et héritage de vues maintenus

4. **Données (fne_config_data.xml)**
   - Configuration par défaut conservée
   - Séquence FNE maintenue

5. **Fichiers supprimés:**
   - ir.model.access.csv (non nécessaire)
   - payroll_layout.css (vide/inutile)

### Installation:

1. Copier le dossier `fne_parametre_v17` dans `/addons/`
2. Redémarrer Odoo
3. Mettre à jour la liste des applications
4. Installer/Mettre à jour le module "FNE - Paramètres"

### Configuration:

Comptabilité → Configuration → Paramètres → Section "FNE - Facture Normalisée Électronique"

### Support:

support.fne@dgi.gouv.ci
