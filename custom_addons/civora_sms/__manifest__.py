# -*- coding: utf-8 -*-
{
    'name': "CIVORA · SMS",
    'summary': "Passerelle SMS mutualisée pour la plateforme CIVORA",
    'description': """
CIVORA · SMS
============

Passerelle SMS transverse, consommable par n'importe quel module CIVORA
via une API unique :

    self.env['civora.sms'].civora_send(phone, message, partner=..., record=...)

Fournisseur : HSMS (hsms.ci).

Choix d'architecture — un seul fournisseur, volontairement.
Une abstraction multi-fournisseurs construite avant d'en avoir reellement
deux aboutit a des options mortes dans l'interface. Le service est isole
derriere une frontiere nette : ajouter un second operateur restera simple
le jour ou le besoin existera vraiment.

Contenu :
- Configuration HSMS PAR SOCIETE (chaque agence a son compte et son
  sender ID : un locataire doit voir le nom de son agence, pas 'CIVORA')
- File d'envoi traitee par cron, avec relances
- Historique complet avec ticket fournisseur
- Comptage de segments GSM-7 / UCS-2 et retrait optionnel des accents
- Raccourcisseur de liens interne (/s/<code>)
    """,
    'author': "NK SERVICE",
    'website': "https://service-odoo.com",
    'category': "CIVORA/Technique",
    'version': '19.0.1.0.0',
    'license': 'LGPL-3',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'security/civora_sms_rules.xml',
        'data/civora_sms_cron.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
