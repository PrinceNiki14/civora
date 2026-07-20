# FNE - Certification Factures Avoir (Odoo 17)

## Description
Module de certification automatique des factures d'avoir (avoirs/remboursements) auprès de la plateforme FNE (Facture Normalisée Électronique) de la DGI Côte d'Ivoire.

## Fonctionnalités
- ✅ Certification automatique des avoirs
- ✅ Vérification d'éligibilité automatique
- ✅ Correspondance automatique des articles avec IDs FNE
- ✅ Support multi-société
- ✅ Interface de debug pour le dépannage
- ✅ Confirmation avant certification

## Prérequis
- **Odoo:** 17.0
- **Module requis:** `fne_sale_invoice_certification` (doit être installé en premier)
- **Python:** `requests`

## Installation

### 1. Installer le module principal
Assurez-vous que le module `fne_sale_invoice_certification` est déjà installé et configuré.

### 2. Installer ce module
1. Copier le dossier dans le répertoire addons d'Odoo
2. Mettre à jour la liste des applications
3. Installer le module "FNE - Certification Factures Avoir"

## Utilisation

### Workflow de certification d'avoir

1. **Créer un avoir à partir d'une facture certifiée FNE**
   - La facture originale doit être certifiée FNE
   - Créer l'avoir normalement (Facture → Ajouter une note de crédit)

2. **Vérifier l'éligibilité**
   - Badge "📋 Avoir Éligible FNE" apparaît automatiquement
   - Affiche le nombre d'articles correspondants

3. **Certifier l'avoir**
   - Cliquer sur le bouton **"Certifier Avoir FNE"**
   - Confirmer l'action
   - Badge "✅ Avoir Certifié FNE" apparaît

### Conditions d'éligibilité

Un avoir est éligible si :
- ✅ C'est un avoir validé (`out_refund`)
- ✅ Il est lié à une facture certifiée FNE
- ✅ Au moins un article correspond à la facture originale
- ✅ Les articles ont des IDs FNE valides

### Debug

Pour les utilisateurs admin :
- Bouton **"🔍 Debug Avoir"** disponible
- Affiche dans les logs :
  - Statut d'éligibilité
  - Facture originale
  - ID FNE original
  - Nombre d'articles correspondants

## Changements Odoo 17

### Modifications principales :
- ✅ `attrs` remplacé par `invisible`, `required`
- ✅ Ajout `_description` sur le modèle
- ✅ Version format `17.0.x.x.x`
- ✅ Modernisation syntaxe XML
- ✅ Ajout confirmation avant certification

## Architecture

### Structure fichiers
```
fne_refund_certification/
├── models/
│   └── account_move_refund.py
├── views/
│   └── account_move_refund_views.xml
├── security/
│   └── ir.model.access.csv
├── __init__.py
├── __manifest__.py
└── README.md
```

### Champs ajoutés sur `account.move`
- `fne_refund_certified` : Statut certification
- `fne_refund_reference` : Référence FNE avoir
- `fne_refund_token` : Token vérification
- `fne_refund_qr_url` : URL QR code
- `fne_is_refund_eligible` : Éligibilité (computed)
- `fne_original_invoice_id` : Facture originale (computed)
- `fne_original_fne_id` : ID FNE original (computed)
- `fne_refund_items_count` : Nb articles (computed)

### Méthodes principales
- `action_certify_fne_refund()` : Certifier l'avoir
- `_check_fne_refund_prerequisites()` : Vérifications
- `_prepare_fne_refund_data()` : Préparer données API
- `_call_fne_refund_api()` : Appel API FNE
- `_process_fne_refund_response()` : Traiter réponse
- `debug_fne_refund_status()` : Debug statut

## API FNE

### Endpoint utilisé
```
POST {base_url}/external/invoices/{invoice_id}/refund
```

### Format des données
```json
{
  "items": [
    {
      "id": "ID_FNE_ARTICLE_ORIGINAL",
      "quantity": 2
    }
  ]
}
```

## Dépannage

### L'avoir n'est pas éligible
- Vérifier que la facture originale est certifiée FNE
- Vérifier que l'avoir est lié à la facture
- Utiliser le bouton "🔍 Debug Avoir"

### Erreur "Aucun article avec ID FNE"
- Les articles de la facture originale doivent avoir été certifiés
- Vérifier que `fne_item_id` est renseigné sur les lignes originales

### Erreur API
- Vérifier la configuration FNE (clé API)
- Vérifier que l'ID FNE de la facture originale existe
- Consulter les logs Odoo pour plus de détails

## Support
Pour toute question ou problème, contacter le support technique.

## Auteur
Votre Société

## Licence
LGPL-3
