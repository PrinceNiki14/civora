{
    'name': 'FNE - Certification Factures Avoir',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Certification des factures d\'avoir auprès de la FNE Côte d\'Ivoire',
    'description': '''
        Ce module permet de certifier les factures d'avoir (avoirs/remboursements) 
        auprès de la plateforme FNE (Facture Normalisée Électronique) de la DGI Côte d'Ivoire.

        Fonctionnalités:
        - Certification automatique des avoirs liés à des factures FNE certifiées
        - Vérification d'éligibilité automatique
        - Correspondance automatique des articles avec IDs FNE
        - Support multi-société
        - Interface de debug pour le dépannage
    ''',
    'author': 'Votre Société',
    'website': 'https://www.votresociete.com',
    'depends': [
        'account',
        'fne_sale_invoice_certification',  # Module principal FNE
    ],
    'external_dependencies': {
        'python': ['requests'],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_refund_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
