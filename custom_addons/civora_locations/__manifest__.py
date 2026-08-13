# -*- coding: utf-8 -*-
{
    'name': "CIVORA Locations",
    'summary': "Gestion locative : baux, loyers, encaissements, contrats numériques",
    'description': """
CIVORA Locations v2.0.0
========================
- Modèles : civora.lease, civora.lease.payment, civora.lease.receipt
- Modèles contrats : civora.lease.clause, civora.lease.clause.set,
  civora.lease.contract (workflow signature bailleur → locataire)
- Écran Paramétrage des clauses par type de bail et société
- Rapport PDF Quittance + Rapport PDF Contrat de bail (calqué Alamako)
- Onglet "Contrat" dans la fiche Bail 360° : aperçu, pad de signature bailleur,
  génération du lien locataire, WhatsApp
- Seed de 22 clauses standard (bail d'habitation longue durée)
    """,
    'author': "NK SERVICE",
    'website': "https://service-odoo.com",
    'category': 'Real Estate',
    'version': '19.0.5.0.0',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'mail', 'portal', 'civora_core', 'civora_contacts', 'civora_biens', 'civora_agence', 'civora_pipeline', 'civora_documents'],
    'data': [
        'security/ir.model.access.csv',
        'security/civora_locations_rules.xml',
        'data/civora_lease_sequence.xml',
        'data/civora_lease_clauses_seed.xml',
        'data/civora_lease_contract_cron.xml',
        'data/civora_lease_reminder_cron.xml',
        'reports/lease_receipt_report.xml',
        'reports/lease_contract_report.xml',
        'reports/lease_formal_notice_report.xml',
        'views/civora_locations_menu.xml',
        'views/portal/portal_contract_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # SCSS
            'civora_locations/static/src/leases/leases_screen.scss',
            'civora_locations/static/src/leases/lease_drawer.scss',
            'civora_locations/static/src/lease_detail/lease_360.scss',
            'civora_locations/static/src/property_tab/property_lease_tab.scss',
            'civora_locations/static/src/clauses/clauses_screen.scss',
            'civora_locations/static/src/contracts/contract_tab.scss',
            'civora_locations/static/src/installments/installment_schedule.scss',
            'civora_locations/static/src/finance/finance_overview.scss',
            'civora_locations/static/src/finance/payment_method_stats.scss',
            'civora_locations/static/src/finance/initial_payment_wizard.scss',
            'civora_locations/static/src/finance/deposit_refund.scss',
            'civora_locations/static/src/timeline/lease_timeline.scss',
            'civora_locations/static/src/incidents/incidents_tab.scss',
            'civora_locations/static/src/incidents/reminder_drawer.scss',
            'civora_locations/static/src/arrears/arrears_view.scss',
            'civora_locations/static/src/arrears/bulk_reminder_dialog.scss',
            'civora_locations/static/src/opportunity_patch/opportunity_lease_patch.scss',
            # JS
            'civora_locations/static/src/arrears/bulk_reminder_dialog.js',
            'civora_locations/static/src/arrears/arrears_view.js',
            'civora_locations/static/src/leases/lease_drawer.js',
            'civora_locations/static/src/leases/leases_screen.js',
            'civora_locations/static/src/lease_detail/lease_360.js',
            'civora_locations/static/src/property_tab/property_lease_tab.js',
            'civora_locations/static/src/property_patch/property_360_patch.js',
            'civora_locations/static/src/clauses/clauses_screen.js',
            'civora_locations/static/src/contracts/contract_tab.js',
            'civora_locations/static/src/installments/installment_schedule.js',
            'civora_locations/static/src/finance/finance_overview.js',
            'civora_locations/static/src/finance/payment_method_stats.js',
            'civora_locations/static/src/finance/initial_payment_wizard.js',
            'civora_locations/static/src/finance/deposit_refund.js',
            'civora_locations/static/src/timeline/lease_timeline.js',
            'civora_locations/static/src/incidents/incidents_tab.js',
            'civora_locations/static/src/incidents/reminder_drawer.js',
            'civora_locations/static/src/opportunity_patch/opportunity_lease_patch.js',
            'civora_locations/static/src/command_center_patch/command_center_locations_patch.js',
            'civora_locations/static/src/documents_bridge/lease_documents_patch.js',
            # XML templates
            'civora_locations/static/src/arrears/bulk_reminder_dialog.xml',
            'civora_locations/static/src/arrears/arrears_view.xml',
            'civora_locations/static/src/leases/lease_drawer.xml',
            'civora_locations/static/src/leases/leases_screen.xml',
            'civora_locations/static/src/lease_detail/lease_360.xml',
            'civora_locations/static/src/property_tab/property_lease_tab.xml',
            'civora_locations/static/src/property_patch/property_360_inherit.xml',
            'civora_locations/static/src/clauses/clauses_screen.xml',
            'civora_locations/static/src/contracts/contract_tab.xml',
            'civora_locations/static/src/installments/installment_schedule.xml',
            'civora_locations/static/src/finance/finance_overview.xml',
            'civora_locations/static/src/finance/payment_method_stats.xml',
            'civora_locations/static/src/finance/initial_payment_wizard.xml',
            'civora_locations/static/src/finance/deposit_refund.xml',
            'civora_locations/static/src/timeline/lease_timeline.xml',
            'civora_locations/static/src/incidents/incidents_tab.xml',
            'civora_locations/static/src/incidents/reminder_drawer.xml',
            'civora_locations/static/src/opportunity_patch/opportunity_lease_patch.xml',
            # SCSS divers
            'civora_locations/static/src/property_patch/property_360_patch.scss',
        ],
        'web.assets_frontend': [
            'civora_locations/static/src/portal/portal_contract.scss',
        ],
        'web.report_assets_common': [
            'civora_locations/static/src/reports/civora_report_overrides.scss',
        ],
    },
    'installable': True,
    'application': False,
}
