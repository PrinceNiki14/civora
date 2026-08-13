# -*- coding: utf-8 -*-
"""
Contrôleur public de signature locataire.

Routes :
  GET  /civora/contract/<token>              consultation + signature
  POST /civora/contract/<token>/remark       dépôt d'une remarque sur un article
  POST /civora/contract/<token>/sign         réception de la signature (PNG base64)
  GET  /civora/contract/<token>/confirmation accusé de signature
  GET  /civora/contract/<token>/pdf          téléchargement du PDF

Règle métier (option A) : tant qu'une remarque est en attente de réponse,
la signature est refusée. On ne signe pas un contrat que l'on conteste.
"""
import json
import logging

from markupsafe import Markup

from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)

# Etats pour lesquels la page de signature n'a pas de sens.
BLOCKED_STATES = {
    'cancelled': 'cancelled',
    'expired': 'expired',
    'terminated': 'terminated',
}


def _json(payload, status=200):
    return request.make_response(
        json.dumps(payload), status=status,
        headers=[('Content-Type', 'application/json')],
    )


def _client_ip():
    """IP réelle du visiteur, en tenant compte du reverse proxy."""
    fwd = request.httprequest.headers.get('X-Forwarded-For', '')
    if fwd:
        return fwd.split(',')[0].strip()
    return request.httprequest.remote_addr or ''


def _user_agent():
    return request.httprequest.headers.get('User-Agent', '')[:255]


class CivoraContractPortal(http.Controller):

    def _get_contract(self, token):
        return request.env['civora.lease.contract'].sudo().search(
            [('token', '=', token)], limit=1)

    # ══════════════════════════════════════════════════════════════════
    # Consultation + signature
    # ══════════════════════════════════════════════════════════════════
    @http.route('/civora/contract/<string:token>', type='http', auth='public',
                website=False, csrf=False)
    def contract_view(self, token, **kw):
        contract = self._get_contract(token)
        if not contract:
            return request.render('civora_locations.portal_contract_notfound',
                                  {'reason': 'not_found'})
        # 'terminated' etait absent de cette liste : la page s'affichait avec
        # un bouton Signer, et le POST echouait ensuite sur un message faux.
        if contract.state in BLOCKED_STATES:
            return request.render('civora_locations.portal_contract_notfound',
                                  {'reason': BLOCKED_STATES[contract.state]})

        if contract.state == 'signed_tenant':
            return request.redirect('/civora/contract/%s/confirmation' % token)

        can_sign, sign_blocked_reason = contract.civora_can_sign()
        return request.render('civora_locations.portal_contract_sign', {
            'contract': contract,
            'data': contract.render_html_preview(),
            'token': token,
            'already_signed': False,
            'can_sign': can_sign,
            'sign_blocked_reason': sign_blocked_reason,
            'remarks': contract.remark_ids.sorted(key=lambda r: r.id, reverse=True),
            'open_remarks': contract.remark_open_count,
        })

    # ══════════════════════════════════════════════════════════════════
    # Dépôt d'une remarque
    # ══════════════════════════════════════════════════════════════════
    @http.route('/civora/contract/<string:token>/remark', type='http',
                auth='public', methods=['POST'], csrf=False)
    def contract_remark(self, token, **post):
        contract = self._get_contract(token)
        if not contract or contract.state != 'signed_lessor':
            return _json({'ok': False,
                          'error': "Ce contrat n'accepte plus de remarques."})

        body = (post.get('body') or '').strip()
        if len(body) < 5:
            return _json({'ok': False,
                          'error': "Merci de détailler votre remarque."})

        try:
            request.env['civora.contract.remark'].sudo().civora_portal_create(
                contract, body,
                section_ref=post.get('section_ref'),
                section_label=post.get('section_label'),
                clause_id=post.get('clause_id') or None,
                ip=_client_ip(),
                user_agent=_user_agent(),
            )
        except Exception as e:  # noqa: BLE001
            _logger.exception("[CIVORA portal] echec depot de remarque")
            return _json({'ok': False, 'error': "Enregistrement impossible : %s" % e})

        return _json({'ok': True, 'reload': True})

    # ══════════════════════════════════════════════════════════════════
    # Signature
    # ══════════════════════════════════════════════════════════════════
    @http.route('/civora/contract/<string:token>/sign', type='http',
                auth='public', methods=['POST'], csrf=False)
    def contract_sign(self, token, **post):
        contract = self._get_contract(token)
        if not contract:
            return _json({'ok': False, 'error': "Contrat introuvable."})

        # Garde-fou metier : une remarque ouverte bloque la signature.
        can_sign, reason = contract.civora_can_sign()
        if not can_sign:
            return _json({'ok': False, 'error': reason})

        sign_data = post.get('signature', '')
        if sign_data.startswith('data:image'):
            sign_data = sign_data.split(',', 1)[-1]
        if not sign_data:
            return _json({'ok': False, 'error': "Signature manquante."})
        try:
            sign_bytes = sign_data.encode('ascii')
        except UnicodeEncodeError:
            return _json({'ok': False, 'error': "Signature mal encodee."})

        try:
            contract.write({
                'state': 'signed_tenant',
                'sign_tenant': sign_bytes,
                'signed_at_tenant': fields.Datetime.now(),
                'sign_tenant_ip': _client_ip()[:64],
                'sign_tenant_ua': _user_agent(),
            })
            contract.message_post(
                body=Markup("Le locataire <b>%s</b> a signé le contrat "
                            "<b>%s</b> depuis l'adresse %s.")
                     % (contract.lease_id.tenant_id.name or "—",
                        contract.name, _client_ip() or "inconnue"),
                subtype_xmlid='mail.mt_note',
            )
        except Exception as e:  # noqa: BLE001
            _logger.exception("[CIVORA portal] echec enregistrement signature")
            return _json({'ok': False, 'error': str(e)})

        return _json({'ok': True,
                      'redirect': '/civora/contract/%s/confirmation' % token})

    # ══════════════════════════════════════════════════════════════════
    # Accusé de signature
    # ══════════════════════════════════════════════════════════════════
    @http.route('/civora/contract/<string:token>/confirmation', type='http',
                auth='public', website=False, csrf=False)
    def contract_confirmation(self, token, **kw):
        contract = self._get_contract(token)
        if not contract:
            return request.render('civora_locations.portal_contract_notfound',
                                  {'reason': 'not_found'})
        if contract.state != 'signed_tenant':
            return request.redirect('/civora/contract/%s' % token)

        signed = contract.signed_at_tenant
        return request.render('civora_locations.portal_contract_signed', {
            'contract': contract,
            'data': contract.render_html_preview(),
            'token': token,
            'tenant_name': contract.lease_id.tenant_id.name or "-",
            'signed_date': fields.Datetime.to_string(signed) if signed else '',
            'signed_ip': contract.sign_tenant_ip or '',
            # Nom du cookie surveille par le JS pour confirmer le telechargement
            'dl_cookie': 'civora_dl_%s' % contract.id,
        })

    # ══════════════════════════════════════════════════════════════════
    # Téléchargement du PDF
    # ══════════════════════════════════════════════════════════════════
    @http.route('/civora/contract/<string:token>/pdf', type='http',
                auth='public', csrf=False)
    def contract_pdf(self, token, **kw):
        contract = self._get_contract(token)
        if not contract or contract.state == 'cancelled':
            return request.not_found()

        report = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
            'civora_locations.action_report_lease_contract',
            res_ids=[contract.id],
        )
        pdf_content = report[0]
        filename = ("Contrat_%s.pdf" % (contract.name or "contrat")).replace(' ', '_')

        response = request.make_response(pdf_content, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf_content)),
            ('Content-Disposition', 'attachment; filename="%s"' % filename),
        ])
        # Un navigateur ne signale jamais la fin d'un telechargement. En
        # revanche, poser un cookie au moment ou le serveur envoie le fichier
        # permet au JS de detecter que le transfert a bien demarre - c'est
        # nettement plus honnete qu'un simple minuteur cote client.
        response.set_cookie(
            'civora_dl_%s' % contract.id, '1',
            max_age=120, path='/', samesite='Lax',
        )
        return response
