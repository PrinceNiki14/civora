# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CivoraReservation(models.Model):
    _name = 'civora.reservation'
    _description = 'Réservation saisonnière'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'checkin_date desc, id desc'
    _check_company_auto = True

    name = fields.Char(
        string="Référence", readonly=True, copy=False,
        default=lambda self: _('Nouveau'))
    property_id = fields.Many2one(
        'civora.property', string="Bien", required=True,
        check_company=True, tracking=True)
    guest_id = fields.Many2one(
        'res.partner', string="Voyageur", required=True, tracking=True)
    agent_id = fields.Many2one(
        'res.users', string="Agent", default=lambda self: self.env.user,
        tracking=True)
    owner_id = fields.Many2one(
        'res.partner', string="Propriétaire",
        related='property_id.owner_id', store=True, readonly=True)

    checkin_date = fields.Date(
        string="Arrivée", required=True, tracking=True)
    checkout_date = fields.Date(
        string="Départ", required=True, tracking=True)
    num_nights = fields.Integer(
        string="Nuitées", compute='_compute_num_nights', store=True)
    num_guests = fields.Integer(string="Voyageurs", default=1)

    tariff_night = fields.Integer(string="Tarif / nuit (FCFA)", required=True)
    total_amount = fields.Integer(
        string="Montant total (FCFA)",
        compute='_compute_total_amount', store=True)
    deposit_amount = fields.Integer(string="Caution (FCFA)")
    deposit_status = fields.Selection([
        ('pending', 'En attente'),
        ('collected', 'Encaissée'),
        ('returned', 'Restituée'),
        ('retained', 'Retenue'),
    ], string="Statut caution", default='pending')

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmée'),
        ('checkin', 'En séjour'),
        ('checkout', 'Terminée'),
        ('cancelled', 'Annulée'),
    ], string="Statut", default='draft', tracking=True, required=True)

    source = fields.Selection([
        ('direct', 'Direct'),
        ('airbnb', 'Airbnb'),
        ('booking', 'Booking.com'),
        ('whatsapp', 'WhatsApp'),
        ('referral', 'Référence'),
        ('other', 'Autre'),
    ], string="Source", default='direct')

    notes = fields.Text(string="Notes")
    access_instructions = fields.Text(string="Instructions d'accès")
    welcome_message_sent = fields.Boolean(string="Message d'accueil envoyé")

    review_ids = fields.One2many(
        'civora.reservation.review', 'reservation_id', string="Avis")
    cleaning_task_ids = fields.One2many(
        'civora.cleaning.task', 'reservation_id', string="Ménages")
    has_review = fields.Boolean(
        compute='_compute_has_review', store=True)
    guest_rating = fields.Float(
        string="Note voyageur",
        compute='_compute_has_review', store=True)

    company_id = fields.Many2one(
        'res.company', string="Société",
        default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id')

    @api.depends('checkin_date', 'checkout_date')
    def _compute_num_nights(self):
        for rec in self:
            if rec.checkin_date and rec.checkout_date:
                delta = rec.checkout_date - rec.checkin_date
                rec.num_nights = max(delta.days, 0)
            else:
                rec.num_nights = 0

    @api.depends('tariff_night', 'num_nights')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = rec.tariff_night * rec.num_nights

    @api.depends('review_ids', 'review_ids.rating')
    def _compute_has_review(self):
        for rec in self:
            reviews = rec.review_ids
            rec.has_review = bool(reviews)
            if reviews:
                rec.guest_rating = sum(r.rating for r in reviews) / len(reviews)
            else:
                rec.guest_rating = 0.0

    @api.constrains('checkin_date', 'checkout_date')
    def _check_dates(self):
        for rec in self:
            if rec.checkin_date and rec.checkout_date and rec.checkout_date <= rec.checkin_date:
                raise ValidationError(
                    _("La date de départ doit être postérieure à la date d'arrivée."))

    @api.constrains('checkin_date', 'checkout_date', 'property_id')
    def _check_overlap(self):
        for rec in self:
            if not (rec.checkin_date and rec.checkout_date and rec.property_id):
                continue
            domain = [
                ('id', '!=', rec.id),
                ('property_id', '=', rec.property_id.id),
                ('state', 'not in', ['cancelled', 'draft']),
                ('checkin_date', '<', rec.checkout_date),
                ('checkout_date', '>', rec.checkin_date),
            ]
            if self.search_count(domain):
                raise ValidationError(
                    _("Ce bien est déjà réservé sur cette période."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'civora.reservation') or _('Nouveau')
        return super().create(vals_list)

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_checkin(self):
        self.write({'state': 'checkin'})
        for rec in self:
            if rec.property_id:
                rec.property_id.write({'status': 'saisonnier'})

    def action_checkout(self):
        self.write({'state': 'checkout'})
        for rec in self:
            if rec.property_id:
                rec.property_id.write({'status': 'disponible'})
            self.env['civora.cleaning.task'].create({
                'reservation_id': rec.id,
                'property_id': rec.property_id.id,
                'date': rec.checkout_date,
                'task_type': 'menage',
                'priority': 'haute',
                'state': 'a_planifier',
                'company_id': rec.company_id.id,
            })

    @api.model
    def _demo_assign_agents(self):
        """Repartit les sejours de demonstration sur les gestionnaires CIVORA.

        Meme raison que cote Ventes : sans cela tout est rattache a l'utilisateur
        qui a installe le module (OdooBot), et la ligne « Agent » de la fiche 360
        affiche un robot au lieu d'un membre de l'equipe.

        Tolerant : sans les comptes de l'equipe, la methode ne fait rien.
        """
        logins = [
            "mariam.bamba@civora.ci",
            "kofi.asante@civora.ci",
            "moussa.ouattara@civora.ci",
        ]
        agents = self.env["res.users"].sudo().search([("login", "in", logins)])
        if not agents:
            return False
        ordered = [a for login in logins for a in agents if a.login == login]
        for index, rec in enumerate(self.search([], order="id")):
            rec.agent_id = ordered[index % len(ordered)]
        return True

    def action_cancel(self):
        # Le statut du bien doit etre libere AVANT d'ecrire l'annulation :
        # sinon rec.state vaut deja 'cancelled' et le test ne passe jamais,
        # ce qui laissait un bien marque occupe apres l'annulation d'un sejour
        # en cours.
        for rec in self:
            if rec.property_id and rec.state == 'checkin':
                rec.property_id.write({'status': 'disponible'})
        self.write({'state': 'cancelled'})

    # ------------------------------------------------------------------
    # Caution
    # ------------------------------------------------------------------
    def action_deposit_collect(self):
        for rec in self:
            if not rec.deposit_amount:
                raise ValidationError(
                    _("Renseignez d'abord le montant de la caution."))
        self.write({'deposit_status': 'collected'})

    def action_deposit_return(self):
        for rec in self:
            if rec.deposit_status != 'collected':
                raise ValidationError(
                    _("La caution doit avoir ete encaissee avant d'etre restituee."))
        self.write({'deposit_status': 'returned'})

    def action_deposit_retain(self):
        for rec in self:
            if rec.deposit_status != 'collected':
                raise ValidationError(
                    _("La caution doit avoir ete encaissee avant d'etre retenue."))
        self.write({'deposit_status': 'retained'})

    @api.model
    def get_seasonal_kpis(self):
        today = fields.Date.today()
        first_of_month = today.replace(day=1)
        active = self.search_count([
            ('state', 'in', ['confirmed', 'checkin']),
        ])
        checkins_today = self.search_count([
            ('checkin_date', '=', today),
            ('state', '=', 'confirmed'),
        ])
        checkouts_today = self.search_count([
            ('checkout_date', '=', today),
            ('state', '=', 'checkin'),
        ])
        month_reservations = self.search([
            ('state', 'in', ['confirmed', 'checkin', 'checkout']),
            ('checkin_date', '>=', first_of_month),
            ('checkin_date', '<=', today),
        ])
        revenue_month = sum(month_reservations.mapped('total_amount'))
        all_reviews = self.env['civora.reservation.review'].search([])
        avg_rating = 0.0
        review_count = len(all_reviews)
        if review_count:
            avg_rating = round(sum(all_reviews.mapped('rating')) / review_count, 1)
        cleaning_pending = self.env['civora.cleaning.task'].search_count([
            ('state', 'in', ['a_planifier', 'planifie']),
        ])
        properties = self.env['civora.property'].search([('transaction', '=', 'saisonnier')])
        property_count = len(properties)
        occupation_rate = 86
        if property_count:
            from datetime import timedelta
            total_days = 0
            occupied_days = 0
            for prop in properties:
                total_days += 30
                reservations = self.search([
                    ('property_id', '=', prop.id),
                    ('state', 'in', ['confirmed', 'checkin', 'checkout']),
                    ('checkin_date', '>=', first_of_month),
                ])
                for r in reservations:
                    start = max(r.checkin_date, first_of_month)
                    end = min(r.checkout_date, today) if r.checkout_date <= today else today
                    if end > start:
                        occupied_days += (end - start).days
            if total_days > 0:
                occupation_rate = round(occupied_days / total_days * 100)
        # Tendances calculees par rapport au mois precedent (pas de valeur figee).
        from datetime import timedelta
        prev_end = first_of_month - timedelta(days=1)
        prev_start = prev_end.replace(day=1)
        prev_reservations = self.search([
            ('state', 'in', ['confirmed', 'checkin', 'checkout']),
            ('checkin_date', '>=', prev_start),
            ('checkin_date', '<=', prev_end),
        ])
        prev_revenue = sum(prev_reservations.mapped('total_amount'))
        revenue_trend = round(
            (revenue_month - prev_revenue) * 100.0 / prev_revenue) if prev_revenue else 0
        week_start = today - timedelta(days=7)
        new_this_week = self.search_count([('create_date', '>=', week_start)])
        prev_days = max((prev_end - prev_start).days + 1, 1)
        prev_occupied = 0
        for prop in properties:
            for r in prev_reservations.filtered(lambda x: x.property_id == prop):
                start = max(r.checkin_date, prev_start)
                end = min(r.checkout_date, prev_end)
                if end > start:
                    prev_occupied += (end - start).days
        prev_rate = round(
            prev_occupied * 100.0 / (prev_days * property_count)) if property_count else 0
        return {
            'active': active,
            'active_reservations': active,
            'checkins_today': checkins_today,
            'checkouts_today': checkouts_today,
            'revenue_month': revenue_month,
            'month_revenue': revenue_month,
            'revenue_trend': revenue_trend,
            'new_this_week': new_this_week,
            'occupation_trend': occupation_rate - prev_rate,
            'avg_rating': avg_rating,
            'review_count': review_count,
            'cleaning_pending': cleaning_pending,
            'property_count': property_count,
            'occupation_rate': occupation_rate,
        }

    @api.model
    def get_checkins_today(self):
        today = fields.Date.today()
        reservations = self.search([
            ('checkin_date', '=', today),
            ('state', '=', 'confirmed'),
        ])
        result = []
        for r in reservations:
            # Le code d'acces est genere de facon stable a partir de la
            # reference : pas de valeur aleatoire qui changerait a chaque
            # rechargement de l'ecran.
            digits = "".join(c for c in (r.name or "") if c.isdigit()) or str(r.id)
            code = (digits + "0000")[-4:]
            result.append({
                'id': r.id,
                'guest_name': r.guest_id.name or '',
                'property_name': r.property_id.name or '',
                'num_nights': r.num_nights,
                'access_code': code,
                'checkin_time': '14:00',
            })
        return result

    @api.model
    def get_checkouts_and_cleaning(self):
        today = fields.Date.today()
        from datetime import timedelta
        end_date = today + timedelta(days=7)
        tasks = self.env['civora.cleaning.task'].search([
            ('date', '>=', today),
            ('date', '<=', end_date),
        ], order='date asc', limit=10)
        result = []
        for t in tasks:
            Task = self.env['civora.cleaning.task']
            slot = dict(Task._fields['time_slot'].selection).get(t.time_slot, '')
            result.append({
                'id': t.id,
                'property_name': t.property_id.name if t.property_id else '',
                'date': str(t.date) if t.date else '',
                'date_label': '%s · %s' % (self._relative_day(t.date), slot),
                'time_slot': t.time_slot or '',
                'assigned_to': (t.staff_id.name if t.staff_id else
                                (t.assigned_to.name if t.assigned_to else '')),
                'state': t.state,
                'state_label': dict(Task._fields['state'].selection).get(t.state, ''),
            })
        return result

    @api.model
    def get_recent_reviews(self):
        reviews = self.env['civora.reservation.review'].search(
            [], order='create_date desc', limit=5
        )
        result = []
        for rev in reviews:
            result.append({
                'id': rev.id,
                'guest_name': rev.reservation_id.guest_id.name if rev.reservation_id and rev.reservation_id.guest_id else '',
                'property_name': rev.reservation_id.property_id.name if rev.reservation_id and rev.reservation_id.property_id else '',
                'rating': rev.rating,
                'comment': rev.comment or '',
            })
        return result


class CivoraReservationDashboard(models.Model):
    """API d'ecran du module Saisonnier.

    Un seul aller-retour RPC alimente les 15 onglets. Tout provient de la
    base : aucun chiffre n'est ecrit en dur dans le front.
    """

    _inherit = "civora.reservation"

    # ------------------------------------------------------------------
    @api.model
    def _seasonal_properties(self):
        Property = self.env["civora.property"]
        props = Property.search([("transaction", "=", "saisonnier")])
        if not props:
            props = Property.search([], limit=8)
        return props

    @api.model
    def _month_label(self, date):
        months = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet",
                  "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        return "%s %s" % (months[date.month - 1], date.year)

    @api.model
    def _ago(self, dt):
        """« il y a 8 min » — helper local, sans dependance a un autre module."""
        if not dt:
            return ""
        delta = fields.Datetime.now() - dt
        minutes = int(delta.total_seconds() // 60)
        if minutes < 1:
            return "à l'instant"
        if minutes < 60:
            return "il y a %s min" % minutes
        hours = minutes // 60
        if hours < 24:
            return "il y a %s h" % hours
        days = hours // 24
        if days == 1:
            return "hier"
        if days < 30:
            return "il y a %s jours" % days
        return fields.Datetime.to_string(dt)[:10]

    @api.model
    def _relative_day(self, date):
        if not date:
            return ""
        from datetime import timedelta
        today = fields.Date.today()
        delta = (date - today).days
        if delta == 0:
            return "Aujourd'hui"
        if delta == 1:
            return "Demain"
        if delta == -1:
            return "Hier"
        days = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
        if 0 < delta < 7:
            return days[date.weekday()].capitalize()
        return fields.Date.to_string(date)

    @api.model
    def get_seasonal_dashboard(self):
        from datetime import timedelta
        today = fields.Date.today()
        first = today.replace(day=1)
        next_month = (first + timedelta(days=32)).replace(day=1)
        last = next_month - timedelta(days=1)

        props = self._seasonal_properties()
        reservations = self.search([("state", "!=", "cancelled")])

        # ---- Planning : une ligne par bien, une case par jour du mois ----
        emojis = ["🌊", "🏙️", "🏖️", "✨", "🌴", "🏝️", "🌇", "🛎️"]
        planning = []
        for idx, prop in enumerate(props):
            bars = []
            for res in reservations.filtered(lambda r: r.property_id == prop):
                if not (res.checkin_date and res.checkout_date):
                    continue
                if res.checkout_date < first or res.checkin_date > last:
                    continue
                start = max(res.checkin_date, first)
                end = min(res.checkout_date, last)
                bars.append({
                    "id": res.id,
                    "guest": res.guest_id.name or "",
                    "source": res.source or "direct",
                    "source_label": dict(self._fields["source"].selection).get(res.source, ""),
                    "state": res.state,
                    "start_day": start.day,
                    "span": max((end - start).days, 1),
                    "nights": res.num_nights,
                    "total": res.total_amount,
                })
            planning.append({
                "id": prop.id,
                "emoji": emojis[idx % len(emojis)],
                "name": prop.name,
                "city": prop.city or "",
                "price": prop.default_tariff_night or 0,
                "bars": sorted(bars, key=lambda b: b["start_day"]),
            })

        # ---- Reservations ----
        rows = []
        for res in self.search([]):
            rows.append({
                "id": res.id,
                "ref": res.name or "",
                "property": res.property_id.name or "",
                "guest": res.guest_id.name or "",
                "checkin": fields.Date.to_string(res.checkin_date) if res.checkin_date else "",
                "checkout": fields.Date.to_string(res.checkout_date) if res.checkout_date else "",
                "nights": res.num_nights,
                "tariff": res.tariff_night,
                "total": res.total_amount,
                "source": res.source or "",
                "source_label": dict(self._fields["source"].selection).get(res.source, ""),
                "state": res.state,
                "state_label": dict(self._fields["state"].selection).get(res.state, ""),
            })

        # ---- Inbox ----
        threads = self.env["civora.seasonal.thread"].search([])
        thread_rows = []
        for th in threads:
            thread_rows.append({
                "id": th.id,
                "guest": th.guest_id.name or "",
                "guest_id": th.guest_id.id,
                "property": th.property_id.name or "",
                "channel": th.channel,
                "channel_label": dict(th._fields["channel"].selection).get(th.channel, ""),
                "last_message": th.last_message or "",
                "unread": th.unread_count,
                "ago": self._ago(th.last_message_date),
                "guest_email": th.guest_id.email or "",
                "guest_phone": th.guest_id.phone or "",
                "guest_stays": th.guest_id.stay_count,
                "guest_rating": th.guest_id.rating,
                "reservation": {
                    "dates": (
                        "%s → %s" % (
                            fields.Date.to_string(th.reservation_id.checkin_date),
                            fields.Date.to_string(th.reservation_id.checkout_date),
                        ) if th.reservation_id.checkin_date else ""),
                    "nights": th.reservation_id.num_nights,
                    "total": th.reservation_id.total_amount,
                } if th.reservation_id else {},
                "messages": [{
                    "id": m.id,
                    "body": m.body,
                    "direction": m.direction,
                    "is_ai": m.is_ai,
                    "time": fields.Datetime.to_string(m.message_date)[11:16],
                } for m in th.message_ids.sorted(lambda m: (m.message_date, m.id))],
            })

        # ---- Voyageurs ----
        guests = self.env["civora.seasonal.guest"].search([])
        guest_rows = [g.to_dict() for g in guests]
        recurring = len([g for g in guests if g.stay_count > 1])
        avg_rating = round(sum(guests.mapped("rating")) / len(guests), 1) if guests else 0
        ltv = int(sum(guests.mapped("total_spent")) / len(guests)) if guests else 0

        # ---- Channels ----
        channels = self.env["civora.seasonal.channel"].search([])
        channel_rows = [{
            "id": c.id,
            "name": c.name,
            "emoji": c.emoji or "🌐",
            "connected": c.connected,
            "listings": c.listing_count,
            "commission": c.commission_rate,
            "sync": c.last_sync_label or "—",
        } for c in channels]

        # ---- Tarification ----
        pricing = []
        for idx, prop in enumerate(props):
            base = prop.default_tariff_night or 0
            pricing.append({
                "id": prop.id,
                "emoji": emojis[idx % len(emojis)],
                "name": prop.name,
                "base": base,
                "week": base,
                "weekend": int(round(base * 1.22)),
                "high": int(round(base * 1.40)),
                "event": int(round(base * 1.65)),
            })

        # ---- Upsells ----
        upsells = self.env["civora.seasonal.upsell"].search([])
        upsell_rows = [{
            "id": u.id,
            "name": u.name,
            "price": u.price,
            "unit": u.price_unit or "",
            "margin": u.margin_pct,
            "sales": u.sales_count,
            "revenue": u.revenue,
            "active": u.is_active,
        } for u in upsells]
        upsell_revenue = sum(u.revenue for u in upsells if u.is_active)
        upsell_basket = int(
            upsell_revenue / sum(u.sales_count for u in upsells if u.is_active)
        ) if any(u.sales_count for u in upsells if u.is_active) else 0
        active_upsells = upsells.filtered("is_active")
        stays = reservations.filtered(
            lambda r: r.state in ("confirmed", "checkin", "checkout"))
        stays_done = len(stays)
        # Attach rate = part des sejours ayant declenche au moins un service.
        lines = self.env["civora.seasonal.upsell.line"].search(
            [("reservation_id", "in", stays.ids)])
        attach_rate = round(
            len(set(lines.mapped("reservation_id").ids)) * 100.0 / stays_done
        ) if stays_done else 0
        upsell_margin = int(round(
            sum(u.revenue * u.margin_pct for u in active_upsells)
            / (upsell_revenue or 1)
        )) if active_upsells else 0

        # ---- Incidents & cautions ----
        incidents = self.env["civora.seasonal.incident"].search([])
        incident_rows = [{
            "id": i.id,
            "ref": i.name,
            "property": i.property_id.name or "",
            "guest": i.guest_id.name or "",
            "date": fields.Date.to_string(i.incident_date),
            "type": dict(i._fields["incident_type"].selection).get(i.incident_type, ""),
            "description": i.description or "",
            "amount": i.amount,
            "severity": i.severity,
            "severity_label": dict(i._fields["severity"].selection).get(i.severity, ""),
            "state": i.state,
            "state_label": dict(i._fields["state"].selection).get(i.state, ""),
        } for i in incidents]

        deposits = []
        total_deposit = 0
        for prop in props:
            active = reservations.filtered(
                lambda r: r.property_id == prop and r.state in ("confirmed", "checkin"))
            amount = sum(active.mapped("deposit_amount"))
            total_deposit += amount
            nights = sum(active.mapped("num_nights"))
            deposits.append({
                "property": prop.name,
                "stays": len(active),
                "avg_nights": round(nights / len(active), 1) if active else 0,
                "amount": amount,
            })
        insurance = self.env["civora.seasonal.insurance"].search([], limit=1)

        # ---- Paiements & revenus ----
        payouts = self.env["civora.seasonal.payout"].search([])
        payout_rows = [{
            "id": p.id,
            "date": fields.Date.to_string(p.payout_date),
            "channel": p.channel_id.name or "",
            "reference": p.reference,
            "gross": p.gross_amount,
            "commission": p.commission_amount,
            "net": p.net_amount,
            "state": p.state,
            "state_label": dict(p._fields["state"].selection).get(p.state, ""),
        } for p in payouts]
        statements = self.env["civora.seasonal.owner.statement"].search([])
        statement_rows = [{
            "id": s.id,
            "name": s.name,
            "gross": s.gross_amount,
            "commission": s.channel_commission,
            "fee": s.management_fee,
            "net": s.net_amount,
            "sent": s.sent,
        } for s in statements]
        # Les releves proprietaires couvrent l'integralite du chiffre du mois ;
        # les virements channels n'en couvrent que la part deja versee. Les KPI
        # de revenus se calculent donc sur les releves, pour rester coherents
        # entre eux (brut - commissions - honoraires = net a reverser).
        gross_total = sum(statements.mapped("gross_amount"))
        commission_total = sum(statements.mapped("channel_commission"))
        owner_total = sum(statements.mapped("net_amount"))

        # ---- Regles & frais ----
        rule = self.env["civora.seasonal.rule"].search([], limit=1)
        rule_data = {}
        if rule:
            rule_data = {
                "min_nights": rule.min_nights,
                "max_nights": rule.max_nights,
                "notice": rule.notice_label,
                "free_cancel": "%s h avant arrivée" % rule.free_cancel_hours,
                "checkin": "%s – %s" % (rule.checkin_from, rule.checkin_to),
                "checkout": "Avant %s" % rule.checkout_before,
                "children": "Oui" if rule.children_allowed else "Non",
                "pets": dict(rule._fields["pets_policy"].selection).get(rule.pets_policy, ""),
                "parties": "Autorisés" if rule.parties_allowed else "Interdits",
                "registration": rule.registration_number or "—",
                "declaration": rule.declaration_status or "",
                "insurance": rule.insurance_status or "",
                "fees": [{
                    "id": f.id, "name": f.name, "amount": f.amount_label, "auto": f.is_auto,
                } for f in rule.fee_ids],
                "messages": [{
                    "id": m.id, "name": m.name, "active": m.is_active,
                } for m in rule.auto_message_ids],
            }

        # ---- Marche & rate shopper ----
        competitors = self.env["civora.seasonal.competitor"].search([])
        comp_rows = [{
            "id": c.id, "name": c.name, "distance": c.distance_km, "rating": c.rating,
            "occupancy": c.occupancy, "price": c.price_night, "trend": c.trend_7d,
            "is_self": c.is_self,
        } for c in competitors]
        pace = [{"id": p.id, "name": p.name, "percent": p.percent}
                for p in self.env["civora.seasonal.demand.pace"].search([])]
        events = [{"id": e.id, "name": e.name, "period": e.period_label,
                   "impact": e.impact_label, "hot": e.is_hot}
                  for e in self.env["civora.seasonal.event"].search([])]

        # ---- Booking engine ----
        funnel_recs = self.env["civora.seasonal.funnel.step"].search([])
        funnel = []
        base_visitors = funnel_recs[0].visitors if funnel_recs else 0
        previous = None
        for step in funnel_recs:
            funnel.append({
                "id": step.id,
                "name": step.name,
                "visitors": step.visitors,
                "pct": round(step.visitors * 100.0 / base_visitors, 1) if base_visitors else 0,
                "drop": round(step.visitors * 100.0 / previous, 1) if previous else None,
            })
            previous = step.visitors
        entries = [{
            "id": e.id, "name": e.name, "sessions": e.sessions, "conversion": e.conversion,
            "type": dict(e._fields["entry_type"].selection).get(e.entry_type, ""),
        } for e in self.env["civora.seasonal.booking.entry"].search([])]
        booking_cfg = self.env["civora.seasonal.booking.config"].search([], limit=1)

        # ---- Guest journey ----
        journey = [{
            "id": s.id,
            "name": s.name,
            "offset": s.offset_label,
            "actions": [{
                "id": a.id,
                "channel": a.channel,
                "channel_label": dict(a._fields["channel"].selection).get(a.channel, ""),
                "name": a.name,
                "is_ai": a.is_ai,
            } for a in s.action_ids],
        } for s in self.env["civora.seasonal.journey.step"].search([])]

        # ---- Menage & maintenance ----
        Task = self.env["civora.cleaning.task"]
        tasks = Task.search([], order="date, id")
        slots = dict(Task._fields["time_slot"].selection)
        task_rows = [{
            "id": t.id,
            "property": t.property_id.name or "",
            "type": dict(Task._fields["task_type"].selection).get(t.task_type, "Ménage"),
            "date": fields.Date.to_string(t.date) if t.date else "",
            "date_label": self._relative_day(t.date),
            "slot": slots.get(t.time_slot, ""),
            "priority": t.priority,
            "assignee": (t.staff_id.name or (t.assigned_to.name if t.assigned_to else "")
                         or "À assigner"),
            "state": t.state,
            "state_label": dict(Task._fields["state"].selection).get(t.state, ""),
        } for t in tasks]
        staff = self.env["civora.cleaning.staff"].search([])
        staff_rows = [{
            "id": s.id, "name": s.name, "speciality": s.speciality or "",
            "tasks": s.task_count, "rating": s.rating,
        } for s in staff]
        inventory = [{
            "id": i.id, "name": i.name, "quantity": i.quantity, "low": i.is_low,
        } for i in self.env["civora.seasonal.inventory"].search([])]

        return {
            "month_label": self._month_label(today),
            "days_in_month": last.day,
            "today_day": today.day,
            "planning": planning,
            "reservations": rows,
            "threads": thread_rows,
            "reply_templates": [{
                "id": r.id, "name": r.name, "body": r.body,
            } for r in self.env["civora.seasonal.reply.template"].search([])],
            "guests": guest_rows,
            "guest_kpis": {
                "unique": len(guests),
                "recurring": recurring,
                "recurring_pct": round(recurring * 100.0 / len(guests)) if guests else 0,
                "rating": avg_rating,
                "ltv": ltv,
            },
            "channels": channel_rows,
            "sync_states": [{"id": s.id, "name": s.name, "percent": s.percent}
                            for s in self.env["civora.seasonal.sync.state"].search([])],
            "conflicts": [{"id": c.id, "name": c.name, "description": c.description or ""}
                          for c in self.env["civora.seasonal.conflict"].search(
                              [("resolved", "=", False)])],
            "pricing": pricing,
            "upsells": upsell_rows,
            "upsell_kpis": {
                "revenue": upsell_revenue,
                # Part des sejours ayant declenche au moins un service
                # additionnel : ventes d'upsell rapportees au nombre de
                # sejours honores (borne a 100 %).
                "attach_rate": attach_rate,
                "basket": upsell_basket,
                "margin": upsell_margin,
            },
            "incidents": incident_rows,
            "deposits": deposits,
            "deposit_total": total_deposit,
            "insurance": {
                "coverage": insurance.coverage, "franchise": insurance.franchise,
            } if insurance else {},
            "payouts": payout_rows,
            "statements": statement_rows,
            "revenue_kpis": {
                "gross": gross_total,
                "commission": commission_total,
                "commission_pct": round(commission_total * 100.0 / gross_total, 1)
                if gross_total else 0,
                "net": gross_total - commission_total,
                "owner": owner_total,
                "owner_pct": round(owner_total * 100.0 / gross_total, 1) if gross_total else 0,
            },
            "rules": rule_data,
            "competitors": comp_rows,
            "pace": pace,
            "events": events,
            "funnel": funnel,
            "booking_entries": entries,
            "booking_config": {
                "domain": booking_cfg.domain,
                "payment": booking_cfg.payment_methods,
                "languages": booking_cfg.languages,
                "snippet": booking_cfg.embed_snippet or "",
            } if booking_cfg else {},
            "journey": journey,
            "cleaning": task_rows,
            "staff": staff_rows,
            "inventory": inventory,
        }
