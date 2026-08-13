# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    """Extension res.partner pour la fiche Contact 360°.

    Ajoute deux méthodes RPC utilisées par les onglets contribués :
    - get_civora_portfolio : biens dont le contact est propriétaire
    - get_civora_tenants   : locataires actuels des biens du contact (propriétaire)

    Aucun nouveau champ, seulement des computed helpers exposés via RPC.
    """
    _inherit = 'res.partner'

    # ---- Compteurs pour l'UI (déterminent si les onglets sont pertinents) ----
    civora_property_count = fields.Integer(
        compute='_compute_civora_property_count',
        string="Biens possédés",
        help="Nombre de biens dont ce contact est propriétaire.",
    )
    civora_active_tenants_count = fields.Integer(
        compute='_compute_civora_active_tenants_count',
        string="Locataires actuels",
        help="Nombre de locataires actuels sur l'ensemble des biens du contact.",
    )

    def _compute_civora_property_count(self):
        Property = self.env.get('civora.property')
        for p in self:
            if Property is None:
                p.civora_property_count = 0
                continue
            p.civora_property_count = Property.search_count([('owner_id', '=', p.id)])

    def _compute_civora_active_tenants_count(self):
        Property = self.env.get('civora.property')
        for p in self:
            if Property is None:
                p.civora_active_tenants_count = 0
                continue
            biens = Property.search([('owner_id', '=', p.id)])
            tenants = biens.mapped('tenant_id').filtered(lambda x: x)
            p.civora_active_tenants_count = len(tenants)

    # ══════════════════════════════════════════════════════════════════
    # RPC — Portefeuille
    # ══════════════════════════════════════════════════════════════════
    @api.model
    def get_civora_portfolio(self, contact_id, group_by='none'):
        """Wrapper avec capture d'erreur."""
        try:
            return self._get_civora_portfolio_impl(contact_id, group_by)
        except Exception as e:
            import logging, traceback
            _logger = logging.getLogger(__name__)
            _logger.exception("[CIVORA] get_civora_portfolio error for contact %s", contact_id)
            return {
                'contact_id': contact_id, 'contact_name': "",
                'total': 0, 'items': [], 'groups': [],
                'by_status': {}, 'total_rent': 0,
                'error': str(e),
                'error_trace': traceback.format_exc().splitlines()[-5:],
            }

    def _get_civora_portfolio_impl(self, contact_id, group_by='none'):
        """Retourne les biens dont le contact est propriétaire."""
        Property = self.env.get('civora.property')
        if Property is None or not contact_id:
            return {
                'contact_id': contact_id, 'contact_name': "",
                'total': 0, 'items': [], 'groups': [],
                'by_status': {}, 'total_rent': 0,
            }
        contact = self.browse(contact_id)
        if not contact.exists():
            return {
                'contact_id': contact_id, 'contact_name': "",
                'total': 0, 'items': [], 'groups': [],
                'by_status': {}, 'total_rent': 0,
            }

        biens = Property.sudo().search([('owner_id', '=', contact_id)], order='name asc')
        items = []
        for b in biens:
            try:
                items.append(self._serialize_property_for_portfolio(b))
            except Exception:
                # Un bien qui plante ne casse pas tout le portefeuille
                import logging
                logging.getLogger(__name__).exception("[CIVORA] serialize property %s failed", b.id)

        by_status = {}
        total_rent = 0
        for it in items:
            s = it['status'] or 'unknown'
            by_status[s] = by_status.get(s, 0) + 1
            if it['status'] == 'loue' and it['monthly_rent']:
                total_rent += it['monthly_rent']

        result = {
            'contact_id': contact.id,
            'contact_name': contact.display_name or "",
            'total': len(items),
            'by_status': by_status,
            'total_rent': total_rent,
        }

        if group_by == 'none':
            result['items'] = items
            result['groups'] = []
        elif group_by == 'status':
            result['items'] = []
            result['groups'] = self._group_portfolio_by_status(items)
        elif group_by == 'city':
            result['items'] = []
            result['groups'] = self._group_portfolio_by_city(items)
        else:
            result['items'] = items
            result['groups'] = []

        return result

    def _serialize_property_for_portfolio(self, bien):
        """Sérialise un bien pour l'onglet Portefeuille."""
        vals = {
            'id': bien.id,
            'name': bien.display_name,
            'ref': getattr(bien, 'ref', '') or '',
            'city': getattr(bien, 'city', '') or '',
            'status': bien.status,
            'is_building': getattr(bien, 'is_building', False),
        }
        try:
            status_selection = dict(bien._fields['status'].selection)
            vals['status_label'] = status_selection.get(bien.status, bien.status or '')
        except Exception:
            vals['status_label'] = bien.status or ''
        vals['tenant_id'] = bien.tenant_id.id if bien.tenant_id else False
        vals['tenant_name'] = bien.tenant_id.display_name if bien.tenant_id else ""
        # Bail actif + loyer contractuel du bail (source de vérité)
        Lease = self.env.get('civora.lease')
        ACTIVE_LEASE_STATES = ['actif', 'retard', 'expire_bientot']
        active_lease = None
        monthly_rent = 0
        if Lease is not None:
            try:
                active_lease = Lease.sudo().search([
                    ('property_id', '=', bien.id),
                    ('status', 'in', ACTIVE_LEASE_STATES),
                ], limit=1, order='date_start desc')
                if active_lease:
                    try:
                        monthly_rent = float(active_lease.rent or 0)
                    except Exception:
                        monthly_rent = 0
            except Exception:
                active_lease = None
        # Fallback si le bien porte un loyer indicatif
        if not monthly_rent:
            for candidate in ('rent_amount', 'monthly_rent', 'active_rent', 'contract_rent'):
                if candidate in bien._fields:
                    v = getattr(bien, candidate, 0) or 0
                    if v:
                        monthly_rent = v
                        break
        vals['monthly_rent'] = monthly_rent
        vals['active_lease_id'] = active_lease.id if active_lease else False
        vals['active_lease_ref'] = active_lease.name if active_lease else ""
        vals['image_url'] = ""
        if 'image_1920' in bien._fields and bien.image_1920:
            vals['image_url'] = "/web/image/civora.property/%d/image_1920" % bien.id
        return vals

    def _group_portfolio_by_status(self, items):
        """Groupe les biens du portefeuille par statut."""
        # Ordre logique — codes réels de civora.property
        STATUS_ORDER = ['loue', 'saisonnier', 'disponible']
        STATUS_LABELS = {
            'loue': "Loués",
            'saisonnier': "Saisonniers",
            'disponible': "Disponibles",
        }
        buckets = {}
        for it in items:
            key = it['status'] or 'unknown'
            buckets.setdefault(key, []).append(it)
        groups = []
        seen = set()
        for status in STATUS_ORDER:
            if status in buckets:
                groups.append({
                    'id': 'status_' + status,
                    'name': STATUS_LABELS.get(status, status.title()),
                    'count': len(buckets[status]),
                    'items': buckets[status],
                    'status': status,
                })
                seen.add(status)
        for status, its in buckets.items():
            if status in seen:
                continue
            groups.append({
                'id': 'status_' + str(status),
                'name': STATUS_LABELS.get(status, (status or "Autre").title()),
                'count': len(its),
                'items': its,
                'status': status,
            })
        return groups

    def _group_portfolio_by_city(self, items):
        """Groupe les biens du portefeuille par ville."""
        buckets = {}
        for it in items:
            key = it['city'] or "Sans ville"
            buckets.setdefault(key, []).append(it)
        groups = []
        for city in sorted(buckets.keys(), key=lambda x: x.lower()):
            groups.append({
                'id': 'city_' + city,
                'name': city,
                'count': len(buckets[city]),
                'items': buckets[city],
            })
        return groups

    # ══════════════════════════════════════════════════════════════════
    # RPC — Locataires du propriétaire
    # ══════════════════════════════════════════════════════════════════
    @api.model
    def get_civora_tenants(self, contact_id):
        """Wrapper avec capture d'erreur pour éviter les 500 opaques
        qui produisent un onglet blanc côté client.
        """
        try:
            return self._get_civora_tenants_impl(contact_id)
        except Exception as e:
            import logging, traceback
            _logger = logging.getLogger(__name__)
            _logger.exception("[CIVORA] get_civora_tenants error for contact %s", contact_id)
            return {
                'contact_id': contact_id, 'contact_name': "",
                'total': 0, 'tenants': [],
                'error': str(e),
                'error_trace': traceback.format_exc().splitlines()[-5:],
            }

    def _get_civora_tenants_impl(self, contact_id):
        """Retourne les locataires actuels des biens du contact (propriétaire)."""
        Property = self.env.get('civora.property')
        if Property is None or not contact_id:
            return {
                'contact_id': contact_id, 'contact_name': "",
                'total': 0, 'tenants': [],
            }
        contact = self.browse(contact_id)
        if not contact.exists():
            return {
                'contact_id': contact_id, 'contact_name': "",
                'total': 0, 'tenants': [],
            }

        biens = Property.sudo().search([('owner_id', '=', contact_id)])
        Lease = self.env.get('civora.lease')
        # Statuts de bail considérés "en cours"
        ACTIVE_LEASE_STATES = ['actif', 'retard', 'expire_bientot']

        by_tenant = {}
        for bien in biens:
            try:
                tenant = bien.tenant_id
            except Exception:
                tenant = False
            if not tenant:
                continue
            tid = tenant.id
            if tid not in by_tenant:
                by_tenant[tid] = {
                    'id': tenant.id,
                    'name': tenant.display_name or "",
                    'phone': tenant.phone or "",
                    'email': tenant.email or "",
                    'biens': [],
                    'total_rent': 0,
                    'lease_status_agg': 'actif',
                }

            lease_id = False
            lease_ref = ""
            lease_status = ""
            lease_start = ""
            lease_end = ""
            monthly_rent = 0
            # Recherche du bail actif en isolant tout ce qui peut planter
            if Lease is not None:
                try:
                    active_lease = Lease.sudo().search([
                        ('property_id', '=', bien.id),
                        ('tenant_id', '=', tid),
                        ('status', 'in', ACTIVE_LEASE_STATES),
                    ], limit=1, order='date_start desc')
                    if active_lease:
                        lease_id = active_lease.id
                        lease_ref = active_lease.name or ""
                        lease_status = active_lease.status or ""
                        if active_lease.date_start:
                            lease_start = str(active_lease.date_start)
                        if active_lease.date_end:
                            lease_end = str(active_lease.date_end)
                        try:
                            monthly_rent = float(active_lease.rent or 0)
                        except Exception:
                            monthly_rent = 0
                except Exception:
                    pass

            by_tenant[tid]['biens'].append({
                'id': bien.id,
                'name': bien.display_name or "",
                'ref': getattr(bien, 'ref', '') or '',
                'city': getattr(bien, 'city', '') or '',
                'monthly_rent': monthly_rent,
                'lease_id': lease_id,
                'lease_ref': lease_ref,
                'lease_status': lease_status,
                'lease_start': lease_start,
                'lease_end': lease_end,
            })
            by_tenant[tid]['total_rent'] += monthly_rent

        tenants = sorted(by_tenant.values(), key=lambda t: (t['name'] or "").lower())
        return {
            'contact_id': contact.id,
            'contact_name': contact.display_name or "",
            'total': len(tenants),
            'tenants': tenants,
        }
