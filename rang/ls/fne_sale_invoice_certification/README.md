# FNE - Certification Factures de Vente (Odoo 17)

## Description
Module de certification automatique des factures de vente auprès de la plateforme FNE (Facture Normalisée Électronique) de la DGI Côte d'Ivoire.

## Fonctionnalités
- ✅ Certification manuelle via bouton
- ✅ Support des templates FNE (B2B, B2C, B2G, B2F)
- ✅ Gestion des taxes personnalisées
- ✅ Génération automatique de QR code
- ✅ Stockage du token de vérification
- ✅ Support multi-société
- ✅ Rapports PDF personnalisés style CIA

## Version
- **Odoo:** 17.0
- **Version module:** 1.0.0
- **Licence:** LGPL-3

## Installation

### Prérequis Python
```bash
pip install requests qrcode[pil]
```

### Installation du module
1. Copier le dossier dans le répertoire addons d'Odoo
2. Mettre à jour la liste des applications
3. Installer le module "FNE - Certification Factures de Vente"

## Configuration

### 1. Paramètres système
Aller dans **Paramètres → Paramètres techniques → Paramètres système**

Ajouter les clés suivantes pour chaque société:

```
fne.base_url = http://54.247.95.108/ws
fne.api_key.{company_id} = VOTRE_CLE_API_FNE
fne.default_point_of_sale.{company_id} = Nom du point de vente
fne.default_establishment.{company_id} = Nom de l'établissement
fne.default_seller_name.{company_id} = Nom du vendeur par défaut
fne.default_commercial_message.{company_id} = Message commercial
fne.default_footer_message.{company_id} = Message pied de page
```

### 2. Configuration des clients B2B
Pour les clients entreprises (template B2B), renseigner le champ **NCC** dans la fiche contact.

## Utilisation

### Certifier une facture
1. Créer et valider une facture de vente
2. Cliquer sur le bouton **"Certifier FNE"**
3. Le système génère automatiquement:
   - Référence FNE
   - Token de vérification
   - QR Code

### Vérification
- Cliquer sur **"Voir QR Code"** pour afficher le QR code
- Scanner le QR code avec un smartphone pour vérifier l'authenticité

## Changements Odoo 17

### Modifications principales:
- ✅ `attrs` remplacé par `invisible`, `required`, `readonly`
- ✅ Suppression de `@api.one`
- ✅ Ajout `_description` sur tous les modèles
- ✅ Mise à jour structure assets dans manifest
- ✅ Version format `17.0.x.x.x`
- ✅ Modernisation syntaxe XML

## Support
Pour toute question ou problème, contacter le support technique.

## Auteur
Votre Société

## Licence
LGPL-3
