# -*- coding: utf-8 -*-
{
    'name': "CIVORA Pipeline",
    'summary': "Pistes & Pipeline commercial CIVORA",
    'description': """
CIVORA Pipeline
===============
- civora.lead : pistes entrantes (Nouveau / A qualifier / Qualifie / Rejete).
- civora.opportunity : opportunites du pipeline (kanban par etape).
- civora.pipeline.stage : etapes parametrables PAR SOCIETE (Nouveau -> Qualifie
  -> Visite -> Offre -> Gagne/Perdu). Chaque societe peut renommer, reordonner,
  ajouter ou supprimer ses propres etapes depuis l'ecran Pipeline.
Qualifier une piste cree l'opportunite associee.
    """,
    'author': "NK SERVICE",
    'website': "https://service-odoo.com",
    'category': 'Real Estate',
    'version': '19.0.10.5.0',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'mail', 'civora_core', 'civora_contacts', 'civora_biens', 'civora_agence'],
    'data': [
        'security/ir.model.access.csv',
        'security/civora_pipeline_rules.xml',
        'views/civora_pipeline_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'civora_pipeline/static/src/components/civora_autocomplete.scss',
            'civora_pipeline/static/src/leads/leads_screen.scss',
            'civora_pipeline/static/src/pipeline/pipeline_screen.scss',
            'civora_pipeline/static/src/pipeline/opportunity_360.scss',
            'civora_pipeline/static/src/pipeline/history_activities.scss',
            'civora_pipeline/static/src/contact_tab/contact_opps_tab.scss',
            'civora_pipeline/static/src/components/civora_autocomplete.js',
            'civora_pipeline/static/src/components/civora_autocomplete.xml',
            'civora_pipeline/static/src/leads/lead_drawer.js',
            'civora_pipeline/static/src/leads/lead_drawer.xml',
            'civora_pipeline/static/src/leads/leads_screen.js',
            'civora_pipeline/static/src/leads/leads_screen.xml',
            'civora_pipeline/static/src/pipeline/opportunity_drawer.js',
            'civora_pipeline/static/src/pipeline/opportunity_drawer.xml',
            'civora_pipeline/static/src/pipeline/history_tab.js',
            'civora_pipeline/static/src/pipeline/history_tab.xml',
            'civora_pipeline/static/src/pipeline/activities_tab.js',
            'civora_pipeline/static/src/pipeline/activities_tab.xml',
            'civora_pipeline/static/src/pipeline/pipeline_screen.js',
            'civora_pipeline/static/src/pipeline/pipeline_screen.xml',
            'civora_pipeline/static/src/pipeline/opportunity_360.js',
            'civora_pipeline/static/src/pipeline/opportunity_360.xml',
            'civora_pipeline/static/src/contact_tab/contact_opps_tab.js',
            'civora_pipeline/static/src/contact_tab/contact_opps_tab.xml',
            'civora_pipeline/static/src/property_tab/property_opps_tab.js',
            'civora_pipeline/static/src/property_tab/property_opps_tab.xml',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
}
