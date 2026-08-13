# -*- coding: utf-8 -*-
from . import models


def post_init_hook(env):
    """A l'installation du module, cree les 6 etapes par defaut pour chaque
    societe existante. Les societes creees ulterieurement les recevront via
    l'override de res.company.create()."""
    Stage = env['civora.pipeline.stage'].sudo()
    for company in env['res.company'].sudo().search([]):
        Stage._create_default_stages_for_company(company)

