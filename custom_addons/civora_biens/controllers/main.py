# -*- coding: utf-8 -*-
from werkzeug.exceptions import NotFound

import json

from odoo import fields, http
from odoo.http import request


def _json_ok(**extra):
    payload = {'ok': True}
    payload.update(extra)
    return request.make_response(
        json.dumps(payload), headers=[('Content-Type', 'application/json')])


def _json_err(message):
    return request.make_response(
        json.dumps({'ok': False, 'error': message}),
        headers=[('Content-Type', 'application/json')])


class CivoraBienPublic(http.Controller):
    """Fiche publique d'un bien, accessible sans compte via un jeton."""

    def _get_shared_property(self, token):
        if not token:
            return None
        prop = request.env['civora.property'].sudo().search([
            ('access_token', '=', token),
        ], limit=1)
        if not prop:
            return None
        # Acces direct (bien partage) OU acces herite (unite d'un immeuble partage).
        if not prop._is_publicly_accessible():
            return None
        return prop

    def _unit_public_url(self, unit):
        """URL publique d'une unite : via son propre token si present,
        sinon on en genere un a la volee (immeuble deja partage)."""
        unit._ensure_share_token()
        return "/civora/bien/" + unit.access_token

    def _property_card(self, prop):
        """Serialise une unite pour la grille publique."""
        def _fmt(amount):
            return "{:,}".format(int(amount or 0)).replace(",", " ") + " FCFA"
        cover = prop.image_ids.sorted(lambda r: (r.sequence, r.id))[:1]
        status_labels = {'disponible': "Disponible", 'loue': "Loué", 'saisonnier': "Saisonnier"}
        price = _fmt(prop.monthly_revenue) + " /mois" if prop.monthly_revenue else _fmt(prop.price)
        url = self._unit_public_url(prop)  # assure le token avant usage
        cover_style = ""
        if cover:
            cover_style = "background-image:url(/civora/bien/%s/photo/%s)" % (prop.access_token, cover.id)
        return {
            'id': prop.id,
            'name': prop.name,
            'unit_number': prop.unit_number or "",
            'floor': prop.floor or 0,
            'status_label': status_labels.get(prop.status, ''),
            'status': prop.status,
            'bedrooms': prop.bedrooms or 0,
            'bathrooms': prop.bathrooms or 0,
            'surface': int(prop.surface or 0),
            'price_str': price,
            'url': url,
            'has_cover': bool(cover),
            'cover_style': cover_style,
        }

    @http.route(['/civora/bien/<string:token>'], type='http', auth='public', website=False, sitemap=False)
    def public_property(self, token, **kw):
        prop = self._get_shared_property(token)
        if not prop:
            raise NotFound()
        images = prop.image_ids.sorted(lambda r: (r.sequence, r.id))
        status_labels = {
            'disponible': "Disponible",
            'loue': "Loué",
            'saisonnier': "Saisonnier",
        }

        def _fmt(amount):
            return "{:,}".format(int(amount or 0)).replace(",", " ") + " FCFA"

        loc = ", ".join([p for p in [prop.neighborhood, prop.city] if p])

        # Immeuble : liste des unites. Unite : immeuble parent + unites soeurs.
        units = []
        parent_info = None
        siblings = []
        if prop.is_building:
            units = [self._property_card(u) for u in prop._public_units()]
        elif prop.parent_id:
            parent = prop.parent_id
            parent._ensure_share_token()
            parent_info = {'name': parent.name, 'url': "/civora/bien/" + parent.access_token}
            for sib in parent.unit_ids.sorted(lambda u: (u.floor or 0, u.unit_number or "", u.name or "")):
                if sib.id != prop.id:
                    siblings.append(self._property_card(sib))

        values = {
            'prop': prop,
            'images': images,
            'token': token,
            'status_label': status_labels.get(prop.status, ''),
            'price_str': _fmt(prop.price),
            'revenue_str': _fmt(prop.monthly_revenue) if prop.monthly_revenue else "",
            'loc': loc,
            # Carte : on n'affiche rien si les coordonnees sont absentes ou a
            # zero. Un (0, 0) place le marqueur dans le golfe de Guinee — mieux
            # vaut pas de carte du tout qu'une carte fausse.
            'has_geo': bool(prop.latitude and prop.longitude),
            'latitude': prop.latitude or 0.0,
            'longitude': prop.longitude or 0.0,
            'type_label': prop.property_type_id.name or "",
            'is_rental': prop.transaction in ('location', 'saisonnier'),
            'is_sale': prop.transaction == 'vente',
            'is_building': prop.is_building,
            'units': units,
            'units_total': prop.total_units or len(units),
            'units_available': len([u for u in units if u['status'] == 'disponible']),
            'parent_info': parent_info,
            'siblings': siblings,
            # Nom de l'agence, pas 'CIVORA' : la page est en marque blanche.
            'company_name': prop.company_id.name or '',
            'sent': kw.get('sent') == '1',
            'form_error': kw.get('error') == '1',
        }
        html = request.env['ir.qweb']._render('civora_biens.public_property_page', values)
        return request.make_response(
            "<!DOCTYPE html>\n" + str(html),
            headers=[('Content-Type', 'text/html; charset=utf-8')],
        )

    @http.route(['/civora/bien/<string:token>/photo/<int:image_id>'], type='http', auth='public', sitemap=False)
    def public_photo(self, token, image_id, **kw):
        prop = self._get_shared_property(token)
        if not prop:
            raise NotFound()
        image = request.env['civora.property.image'].sudo().browse(image_id).exists()
        if not image or image.property_id.id != prop.id:
            raise NotFound()
        stream = request.env['ir.binary']._get_image_stream_from(image, field_name='image_512')
        return stream.get_response()

    @http.route(['/civora/bien/<string:token>/visite'], type='http', auth='public',
                methods=['POST'], csrf=False, sitemap=False)
    def public_visit_request(self, token, **post):
        prop = self._get_shared_property(token)
        if not prop:
            raise NotFound()
        # Anti-spam : champ appat cache (rempli seulement par des bots).
        if (post.get('website') or '').strip():
            # Pot de miel rempli : on simule un succes pour ne rien apprendre
            # au robot.
            return _json_ok() if post.get('ajax') else request.redirect(
                '/civora/bien/%s?sent=1' % token)
        name = (post.get('name') or '').strip()
        phone = (post.get('phone') or '').strip()
        if not name or not phone:
            if post.get('ajax'):
                return _json_err("Merci d'indiquer au minimum votre nom et votre téléphone.")
            return request.redirect('/civora/bien/%s?error=1' % token)

        # Date souhaitee : on ne fait jamais echouer une demande a cause d'un
        # format de date. Une date illisible est simplement ignoree.
        preferred = False
        raw_date = (post.get('preferred_date') or '').strip()
        if raw_date:
            try:
                preferred = fields.Date.to_date(raw_date)
            except (ValueError, TypeError):
                preferred = False

        vr = request.env['civora.visit.request'].sudo().create({
            'property_id': prop.id,
            'name': name,
            'phone': phone,
            'email': (post.get('email') or '').strip() or False,
            'preferred_date': preferred,
            'message': (post.get('message') or '').strip() or False,
        })

        # Notifie l'agent referent (activite "a faire").
        agent = prop.agent_id
        if agent:
            note = "%s (%s) souhaite visiter ce bien." % (name, phone)
            if preferred:
                note += " Date souhaitee : %s." % preferred.strftime('%d/%m/%Y')
            vr.sudo().activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=agent.id,
                summary="Demande de visite : %s" % prop.name,
                note=note,
            )

        # Le formulaire est envoye en fetch() : on repond en JSON pour
        # afficher l'accuse sans recharger la page ni perdre la position
        # de defilement du visiteur.
        if post.get('ajax'):
            return _json_ok()
        return request.redirect('/civora/bien/%s?sent=1' % token)
