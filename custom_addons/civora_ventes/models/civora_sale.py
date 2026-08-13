# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CivoraSale(models.Model):
    _name = 'civora.sale'
    _description = 'Dossier de vente immobilière'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string="Référence",
        readonly=True,
        copy=False,
        default='Nouveau',
    )
    property_id = fields.Many2one(
        'civora.property',
        string="Bien",
        required=True,
        tracking=True,
    )
    seller_id = fields.Many2one(
        'res.partner',
        string="Vendeur",
        tracking=True,
    )
    buyer_id = fields.Many2one(
        'res.partner',
        string="Acquéreur",
        tracking=True,
    )
    agent_id = fields.Many2one(
        'res.users',
        string="Agent responsable",
        default=lambda self: self.env.user,
        tracking=True,
    )
    state = fields.Selection([
        ('mandat', 'Mandat signé'),
        ('commercialisation', 'En commercialisation'),
        ('offre', 'Offre reçue'),
        ('compromis', 'Compromis signé'),
        ('acte', 'Acte en cours'),
        ('cloture', 'Clôturée'),
        ('annule', 'Annulée'),
    ], string="État", default='mandat', required=True, tracking=True)

    mandate_type = fields.Selection([
        ('exclusif', 'Exclusif'),
        ('simple', 'Simple'),
        ('delegue', 'Délégué'),
    ], string="Type de mandat", default='simple', tracking=True)
    mandate_date = fields.Date(string="Date du mandat")
    mandate_end_date = fields.Date(string="Fin du mandat")

    asking_price = fields.Integer(string="Prix demandé (FCFA)")
    sale_amount = fields.Integer(string="Prix de vente final (FCFA)", tracking=True)

    commission_rate = fields.Float(string="Taux de commission (%)", default=5.0)
    commission_amount = fields.Integer(
        string="Commission agence (FCFA)",
        compute='_compute_commission',
        store=True,
    )

    amount_paid = fields.Integer(
        string="Montant encaissé (FCFA)", tracking=True,
        help="Cumul des sommes effectivement percues sur le dossier "
             "(acompte, sequestre, solde).")
    payment_progress = fields.Integer(
        string="Encaissement (%)", compute='_compute_payment_progress', store=True)
    full_payment_date = fields.Date(
        string="Date de solde", tracking=True,
        help="Date a laquelle le prix a ete integralement percu. Sert au "
             "calcul du delai acte -> encaissement.")
    closing_date = fields.Date(
        string="Closing", compute='_compute_closing_date', store=True,
        help="Date d'acte si elle existe, sinon date previsionnelle.")

    notary_name = fields.Char(string="Notaire")
    notary_phone = fields.Char(string="Téléphone notaire")

    compromis_date = fields.Date(string="Date du compromis", tracking=True)
    conditions_text = fields.Text(string="Conditions suspensives")
    acte_date = fields.Date(string="Date de l'acte", tracking=True)
    estimated_acte_date = fields.Date(string="Date acte prévisionnelle")

    offer_ids = fields.One2many('civora.sale.offer', 'sale_id', string="Offres")
    offer_count = fields.Integer(compute='_compute_offer_count')

    notes = fields.Text(string="Notes internes")

    company_id = fields.Many2one(
        'res.company',
        string="Société",
        default=lambda self: self.env.company,
        required=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = self.env['ir.sequence'].next_by_code('civora.sale') or 'Nouveau'
        return super().create(vals_list)

    @api.depends('amount_paid', 'sale_amount')
    def _compute_payment_progress(self):
        for rec in self:
            rec.payment_progress = (
                round(rec.amount_paid * 100.0 / rec.sale_amount)
                if rec.sale_amount else 0)

    @api.depends('acte_date', 'estimated_acte_date')
    def _compute_closing_date(self):
        for rec in self:
            rec.closing_date = rec.acte_date or rec.estimated_acte_date or False

    @api.depends('sale_amount', 'commission_rate')
    def _compute_commission(self):
        for rec in self:
            rec.commission_amount = int(rec.sale_amount * (rec.commission_rate or 0) / 100)

    def _compute_offer_count(self):
        for rec in self:
            rec.offer_count = len(rec.offer_ids)

    def action_commercialisation(self):
        self.ensure_one()
        self.write({'state': 'commercialisation'})

    def action_offre(self):
        self.ensure_one()
        self.write({'state': 'offre'})

    def action_compromis(self):
        self.ensure_one()
        if not self.buyer_id:
            raise ValidationError("Veuillez renseigner l'acquéreur avant de passer au compromis.")
        self.write({'state': 'compromis'})

    def action_acte(self):
        self.ensure_one()
        if not self.compromis_date:
            raise ValidationError("Veuillez renseigner la date du compromis.")
        self.write({'state': 'acte'})

    def action_cloturer(self):
        self.ensure_one()
        if not self.acte_date:
            raise ValidationError("Veuillez renseigner la date de l'acte.")
        if not self.sale_amount:
            raise ValidationError("Veuillez renseigner le prix de vente final.")
        self.write({'state': 'cloture'})
        if self.property_id:
            self.property_id.write({'status': 'vendu'})

    def action_annuler(self):
        self.ensure_one()
        self.write({'state': 'annule'})
        if self.property_id and self.property_id.status == 'vendu':
            self.property_id.write({'status': 'disponible'})

    @api.model
    def get_sales_kpis(self):
        today = fields.Date.today()
        month_start = today.replace(day=1)
        company_domain = [('company_id', 'in', self.env.companies.ids)]
        domain_active = [('state', 'not in', ['cloture', 'annule'])] + company_domain
        domain_closed = [('state', '=', 'cloture')] + company_domain

        active_records = self.search(domain_active)
        active = len(active_records)
        pipeline_value = sum(active_records.mapped('asking_price'))

        closed = self.search(domain_closed)
        volume_signed = sum(closed.mapped('sale_amount'))
        commission_total = sum(closed.mapped('commission_amount'))

        all_records = self.search(company_domain)
        total_count = len(all_records)
        closed_count = len(closed)
        transformation_rate = round(closed_count / total_count * 100) if total_count else 0

        avg_commission_rate = 0
        if closed:
            avg_commission_rate = round(sum(closed.mapped('commission_rate')) / len(closed), 1)

        return {
            'active': active,
            'pipeline_value': pipeline_value,
            'volume_signed': volume_signed,
            'commission_total': commission_total,
            'avg_commission_rate': avg_commission_rate,
            'transformation_rate': transformation_rate,
        }

    @api.model
    def get_pipeline_data(self):
        company_domain = [('company_id', 'in', self.env.companies.ids)]
        columns = [
            ('offre', 'Promesse'),
            ('compromis', 'Compromis signé'),
            ('acte', 'Acte authentique'),
            ('cloture', 'Encaissé'),
        ]
        result = []
        for state_key, label in columns:
            records = self.search([('state', '=', state_key)] + company_domain, order='create_date desc')
            cards = []
            for r in records:
                cards.append({
                    'id': r.id,
                    'name': r.name,
                    'property_name': r.property_id.name if r.property_id else '',
                    'city': r.property_id.city if r.property_id else '',
                    'amount': r.sale_amount or r.asking_price or 0,
                    'commission_rate': r.commission_rate or 0,
                    'agent_name': r.agent_id.name if r.agent_id else '',
                    'agent_initials': ''.join([w[0] for w in (r.agent_id.name or '').split()[:2]]).upper(),
                    'date': str(r.compromis_date or r.mandate_date or r.create_date.date()) if r.create_date else '',
                })
            total = sum(r.sale_amount or r.asking_price or 0 for r in records)
            result.append({
                'key': state_key,
                'label': label,
                'count': len(records),
                'total': total,
                'cards': cards,
            })
        return result


class CivoraSaleDashboard(models.Model):
    """Onglets Commissions et Performance de l'ecran Ventes.

    Ces deux onglets etaient des placeholders « module en cours de
    developpement ». Tout est desormais calcule a partir des dossiers :
    commissions par commercial, derniers reglements, volume par zone,
    duree du cycle de vente et alertes derivees de l'etat reel des dossiers.
    """

    _inherit = "civora.sale"

    @api.model
    def _initials(self, name):
        parts = (name or "").strip().split()
        return "".join(p[0].upper() for p in parts[:2])

    @api.model
    def get_sales_dashboard(self):
        from datetime import timedelta
        today = fields.Date.today()
        sales = self.search([("company_id", "in", self.env.companies.ids)])
        live = sales.filtered(lambda s: s.state not in ("annule",))
        states = dict(self._fields["state"].selection)

        # ---------- Transactions ----------
        transactions = [{
            "id": s.id,
            "ref": s.name or "",
            "property": s.property_id.name or "",
            "zone": s.property_id.neighborhood or s.property_id.city or "—",
            "buyer": s.buyer_id.name or "—",
            "seller": s.seller_id.name or "—",
            "agent": s.agent_id.name or "—",
            "agent_initials": self._initials(s.agent_id.name),
            "amount": s.sale_amount or s.asking_price,
            "paid": s.amount_paid,
            "progress": s.payment_progress,
            "state": s.state,
            "state_label": states.get(s.state, ""),
            "closing": fields.Date.to_string(s.closing_date) if s.closing_date else "—",
        } for s in sales]

        # ---------- Commissions par commercial ----------
        by_agent = {}
        for s in live:
            key = s.agent_id.id or 0
            entry = by_agent.setdefault(key, {
                "id": key,
                "name": s.agent_id.name or "Non assigné",
                "initials": self._initials(s.agent_id.name) or "NA",
                "deals": 0, "total": 0, "cashed": 0, "pending": 0,
            })
            entry["deals"] += 1
            entry["total"] += s.commission_amount
            # La commission est consideree encaissee quand le dossier est
            # cloture et le prix integralement percu.
            if s.state == "cloture" and s.sale_amount and s.amount_paid >= s.sale_amount:
                entry["cashed"] += s.commission_amount
            else:
                entry["pending"] += s.commission_amount
        agents = sorted(by_agent.values(), key=lambda a: -a["total"])

        recent = []
        for s in live.filtered(lambda x: x.commission_amount and x.closing_date).sorted(
                lambda x: x.closing_date, reverse=True)[:6]:
            recent.append({
                "id": s.id,
                "ref": s.name,
                "property": s.property_id.name or "",
                "date": fields.Date.to_string(s.closing_date),
                "agent": s.agent_id.name or "—",
                "rate": s.commission_rate,
                "amount": s.commission_amount,
            })

        total_commission = sum(a["total"] for a in agents)
        cashed = sum(a["cashed"] for a in agents)
        rates = [s.commission_rate for s in live if s.commission_rate]
        avg_rate = round(sum(rates) / len(rates), 2) if rates else 0

        # ---------- Performance ----------
        zones = {}
        for s in live.filtered(lambda x: x.state in ("compromis", "acte", "cloture")):
            zone = s.property_id.neighborhood or s.property_id.city or "Non renseignée"
            z = zones.setdefault(zone, {"name": zone, "volume": 0, "count": 0})
            z["volume"] += s.sale_amount or 0
            z["count"] += 1
        zone_rows = sorted(zones.values(), key=lambda z: -z["volume"])
        zone_max = zone_rows[0]["volume"] if zone_rows else 0
        for z in zone_rows:
            z["pct"] = round(z["volume"] * 100.0 / zone_max) if zone_max else 0

        promise_to_acte = [
            (s.acte_date - s.compromis_date).days
            for s in sales if s.acte_date and s.compromis_date and s.acte_date >= s.compromis_date
        ]
        acte_to_cash = [
            (s.full_payment_date - s.acte_date).days
            for s in sales
            if s.full_payment_date and s.acte_date and s.full_payment_date >= s.acte_date
        ]
        closed = live.filtered(lambda s: s.state == "cloture" and s.sale_amount)
        ticket = int(sum(closed.mapped("sale_amount")) / len(closed)) if closed else 0

        # ---------- Alertes derivees ----------
        alerts = []
        for s in live:
            if s.state == "compromis" and s.compromis_date:
                waiting = (today - s.compromis_date).days
                if waiting > 15:
                    alerts.append({
                        "id": "bank-%s" % s.id, "sale_id": s.id, "level": "warning",
                        "text": "%s : déblocage bancaire en attente (%s j)" % (s.name, waiting),
                    })
            if s.state == "acte" and not s.acte_date and s.estimated_acte_date \
                    and s.estimated_acte_date < today:
                alerts.append({
                    "id": "notary-%s" % s.id, "sale_id": s.id, "level": "danger",
                    "text": "%s : relance notaire requise" % s.name,
                })
            if s.state in ("compromis", "acte") and not s.amount_paid and s.compromis_date:
                late = (today - s.compromis_date).days
                if late > 5:
                    alerts.append({
                        "id": "deposit-%s" % s.id, "sale_id": s.id, "level": "danger",
                        "text": "%s : acompte en retard de %s j" % (s.name, late),
                    })

        return {
            "transactions": transactions,
            "agents": agents,
            "recent_commissions": recent,
            "commission_summary": {
                "total": total_commission,
                "cashed": cashed,
                "pending": total_commission - cashed,
                "agents": len(agents),
                "avg_rate": avg_rate,
            },
            "zones": zone_rows,
            "cycle": {
                "promise_to_acte": round(sum(promise_to_acte) / len(promise_to_acte))
                if promise_to_acte else 0,
                # Calcule uniquement sur les dossiers dont on connait la
                # date de solde ; sinon on renvoie None et le front affiche « — ».
                "acte_to_cash": (
                    round(sum(acte_to_cash) / len(acte_to_cash)) if acte_to_cash else None),
                "cancelled": len(sales.filtered(lambda s: s.state == "annule")),
                "ticket": ticket,
            },
            "alerts": alerts,
        }
