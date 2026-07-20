{
    'name': 'FNE - Certification Factures de Vente',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Certification automatique des factures de vente via API FNE Côte d\'Ivoire',
    'description': '''
        Ce module permet de certifier les factures de vente auprès de la plateforme FNE 
        (Facture Normalisée Électronique) de la DGI Côte d'Ivoire.

        Fonctionnalités:
        - Certification manuelle via bouton avec confirmation
        - Rafraîchissement automatique après certification
        - Support des templates FNE (B2B, B2C, B2G, B2F)
        - Gestion des taxes personnalisées
        - Stockage du token de vérification et QR code
        - Tests avec l'environnement sandbox FNE
        - Support multi-société
    ''',
    'author': 'Votre Société',
    'website': 'https://www.votresociete.com',
    'depends': ['base', 'contacts', 'account', 'sale'],
    'external_dependencies': {
        'python': ['requests', 'qrcode'],
    },
    'data': [
        'security/ir.model.access.csv',
        #'data/fne_config_data.xml',
        'views/account_move_views.xml',
        'views/view_ncc.xml',
        'views/vue_ids_facture.xml',
        'reports/template.xml',
        'reports/invoice_report_fne_cia.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'fne_sale_invoice_certification/static/src/js/fne_refresh.js',
        ],
        'web.report_assets_common': [
            'fne_sale_invoice_certification/static/src/css/payroll_layout.css',
        ],
    },
    'images': ['static/description/banner.png'],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
