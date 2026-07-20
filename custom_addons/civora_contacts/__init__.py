# -*- coding: utf-8 -*-
from . import models


def _assign_company_to_civora_contacts(env):
    """Cloisonnement strict : les contacts CIVORA existants sans societe
    (company_id vide) deviendraient invisibles avec la nouvelle regle. On les
    rattache a la societe principale pour preserver la visibilite des donnees.
    Couvre le flag civora_is_contact ET les partenaires a role CIVORA
    (acquereurs, proprietaires, locataires...).
    """
    partners = env['res.partner'].sudo().search([
        '|', ('civora_is_contact', '=', True), ('civora_role_ids', '!=', False),
        ('company_id', '=', False),
    ])
    if partners:
        partners.write({'company_id': env.ref('base.main_company').id})
