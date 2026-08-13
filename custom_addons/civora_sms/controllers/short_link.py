# -*- coding: utf-8 -*-
"""Redirection des liens courts : /s/<code>."""
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class CivoraShortLinkController(http.Controller):

    @http.route('/s/<string:code>', type='http', auth='public',
                website=False, sitemap=False, csrf=False)
    def civora_short_redirect(self, code, **kw):
        link = request.env['civora.short.link'].sudo().search(
            [('code', '=', code)], limit=1)
        if not link or not link.civora_is_valid():
            return request.not_found()
        link.civora_register_hit()
        # 302 et non 301 : un lien de signature ne doit jamais etre mis en
        # cache definitivement par un navigateur ou un proxy.
        return request.redirect(link.target_url, code=302, local=False)
