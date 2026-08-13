# -*- coding: utf-8 -*-
{
    'name': "CIVORA 360° · Documents",
    'summary': "GED centrale — 6 dossiers, typologie 11 types, versions, signatures, audit.",
    'description': """
CIVORA 360° · Documents (v2)
============================
GED transversale alignée sur le référentiel front CIVORA :
- 6 dossiers canoniques (Baux & contrats, Factures, Docs propriétaires,
  Docs locataires, Docs biens, Médias & photos)
- 11 types de documents (Bail, Mandat, Contrat, EDL, Facture, Quittance,
  Reporting, Diagnostic, Photo, Média, Autre)
- Fiche 360° 4 onglets : Vue d'ensemble / Versions / Signatures / Audit
- Versioning natif avec historique et restauration
- Circuit de signature avec signataires
- Journal d'audit immuable
- Liens explicites Bien / Contact pour navigation croisée
    """,
    'author': "NK SERVICE",
    'website': "https://nk-service.ci",
    'category': "CIVORA/Core",
    'version': '19.0.3.0.4',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'mail', 'civora_core', 'civora_contacts', 'civora_biens'],
    'data': [
        'security/ir.model.access.csv',
        'security/civora_documents_rules.xml',
        'data/civora_document_sequence.xml',
        'data/civora_document_tag_seed.xml',
        'views/civora_documents_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # SCSS
            'civora_documents/static/src/home/documents_home.scss',
            'civora_documents/static/src/folder/folder_view.scss',
            'civora_documents/static/src/detail/document_detail.scss',
            'civora_documents/static/src/detail/document_drawer.scss',
            'civora_documents/static/src/detail/document_preview.scss',
            'civora_documents/static/src/tab/documents_tab.scss',
            # JS - shared
            'civora_documents/static/src/shared/constants.js',
            # JS - detail (utilisés par home + folder)
            'civora_documents/static/src/detail/document_preview.js',
            'civora_documents/static/src/detail/document_drawer.js',
            'civora_documents/static/src/detail/document_detail.js',
            # JS - home + folder
            'civora_documents/static/src/home/documents_home.js',
            'civora_documents/static/src/folder/folder_view.js',
            # JS - tab (contribution 360°)
            'civora_documents/static/src/tab/documents_tab.js',
            # JS - contribution property 360°
            'civora_documents/static/src/property_bridge/property_documents_tab.js',
            # SCSS - contribution contact 360°
            'civora_documents/static/src/contact_bridge/contact_bridge.scss',
            # JS - contribution contact 360°
            'civora_documents/static/src/contact_bridge/contact_documents_tab.js',
            'civora_documents/static/src/contact_bridge/contact_portfolio_tab.js',
            'civora_documents/static/src/contact_bridge/contact_tenants_tab.js',
            # XML
            'civora_documents/static/src/detail/document_preview.xml',
            'civora_documents/static/src/detail/document_drawer.xml',
            'civora_documents/static/src/detail/document_detail.xml',
            'civora_documents/static/src/home/documents_home.xml',
            'civora_documents/static/src/folder/folder_view.xml',
            'civora_documents/static/src/tab/documents_tab.xml',
            'civora_documents/static/src/property_bridge/property_documents_tab.xml',
            'civora_documents/static/src/contact_bridge/contact_documents_tab.xml',
            'civora_documents/static/src/contact_bridge/contact_portfolio_tab.xml',
            'civora_documents/static/src/contact_bridge/contact_tenants_tab.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
