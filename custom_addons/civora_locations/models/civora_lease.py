# -*- coding: utf-8 -*-
from datetime import timedelta

from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import ValidationError

CIVORA_LEASE_TYPE = [
    ('residentiel', "Résidentiel"),
    ('commercial', "Commercial"),
]
CIVORA_LEASE_STATE = [
    ('draft', "Brouillon"),
    ('active', "Actif"),
    ('ended', "Résilié"),
]
CIVORA_LEASE_STATUS = [
    ('actif', "Actif"),
    ('retard', "Retard"),
    ('expire_bientot', "Expire bientôt"),
    ('resilie', "Résilié"),
]

# Seuil en-dessous duquel un bail est considere "en retard" (taux d'encaissement).
CIVORA_LEASE_ARREARS_THRESHOLD = 95.0
# Fenetre (en jours) avant echeance a partir de laquelle un bail est "a renouveler".
CIVORA_LEASE_RENEWAL_WINDOW_DAYS = 60


class CivoraLease(models.Model):
    """Bail : contrat de location reliant un locataire a un bien CIVORA.

    Remplace a terme le simple champ civora.property.tenant_id par une
    relation contractuelle complete (periode, loyer, depot, encaissements).
    """
    _name = 'civora.lease'
    _description = "Bail CIVORA"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'
    _rec_name = 'name'
    _check_company_auto = True

    name = fields.Char(string="N° de bail", copy=False, index=True, tracking=True,
                       default=lambda self: self._default_name())
    property_id = fields.Many2one(
        'civora.property',
        string="Bien",
        required=True,
        index=True,
        tracking=True,
        check_company=True,
        help="Bien loue par ce contrat.",
    )
    tenant_id = fields.Many2one(
        'res.partner',
        string="Locataire",
        required=True,
        index=True,
        tracking=True,
        domain=[('civora_is_contact', '=', True)],
    )
    owner_id = fields.Many2one(
        'res.partner',
        string="Propriétaire",
        related='property_id.owner_id',
        store=True,
        readonly=True,
    )
    agent_id = fields.Many2one(
        'res.users',
        string="Agent responsable",
        index=True,
        tracking=True,
        default=lambda self: self.env.user,
        help="Agent CIVORA en charge du suivi de ce bail.",
    )
    property_city = fields.Char(
        string="Ville du bien",
        related='property_id.city',
        store=True,
        readonly=True,
        help="Ville du bien loué, déduite automatiquement.",
    )
    opportunity_id = fields.Many2one(
        'civora.opportunity',
        string="Opportunité source",
        index=True,
        ondelete='set null',
        tracking=True,
        help="Opportunité Pipeline qui a donné naissance à ce bail.",
    )
    reminder_ids = fields.One2many(
        'civora.lease.reminder', 'lease_id', string="Relances",
    )
    reminder_count = fields.Integer(
        string="Nb relances", compute='_compute_reminder_count',
    )
    lease_type = fields.Selection(
        CIVORA_LEASE_TYPE, string="Type de bail", default='residentiel', required=True,
    )
    state = fields.Selection(
        CIVORA_LEASE_STATE, string="Cycle de vie", default='active', required=True, tracking=True,
        help="Cycle de vie administratif du bail (independant du statut calcule).",
    )
    status = fields.Selection(
        CIVORA_LEASE_STATUS, string="Statut", compute='_compute_status', store=True,
        help="Statut affiche : deduit du cycle de vie, de l'echeance et du taux d'encaissement.",
    )

    currency_id = fields.Many2one(
        'res.currency', string="Devise", required=True,
        default=lambda self: self.env.company.currency_id,
    )
    rent = fields.Monetary(string="Loyer", currency_field='currency_id', required=True)
    charges = fields.Monetary(string="Charges", currency_field='currency_id')
    deposit = fields.Monetary(
        string="Dépôt de garantie", currency_field='currency_id',
        compute='_compute_deposit', store=True, readonly=False,
        help="Calculé par défaut comme caution_months × loyer. "
             "Peut être surchargé manuellement si le bail impose une valeur différente.",
    )
    total_monthly = fields.Monetary(
        string="Total mensuel", currency_field='currency_id',
        compute='_compute_total_monthly', store=True,
    )

    # ── Versements initiaux à la signature ─────────────────────────────
    advance_months = fields.Integer(
        string="Mois d'avance", default=0,
        help="Nombre de mois de loyer payés d'avance par le locataire à la signature. "
             "Couvre automatiquement les premiers mois du bail.",
    )
    caution_months = fields.Integer(
        string="Mois de caution", default=1,
        help="Nombre de mois de caution. Le montant total = caution_months × loyer. "
             "La caution reste intouchable pendant tout le bail et est restituée en fin "
             "de contrat sauf retenues justifiées (dégradations).",
    )
    agency_months = fields.Integer(
        string="Mois d'agence", default=1,
        help="Nombre de mois de frais d'agence facturés au locataire à la signature. "
             "Montant = agency_months × loyer.",
    )
    advance_amount = fields.Monetary(
        string="Montant d'avance",
        currency_field='currency_id',
        compute='_compute_initial_amounts', store=True,
    )
    caution_amount = fields.Monetary(
        string="Montant caution",
        currency_field='currency_id',
        compute='_compute_initial_amounts', store=True,
    )
    agency_amount = fields.Monetary(
        string="Frais d'agence",
        currency_field='currency_id',
        compute='_compute_initial_amounts', store=True,
    )
    initial_payment_total = fields.Monetary(
        string="Total à verser à la signature",
        currency_field='currency_id',
        compute='_compute_initial_amounts', store=True,
        help="Somme totale que le locataire doit verser à la signature : "
             "loyer d'avance + caution + frais d'agence.",
    )
    first_due_month = fields.Date(
        string="Premier mois effectivement dû",
        compute='_compute_first_due_month', store=True,
        help="Premier mois pour lequel le locataire devra effectivement payer un loyer, "
             "après consommation des mois d'avance.",
    )

    date_start = fields.Date(string="Date d'entrée", required=True, default=fields.Date.context_today)
    date_end = fields.Date(string="Date de fin")
    payday = fields.Integer(string="Jour de paiement", default=1)
    notice_tenant = fields.Char(string="Préavis locataire", default="3 mois")
    notice_owner = fields.Char(string="Préavis bailleur", default="6 mois")
    indexation = fields.Char(string="Indexation", default="Annuelle · IRL")
    note = fields.Text(string="Notes internes")

    payment_ids = fields.One2many('civora.lease.payment', 'lease_id', string="Paiements")
    installment_ids = fields.One2many(
        'civora.lease.installment', 'lease_id', string="Échéances",
    )
    installment_count = fields.Integer(
        string="Nb échéances", compute='_compute_installment_stats', store=True,
    )
    installment_overdue_count = fields.Integer(
        string="Échéances en retard", compute='_compute_installment_stats', store=True,
    )
    payment_count = fields.Integer(string="Nb paiements", compute='_compute_payment_stats', store=True)
    total_paid = fields.Monetary(
        string="Total encaissé", currency_field='currency_id',
        compute='_compute_payment_stats', store=True,
    )
    total_expected = fields.Monetary(
        string="Total attendu", currency_field='currency_id',
        compute='_compute_payment_stats', store=True,
    )
    payment_rate = fields.Float(
        string="Taux d'encaissement (%)", compute='_compute_payment_stats', store=True,
    )
    arrears_amount = fields.Monetary(
        string="Impayés", currency_field='currency_id',
        compute='_compute_payment_stats', store=True,
    )

    company_id = fields.Many2one(
        'res.company', string="Société", required=True, index=True,
        default=lambda self: self.env.company,
        help="Societe rattachee au bien (isolation multi-societe).",
    )

    @api.model
    def _default_name(self):
        seq = self.env['ir.sequence'].next_by_code('civora.lease')
        return seq or "/"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == "/":
                vals['name'] = self._default_name()
        leases = super().create(vals_list)
        # A la creation d'un bail actif, on marque le bien comme loue et on
        # synchronise le locataire courant (compatibilite avec les ecrans
        # existants qui lisent property.tenant_id).
        for lease in leases:
            if lease.state == 'active' and lease.property_id:
                update = {'status': 'loue'}
                if lease.tenant_id:
                    update['tenant_id'] = lease.tenant_id.id
                lease.property_id.write(update)
        return leases

    def write(self, vals):
        res = super().write(vals)
        # Si le bail passe en 'ended', on libere le bien (retour dispo).
        if vals.get('state') == 'ended':
            for lease in self:
                if lease.property_id and lease.property_id.status == 'loue':
                    lease.property_id.write({'status': 'disponible', 'tenant_id': False})
        # Sync locataire courant sur le bien tant que le bail est actif.
        if 'tenant_id' in vals:
            for lease in self:
                if lease.state == 'active' and lease.property_id:
                    lease.property_id.tenant_id = lease.tenant_id.id or False
        return res

    @api.depends('rent', 'charges')
    def _compute_total_monthly(self):
        for lease in self:
            lease.total_monthly = (lease.rent or 0.0) + (lease.charges or 0.0)

    # ── Computed : montants initiaux ────────────────────────────────────
    @api.depends('rent', 'charges', 'advance_months', 'caution_months', 'agency_months')
    def _compute_initial_amounts(self):
        for lease in self:
            monthly = (lease.rent or 0.0) + (lease.charges or 0.0)
            rent_only = lease.rent or 0.0
            lease.advance_amount = (lease.advance_months or 0) * monthly
            lease.caution_amount = (lease.caution_months or 0) * rent_only
            lease.agency_amount = (lease.agency_months or 0) * rent_only
            lease.initial_payment_total = (
                lease.advance_amount + lease.caution_amount + lease.agency_amount
            )

    @api.depends('rent', 'caution_months')
    def _compute_deposit(self):
        """Le dépôt de garantie = caution_months × loyer par défaut,
        mais reste modifiable manuellement (readonly=False)."""
        for lease in self:
            # Ne recalcule que si le champ n'est pas encore rempli à la main
            # ou si les entrées changent volontairement
            lease.deposit = (lease.caution_months or 0) * (lease.rent or 0.0)

    @api.depends('date_start', 'advance_months')
    def _compute_first_due_month(self):
        """Le 1er mois effectivement dû par le locataire =
        date_start + advance_months mois."""
        from dateutil.relativedelta import relativedelta
        for lease in self:
            if not lease.date_start:
                lease.first_due_month = False
                continue
            lease.first_due_month = lease.date_start + relativedelta(
                months=(lease.advance_months or 0)
            )

    @api.depends('installment_ids.state')
    def _compute_installment_stats(self):
        for lease in self:
            lease.installment_count = len(lease.installment_ids)
            lease.installment_overdue_count = len(
                lease.installment_ids.filtered(lambda i: i.state == 'overdue')
            )

    @api.depends('payment_ids.amount', 'payment_ids.status', 'date_start', 'rent', 'charges')
    def _compute_payment_stats(self):
        today = fields.Date.context_today(self)
        for lease in self:
            payments = lease.payment_ids
            lease.payment_count = len(payments)
            lease.total_paid = sum(
                p.amount for p in payments if p.status in ('paid', 'partial')
            )
            months_elapsed = 1
            if lease.date_start and lease.date_start <= today:
                start = lease.date_start
                months_elapsed = max(
                    1, (today.year - start.year) * 12 + (today.month - start.month) + 1
                )
            lease.total_expected = months_elapsed * ((lease.rent or 0.0) + (lease.charges or 0.0))
            lease.payment_rate = (
                min(100.0, round((lease.total_paid / lease.total_expected) * 100, 1))
                if lease.total_expected else 100.0
            )
            lease.arrears_amount = max(0.0, lease.total_expected - lease.total_paid)

    @api.depends('state', 'date_end', 'payment_rate')
    def _compute_status(self):
        today = fields.Date.context_today(self)
        soon = today + timedelta(days=CIVORA_LEASE_RENEWAL_WINDOW_DAYS)
        for lease in self:
            if lease.state == 'ended':
                lease.status = 'resilie'
            elif lease.date_end and lease.date_end <= soon:
                lease.status = 'expire_bientot'
            elif lease.payment_rate < CIVORA_LEASE_ARREARS_THRESHOLD:
                lease.status = 'retard'
            else:
                lease.status = 'actif'

    def action_terminate(self):
        for lease in self:
            lease.state = 'ended'

    def action_reactivate(self):
        for lease in self:
            lease.state = 'active'

    # ═══════════════════════════════════════════════════════════════════
    # Génération de l'échéancier
    # ═══════════════════════════════════════════════════════════════════
    def generate_installments(self, force=False):
        """Génère l'échéancier mensuel du bail.

        - Si `force=False` (défaut) : ne fait rien si l'échéancier existe déjà.
        - Si `force=True` : supprime l'existant et régénère complètement.

        Génère un nombre de mois cohérent :
        - Bail à durée déterminée : de date_start à date_end inclus
        - Bail à durée indéterminée : 12 mois glissants (peut être étendu)
        """
        from dateutil.relativedelta import relativedelta
        Installment = self.env['civora.lease.installment']
        for lease in self:
            if not lease.date_start:
                continue
            existing = lease.installment_ids
            if existing and not force:
                continue
            if existing and force:
                existing.unlink()
            # Nombre de mois à générer
            if lease.date_end:
                nb_months = Installment._months_between(lease.date_start, lease.date_end)
            else:
                nb_months = 12  # glissant pour bail indéterminé
            if nb_months <= 0:
                nb_months = 1
            monthly_due = (lease.rent or 0.0) + (lease.charges or 0.0)
            payday = max(1, min(lease.payday or 1, 28))
            to_create = []
            current = lease.date_start
            for i in range(nb_months):
                # Date d'échéance : jour de paiement du mois courant
                try:
                    due = current.replace(day=payday)
                except ValueError:
                    due = current.replace(day=28)
                to_create.append({
                    'lease_id': lease.id,
                    'sequence': i,
                    'period_month': current.month,
                    'period_year': current.year,
                    'due_date': due,
                    'amount_due': monthly_due,
                })
                current = current + relativedelta(months=1)
            if to_create:
                Installment.create(to_create)
        return True

    def action_regenerate_installments(self):
        """Wrapper public pour régénérer l'échéancier depuis l'interface."""
        self.ensure_one()
        self.generate_installments(force=True)
        return True

    def get_installments_data(self, mode='compact'):
        """Retourne les données de l'échéancier pour affichage OWL.

        mode :
        - 'compact' : mois en cours + mois suivant (2 échéances)
        - 'all'     : toutes les échéances
        - 'upcoming': 6 prochaines + tous les impayés passés
        """
        self.ensure_one()
        today = fields.Date.context_today(self)
        all_installments = self.installment_ids.sorted('sequence')
        if mode == 'compact':
            # Chercher le mois "en cours" = premier non payé et non couvert par avance
            current = all_installments.filtered(
                lambda i: i.state in ('pending', 'partial', 'overdue')
            )
            if current:
                first_idx = list(all_installments).index(current[0])
                selected = all_installments[first_idx:first_idx + 2]
            else:
                # Tous payés : montrer les 2 prochains
                upcoming = all_installments.filtered(
                    lambda i: i.due_date and i.due_date >= today
                )
                selected = upcoming[:2] if upcoming else all_installments[-2:]
        elif mode == 'upcoming':
            overdue = all_installments.filtered(lambda i: i.state == 'overdue')
            upcoming = all_installments.filtered(
                lambda i: i.due_date and i.due_date >= today and i.state != 'covered_by_advance'
            )[:6]
            selected = overdue | upcoming
        else:  # 'all'
            selected = all_installments
        return [
            {
                'id': i.id,
                'sequence': i.sequence,
                'period_label': i.period_label,
                'period_month': i.period_month,
                'period_year': i.period_year,
                'due_date': str(i.due_date) if i.due_date else False,
                'amount_due': i.amount_due,
                'amount_paid': i.amount_paid,
                'amount_remaining': i.amount_remaining,
                'state': i.state,
                'payment_count': len(i.payment_ids),
                'is_overdue_days': (
                    (today - i.due_date).days
                    if (i.due_date and i.due_date < today and i.state in ('overdue', 'partial'))
                    else 0
                ),
            }
            for i in selected
        ]

    def get_financial_kpis(self):
        """KPI financiers consolidés du bail pour la vue d'ensemble.

        Retourne un dict avec :
        - total_encaisse : somme des paiements encaissés
        - total_du : somme des montants dus depuis le début du bail
        - reste_du : total_du - total_encaisse (jamais négatif)
        - next_installment : dict avec period_label, due_date, amount_remaining
                            (ou None si tout est payé)
        - overdue_count : nombre d'échéances en retard
        - overdue_amount : montant total en retard
        - initial_payment_expected : total attendu à la signature
        - initial_payment_received : total effectivement reçu à la signature
                                    (paiements de type advance/caution/agency)
        """
        self.ensure_one()
        today = fields.Date.context_today(self)
        # Encaissements globaux
        paid_payments = self.payment_ids.filtered(
            lambda p: p.status in ('paid', 'partial')
        )
        total_encaisse = sum(p.amount for p in paid_payments)
        # Échéances : total dû à date + reste à payer
        installments = self.installment_ids.sorted('sequence')
        total_du_a_date = sum(
            i.amount_due for i in installments
            if i.due_date and i.due_date <= today
            and i.state != 'covered_by_advance'
        )
        overdue_installments = installments.filtered(lambda i: i.state == 'overdue')
        overdue_amount = sum(i.amount_remaining for i in overdue_installments)
        # Prochaine échéance dûe
        next_inst = installments.filtered(
            lambda i: i.state in ('pending', 'partial', 'overdue')
        )
        next_data = None
        if next_inst:
            n = next_inst[0]
            next_data = {
                'id': n.id,
                'period_label': n.period_label,
                'due_date': str(n.due_date) if n.due_date else False,
                'amount_remaining': n.amount_remaining,
                'is_overdue': n.state == 'overdue',
            }
        # Versements initiaux
        initial_received = sum(
            p.amount for p in paid_payments
            if p.payment_type in ('advance', 'caution', 'agency')
        )
        return {
            'currency': self.currency_id.name or 'FCFA',
            'total_encaisse': total_encaisse,
            'total_du_a_date': total_du_a_date,
            'reste_du_a_date': max(0.0, total_du_a_date - sum(
                p.amount for p in paid_payments if p.payment_type == 'rent'
            )),
            'next_installment': next_data,
            'overdue_count': len(overdue_installments),
            'overdue_amount': overdue_amount,
            'initial_payment_expected': self.initial_payment_total,
            'initial_payment_received': initial_received,
            'initial_payment_pending': max(
                0.0, self.initial_payment_total - initial_received
            ),
            'rent_monthly': self.rent + self.charges,
        }

    def get_payment_method_stats(self):
        """Statistiques par méthode de paiement pour ce bail.

        Retourne une liste triée par montant décroissant.
        """
        self.ensure_one()
        from collections import defaultdict
        agg_amount = defaultdict(float)
        agg_count = defaultdict(int)
        for p in self.payment_ids.filtered(lambda x: x.status in ('paid', 'partial')):
            method = p.method or 'autre'
            agg_amount[method] += p.amount
            agg_count[method] += 1
        method_labels = dict(
            self.env['civora.lease.payment']._fields['method'].selection
        )
        total = sum(agg_amount.values()) or 1.0
        result = []
        for method, amount in sorted(agg_amount.items(), key=lambda x: -x[1]):
            result.append({
                'method': method,
                'method_label': method_labels.get(method, method),
                'amount': amount,
                'count': agg_count[method],
                'percent': round(100.0 * amount / total, 1),
            })
        return result

    def _civora_tracking_html(self, msg):
        """Rend lisibles les messages qui n'ont QUE des valeurs de suivi.

        Un changement d'état de contrat produit un mail.message au corps
        vide : sans ce rendu, la timeline affichait une carte blanche.
        Les noms de champs varient selon les versions d'Odoo, d'où le
        sondage défensif des attributs.
        """
        tracks = getattr(msg, 'tracking_value_ids', False)
        if not tracks:
            return ""

        def _label(t):
            info = getattr(t, 'field_info', None)
            if isinstance(info, dict) and info.get('desc'):
                return info['desc']
            fld = getattr(t, 'field_id', False)
            if fld and getattr(fld, 'field_description', False):
                return fld.field_description
            return getattr(t, 'field_desc', '') or ""

        def _val(t, side):
            for suffix in ('char', 'text', 'integer', 'float',
                           'monetary', 'datetime', 'date'):
                v = getattr(t, '%s_value_%s' % (side, suffix), None)
                if v not in (None, False, ''):
                    return str(v)
            return "—"

        rows = []
        for t in tracks:
            label = _label(t)
            if not label:
                continue
            rows.append(Markup("<li><b>%s</b> : %s → <b>%s</b></li>")
                        % (label, _val(t, 'old'), _val(t, 'new')))
        if not rows:
            return ""
        return Markup("<ul style='margin:0;padding-left:18px;'>%s</ul>") % Markup("").join(rows)

    def get_timeline(self, category=None):
        """Timeline chronologique unifiée des événements du bail.

        Agrège les messages du chatter (mail.message) de :
        - Le bail lui-même (civora.lease)
        - Les contrats liés (civora.lease.contract)
        - La restitution de caution éventuelle (civora.deposit.refund)

        Complète avec les événements dérivés :
        - Paiements enregistrés (création)
        - Paiements annulés

        Args:
            category (str, optional) : filtre par catégorie
                ('contract', 'payment', 'refund', 'other')

        Retourne une liste triée par date descendante, chaque événement
        contenant : date, author, model, model_label, icon, variant,
        title, body, ref (nom lisible du record source).
        """
        self.ensure_one()

        # Récupérer les contrats et restitutions liés
        contracts = self.env['civora.lease.contract'].search([
            ('lease_id', '=', self.id),
        ])
        refunds = self.env['civora.deposit.refund'].search([
            ('lease_id', '=', self.id),
        ])

        # Construire la liste des (modèle, ids) pour la requête mail.message
        model_ids = [
            ('civora.lease', [self.id]),
            ('civora.lease.contract', contracts.ids),
            ('civora.deposit.refund', refunds.ids),
        ]

        MODEL_META = {
            'civora.lease':          {'label': "Bail",              'icon': 'file-text-o', 'variant': 'neutral'},
            'civora.lease.contract': {'label': "Contrat",           'icon': 'file-text',   'variant': 'info'},
            'civora.deposit.refund': {'label': "Restitution",       'icon': 'undo',        'variant': 'warning'},
            'civora.lease.payment':  {'label': "Paiement",          'icon': 'money',       'variant': 'success'},
        }

        events = []
        MailMessage = self.env['mail.message']

        # Récupérer les messages du chatter
        for model, ids in model_ids:
            if not ids:
                continue
            messages = MailMessage.search([
                ('model', '=', model),
                ('res_id', 'in', ids),
                ('message_type', 'in', ('comment', 'notification', 'email')),
            ], order='date desc')
            meta = MODEL_META.get(model, MODEL_META['civora.lease'])
            for msg in messages:
                # Un message sans corps ni valeur de suivi n'apporte rien :
                # il produisait une carte vide dans la timeline.
                body = msg.body or ""
                if not body.strip():
                    body = self._civora_tracking_html(msg)
                if not body:
                    continue

                # Récupérer le nom lisible du record source
                ref_name = ""
                if model == 'civora.lease.contract':
                    contract = contracts.filtered(lambda c: c.id == msg.res_id)
                    ref_name = contract.name if contract else ""
                elif model == 'civora.deposit.refund':
                    refund = refunds.filtered(lambda r: r.id == msg.res_id)
                    ref_name = refund.name if refund else ""
                elif model == 'civora.lease':
                    ref_name = self.name or ""

                events.append({
                    'id': "msg_%d" % msg.id,
                    'date': msg.date.isoformat() if msg.date else False,
                    'author': msg.author_id.name if msg.author_id else (msg.email_from or "Système"),
                    'model': model,
                    'model_label': meta['label'],
                    'icon': meta['icon'],
                    'variant': meta['variant'],
                    'title': msg.subject or "",
                    'body': body,
                    'ref': ref_name,
                    'category': 'contract' if model == 'civora.lease.contract'
                              else 'refund' if model == 'civora.deposit.refund'
                              else 'other',
                })

        # Ajouter les événements de paiements (création)
        pay_meta = MODEL_META['civora.lease.payment']
        for p in self.payment_ids.sorted('create_date', reverse=True):
            title = ""
            body = ""
            if p.status == 'cancelled':
                # Événement d'annulation déjà loggué via message_post,
                # on ne double pas
                continue
            type_label = dict(
                p.__class__._fields['payment_type'].selection
            ).get(p.payment_type, p.payment_type or 'Loyer')
            method_label = dict(
                p.__class__._fields['method'].selection
            ).get(p.method, p.method or '')
            title = "%s encaissé" % type_label
            # Markup + % : les valeurs interpolees sont echappees. Sans cela,
            # une reference de paiement contenant une balise serait executee,
            # la timeline rendant ce HTML via markup() cote navigateur.
            body = Markup(
                "<div>Montant : <b>%s %s</b></div>"
                "<div>Mode : %s</div>"
            ) % (
                p.amount, p.currency_id.name or "",
                method_label,
            )
            if p.reference:
                body += Markup("<div>Référence : %s</div>") % p.reference
            events.append({
                'id': "pay_%d" % p.id,
                'date': p.create_date.isoformat() if p.create_date else False,
                'author': p.create_uid.name if p.create_uid else "Système",
                'model': 'civora.lease.payment',
                'model_label': pay_meta['label'],
                'icon': pay_meta['icon'],
                'variant': pay_meta['variant'],
                'title': title,
                'body': body,
                'ref': "%s" % p.date,
                'category': 'payment',
            })

        # Filtrer par catégorie si demandé
        if category and category != 'all':
            events = [e for e in events if e['category'] == category]

        # Trier par date décroissante
        events.sort(key=lambda e: e['date'] or "", reverse=True)

        return events

    def _compute_reminder_count(self):
        for lease in self:
            lease.reminder_count = len(lease.reminder_ids)

    # ═══════════════════════════════════════════════════════════════════
    # Incidents & Relances (Bloc B)
    # ═══════════════════════════════════════════════════════════════════
    def get_incidents_data(self):
        """Retourne les échéances en retard avec classification de sévérité.

        Sévérité par jours de retard :
        - 'soft'     : 1-15 jours
        - 'moderate' : 15-30 jours
        - 'firm'     : 30-60 jours
        - 'legal'    : 60+ jours (candidat à mise en demeure)
        """
        self.ensure_one()
        today = fields.Date.context_today(self)
        overdue = self.installment_ids.filtered(
            lambda i: i.state in ('overdue', 'partial')
            and i.due_date and i.due_date < today
        ).sorted('due_date')
        result = []
        for inst in overdue:
            days = (today - inst.due_date).days
            if days <= 15:
                severity = 'soft'
                severity_label = "Léger"
            elif days <= 30:
                severity = 'moderate'
                severity_label = "Modéré"
            elif days <= 60:
                severity = 'firm'
                severity_label = "Ferme"
            else:
                severity = 'legal'
                severity_label = "Critique"
            result.append({
                'id': inst.id,
                'period_label': inst.period_label,
                'due_date': str(inst.due_date) if inst.due_date else False,
                'amount_due': inst.amount_due,
                'amount_paid': inst.amount_paid,
                'amount_remaining': inst.amount_remaining,
                'days_overdue': days,
                'severity': severity,
                'severity_label': severity_label,
                'state': inst.state,
            })
        return result

    def get_reminders_history(self, limit=50):
        """Historique des relances de ce bail, triées date desc."""
        self.ensure_one()
        reminders = self.reminder_ids.sorted(
            lambda r: (r.date or fields.Date.today(), r.id), reverse=True
        )[:limit]
        channel_labels = dict(
            self.env['civora.lease.reminder']._fields['channel'].selection
        )
        severity_labels = dict(
            self.env['civora.lease.reminder']._fields['severity'].selection
        )
        state_labels = dict(
            self.env['civora.lease.reminder']._fields['state'].selection
        )
        return [
            {
                'id': r.id,
                'name': r.name,
                'date': str(r.date) if r.date else False,
                'channel': r.channel,
                'channel_label': channel_labels.get(r.channel, r.channel),
                'severity': r.severity,
                'severity_label': severity_labels.get(r.severity, r.severity),
                'subject': r.subject or "",
                'body': r.body or "",
                'arrears_amount': r.arrears_amount,
                'arrears_days': r.arrears_days,
                'sent_by': r.sent_by.name if r.sent_by else "",
                'state': r.state,
                'state_label': state_labels.get(r.state, r.state),
            }
            for r in reminders
        ]

    def get_risk_score(self):
        """Calcule un score de risque impayé (0-100) — heuristique transparente.

        Facteurs :
        - Nombre de retards actuels (0-30 points)
        - Ancienneté du retard le plus vieux (0-30 points)
        - Historique retards passés (0-20 points)
        - Taux de paiement global (0-20 points)

        Interprétation :
        - 0-30   : faible (vert)
        - 31-60  : modéré (orange)
        - 61-100 : élevé (rouge)
        """
        self.ensure_one()
        today = fields.Date.context_today(self)
        installments = self.installment_ids

        overdue = installments.filtered(lambda i: i.state == 'overdue')
        overdue_count_score = min(30, len(overdue) * 10)

        max_days = 0
        for inst in overdue:
            if inst.due_date:
                d = (today - inst.due_date).days
                if d > max_days:
                    max_days = d
        if max_days <= 0:
            days_score = 0
        elif max_days <= 15:
            days_score = 8
        elif max_days <= 30:
            days_score = 16
        elif max_days <= 60:
            days_score = 24
        else:
            days_score = 30

        past_due = installments.filtered(
            lambda i: i.due_date and i.due_date < today
        )
        if past_due:
            late_ratio = len(past_due.filtered(
                lambda i: i.state in ('overdue', 'partial')
            )) / len(past_due)
            history_score = round(late_ratio * 20)
        else:
            history_score = 0

        rate = self.payment_rate or 100.0
        if rate >= 95:
            rate_score = 0
        elif rate >= 80:
            rate_score = 10
        elif rate >= 60:
            rate_score = 15
        else:
            rate_score = 20

        total = overdue_count_score + days_score + history_score + rate_score
        total = min(100, max(0, total))

        if total <= 30:
            level = 'low'
            level_label = "Faible"
        elif total <= 60:
            level = 'medium'
            level_label = "Modéré"
        else:
            level = 'high'
            level_label = "Élevé"

        return {
            'score': total,
            'level': level,
            'level_label': level_label,
            'breakdown': {
                'overdue_count': len(overdue),
                'overdue_count_points': overdue_count_score,
                'max_days_overdue': max_days,
                'days_points': days_score,
                'late_history_points': history_score,
                'payment_rate': rate,
                'rate_points': rate_score,
            },
        }

    def create_reminder(self, vals):
        """Crée une relance en brouillon pour ce bail.

        `vals` doit contenir : channel, severity, subject, body, installment_ids
        (liste d'ids). arrears_amount et arrears_days sont calculés si absents.
        """
        self.ensure_one()
        today = fields.Date.context_today(self)
        overdue = self.installment_ids.filtered(
            lambda i: i.state in ('overdue', 'partial')
        )
        if 'arrears_amount' not in vals:
            vals['arrears_amount'] = sum(i.amount_remaining for i in overdue)
        if 'arrears_days' not in vals:
            max_days = 0
            for i in overdue:
                if i.due_date and i.due_date < today:
                    d = (today - i.due_date).days
                    if d > max_days:
                        max_days = d
            vals['arrears_days'] = max_days
        vals['lease_id'] = self.id
        installment_ids = vals.pop('installment_ids', None)
        if installment_ids:
            vals['installment_ids'] = [(6, 0, installment_ids)]
        reminder = self.env['civora.lease.reminder'].create(vals)
        return reminder.id

    # ═══════════════════════════════════════════════════════════════════
    # Lien Pipeline → Location (Bloc C)
    # ═══════════════════════════════════════════════════════════════════
    @api.model
    def create_lease_from_opportunity(self, opportunity_id, extra_vals=None):
        """Crée un bail à partir d'une opportunité Pipeline.

        Retourne l'id du bail créé. Le lien opportunity_id est établi
        automatiquement.
        """
        from odoo.exceptions import UserError
        opp = self.env['civora.opportunity'].browse(opportunity_id)
        if not opp.exists():
            raise UserError("Opportunité introuvable.")
        if opp.transaction != 'location':
            raise UserError(
                "Cette opportunité n'est pas de type 'Location' — "
                "impossible de créer un bail à partir d'elle."
            )
        base_vals = opp.action_prepare_lease_vals()
        for k in ['property_name', 'tenant_name', 'agent_name']:
            base_vals.pop(k, None)
        if extra_vals:
            base_vals.update(extra_vals)
        if not base_vals.get('rent') or base_vals.get('rent') <= 0:
            raise UserError(
                "Le loyer doit être renseigné (>0) avant la création du bail. "
                "Ajustez le montant estimé de l'opportunité ou saisissez-le manuellement."
            )
        lease = self.create([base_vals])
        return lease.id

    # ═══════════════════════════════════════════════════════════════════
    # Impayés — Vue portefeuille
    # ═══════════════════════════════════════════════════════════════════
    # La grille de sévérité est volontairement identique à celle de
    # get_incidents_data() : un gestionnaire qui voit "Ferme" sur l'écran
    # portefeuille doit retrouver exactement la même qualification en
    # ouvrant le bail. Deux grilles divergentes seraient une source de
    # contestation interne.
    ARREARS_SEVERITY_GRID = [
        (15, 'soft', "Léger"),
        (30, 'moderate', "Modéré"),
        (60, 'firm', "Ferme"),
    ]
    ARREARS_SEVERITY_LAST = ('legal', "Critique")

    @api.model
    def _arrears_classify(self, days):
        """Qualifie un retard en sévérité à partir de son ancienneté."""
        for limit, code, label in self.ARREARS_SEVERITY_GRID:
            if days <= limit:
                return code, label
        return self.ARREARS_SEVERITY_LAST

    @api.model
    def get_arrears_portfolio(self):
        """Agrège les impayés de tout le portefeuille, un enregistrement par bail.

        Ne remonte que les baux non résiliés portant au moins une échéance
        échue non soldée. Le montant retenu est le RESTE À PAYER cumulé, pas
        le montant dû : un locataire ayant réglé 80 % de son loyer ne doit pas
        être relancé pour la totalité.

        Le filtrage multi-société est assuré par les ir.rule — aucun sudo()
        ici, c'est volontaire : cet écran ne doit jamais montrer le
        portefeuille d'une autre agence.
        """
        today = fields.Date.context_today(self)
        leases = self.search([('state', '!=', 'ended')])
        if not leases:
            return []

        # Une seule lecture des échéances en retard pour tout le portefeuille.
        # Boucler avec un search() par bail ferait N+1 requêtes et rendrait
        # l'écran inutilisable au-delà de quelques centaines de baux.
        installments = self.env['civora.lease.installment'].search([
            ('lease_id', 'in', leases.ids),
            ('state', 'in', ('overdue', 'partial')),
            ('due_date', '<', today),
        ], order='due_date asc')

        by_lease = {}
        for inst in installments:
            by_lease.setdefault(inst.lease_id.id, []).append(inst)

        # Dernière relance connue par bail, en une requête.
        last_reminder = {}
        reminders = self.env['civora.lease.reminder'].search([
            ('lease_id', 'in', list(by_lease.keys())),
            ('state', '=', 'sent'),
        ], order='date desc, id desc')
        for rem in reminders:
            last_reminder.setdefault(rem.lease_id.id, rem)

        rows = []
        for lease in leases:
            insts = by_lease.get(lease.id)
            if not insts:
                continue

            oldest = insts[0]
            days = (today - oldest.due_date).days if oldest.due_date else 0
            severity, severity_label = self._arrears_classify(days)
            total_due = sum(i.amount_remaining or 0.0 for i in insts)
            if lease.currency_id and lease.currency_id.is_zero(total_due):
                continue

            rem = last_reminder.get(lease.id)
            tenant = lease.tenant_id

            rows.append({
                'lease_id': lease.id,
                'lease_ref': lease.name or "—",
                'tenant_id': tenant.id if tenant else False,
                'tenant_name': (tenant.name if tenant else "") or "—",
                'tenant_email': (tenant.email or "") if tenant else "",
                'tenant_phone': (tenant.phone or "") if tenant else "",
                'property_id': lease.property_id.id if lease.property_id else False,
                'property_name': (lease.property_id.name if lease.property_id else "") or "—",
                'city': lease.property_city or "",
                'agent_name': (lease.agent_id.name if lease.agent_id else "") or "",
                'payday': lease.payday or 0,
                'rent': lease.rent or 0.0,
                'amount_due': total_due,
                'days_overdue': days,
                'severity': severity,
                'severity_label': severity_label,
                'installment_count': len(insts),
                'installment_ids': [i.id for i in insts],
                'periods': ", ".join(i.period_label or "" for i in insts[:3]),
                # Forme attendue par ReminderDrawer.defaultContext.periods :
                # le drawer est partage avec l'onglet Incidents du Bail 360,
                # les deux appelants doivent lui parler le meme langage.
                'periods_detail': [{
                    'period_label': i.period_label or "",
                    'days_overdue': (today - i.due_date).days if i.due_date else 0,
                    'amount_remaining': i.amount_remaining or 0.0,
                } for i in insts],
                'last_reminder_date': str(rem.date) if rem and rem.date else False,
                'last_reminder_days': (today - rem.date).days if rem and rem.date else False,
                'last_reminder_severity': rem.severity if rem else False,
                'reminder_count': lease.reminder_count,
            })

        # Le plus grave d'abord, puis le plus gros montant : c'est l'ordre
        # dans lequel un gestionnaire traite réellement sa journée.
        order = {'legal': 0, 'firm': 1, 'moderate': 2, 'soft': 3}
        rows.sort(key=lambda r: (order.get(r['severity'], 9), -r['amount_due']))
        return rows

    @api.model
    def get_arrears_summary(self):
        """KPIs de l'écran Impayés, calculés sur la même base que la liste."""
        rows = self.get_arrears_portfolio()
        total = sum(r['amount_due'] for r in rows)
        legal = [r for r in rows if r['severity'] == 'legal']
        never = [r for r in rows if not r['last_reminder_date']]
        return {
            'lease_count': len(rows),
            'total_due': total,
            'legal_count': len(legal),
            'legal_amount': sum(r['amount_due'] for r in legal),
            'never_reminded': len(never),
            'avg_days': round(sum(r['days_overdue'] for r in rows) / len(rows)) if rows else 0,
            'max_days': max((r['days_overdue'] for r in rows), default=0),
        }

    # ═══════════════════════════════════════════════════════════════════
    # Command Center — Agrégats globaux (Bloc D)
    # ═══════════════════════════════════════════════════════════════════
    @api.model
    def get_command_center_kpis(self):
        """Retourne les KPIs agrégés du domaine 'locations' pour le Command Center.

        Le filtrage multi-société est automatique via ir.rule.

        Retour :
        {
            'mrr_locatif':      {value_num, value_fmt, delta_pct, hint},
            'baux_actifs':      {value_num, value_fmt, delta_pct, hint},
            'collections':      {value_num, value_fmt, delta_pct, hint},
            'impayes':          {value_num, value_fmt, delta_pct, hint},
            'occupation':       {value_num, value_fmt, delta_pct, hint},
            'occupancy_donut':  [{name, value, color}, ...],
            'activity':         [{tone, title, detail, ago}, ...],
        }
        """
        today = fields.Date.context_today(self)
        Lease = self.env['civora.lease']
        active_leases = Lease.search([('state', '=', 'active')])
        all_leases = Lease.search([])

        # --- MRR locatif -----------------------------------------------
        mrr = sum(lease.rent for lease in active_leases)
        mrr_prev = sum(
            lease.rent for lease in all_leases
            if lease.date_start and lease.date_start <= today.replace(day=1)
            and (not lease.date_end or lease.date_end >= today.replace(day=1))
        )
        mrr_delta_pct = self._safe_pct_delta(mrr, mrr_prev)

        # --- Baux actifs -----------------------------------------------
        active_count = len(active_leases)

        # --- Collections (taux d'encaissement moyen pondéré) -----------
        total_expected = sum(l.total_expected for l in active_leases)
        total_paid = sum(l.total_paid for l in active_leases)
        collections_pct = (
            (total_paid / total_expected * 100.0) if total_expected else 0.0
        )

        # --- Impayés ----------------------------------------------------
        overdue_leases = active_leases.filtered(lambda l: l.status == 'retard')
        arrears_amount = sum(l.arrears_amount for l in overdue_leases)
        arrears_count = len(overdue_leases)

        # --- Taux d'occupation (properties) ----------------------------
        Property = self.env['civora.property']
        # Seuls les biens louables (non-bâtiments) comptent
        all_props = Property.search([('is_building', '=', False)])
        # Les valeurs de status varient selon la config civora_biens.
        # On considère "loué" tout bien qui a un bail actif — plus fiable
        # que de se baser sur le seul champ status.
        loued_props = all_props.filtered(
            lambda p: p.lease_ids.filtered(lambda l: l.state == 'active')
        )
        saisonnier_props = all_props.filtered(
            lambda p: p.status == 'reserve' and p not in loued_props
        )
        disponible_props = all_props - loued_props - saisonnier_props
        total_props = len(all_props)
        loued_count = len(loued_props)
        saisonnier_count = len(saisonnier_props)
        disponible_count = len(disponible_props)
        occ_pct = (
            (loued_count + saisonnier_count) / total_props * 100.0
            if total_props else 0.0
        )
        occupancy_donut = []
        if total_props:
            occupancy_donut = [
                {
                    'name': "Loué",
                    'value': round(loued_count / total_props * 100),
                    'color': "#00ab68",
                },
                {
                    'name': "Réservé",
                    'value': round(saisonnier_count / total_props * 100),
                    'color': "#25afd2",
                },
                {
                    'name': "Disponible",
                    'value': round(disponible_count / total_props * 100),
                    'color': "#c7ccd3",
                },
            ]

        # --- Activité live : derniers évènements -----------------------
        activity = self._build_command_center_activity(limit=5)

        return {
            'mrr_locatif': {
                'value_num': mrr,
                'value_fmt': self._fmt_fcfa(mrr),
                'delta_pct': mrr_delta_pct,
                'hint': "%d baux actifs" % active_count,
            },
            'baux_actifs': {
                'value_num': active_count,
                'value_fmt': str(active_count),
                'delta_pct': None,
                'hint': "sur %d baux au total" % len(all_leases),
            },
            'collections': {
                'value_num': collections_pct,
                'value_fmt': "%d%%" % round(collections_pct),
                'delta_pct': None,
                'hint': "encaissé / attendu",
            },
            'impayes': {
                'value_num': arrears_amount,
                'value_fmt': self._fmt_fcfa(arrears_amount),
                'delta_pct': None,
                'hint': "%d dossier(s)" % arrears_count,
            },
            'occupation': {
                'value_num': occ_pct,
                'value_fmt': "%d%%" % round(occ_pct),
                'delta_pct': None,
                'hint': "%d biens au total" % total_props,
            },
            'occupancy_donut': occupancy_donut,
            'activity': activity,
        }

    @api.model
    def _fmt_fcfa(self, n):
        """Format identique au front : '142M FCFA', '4,2M FCFA', '1,2Md FCFA'."""
        n = float(n or 0)
        if n >= 1e9:
            v = n / 1e9
            s = ("%.1f" % v).replace('.', ',') if v % 1 else str(int(v))
            return s + "Md FCFA"
        if n >= 1e6:
            v = n / 1e6
            s = ("%.1f" % v).replace('.', ',') if v % 1 else str(int(v))
            return s + "M FCFA"
        if n >= 1e3:
            return "%dk FCFA" % round(n / 1e3)
        return "%d FCFA" % round(n)

    @api.model
    def _safe_pct_delta(self, current, previous):
        if not previous:
            return None
        return round((current - previous) / previous * 100.0, 1)

    @api.model
    def _build_command_center_activity(self, limit=5):
        """Compile les 5 derniers évènements pertinents : signatures, paiements,
        retards, relances. Trie par date desc.
        """
        activity = []
        today = fields.Date.context_today(self)

        # 1) Baux signés récemment (état actif, date de début récente)
        recent_leases = self.search(
            [('state', '=', 'active')],
            order='date_start desc, id desc', limit=limit,
        )
        for lease in recent_leases:
            if not lease.date_start:
                continue
            days = (today - lease.date_start).days
            if days < 0 or days > 90:
                continue
            activity.append({
                'tone': 'primary',
                'title': "Bail signé",
                'detail': "%s · %s/mois" % (
                    lease.property_id.name if lease.property_id else "—",
                    self._fmt_fcfa(lease.rent),
                ),
                'ago': self._fmt_ago(days),
                'sort_key': lease.date_start.toordinal(),
            })

        # 2) Paiements récents (encaissés dans les 30 derniers jours)
        Payment = self.env['civora.lease.payment']
        recent_pays = Payment.search(
            [('status', 'in', ('paid', 'partial'))],
            order='date desc, id desc', limit=limit,
        )
        for p in recent_pays:
            if not p.date:
                continue
            days = (today - p.date).days
            if days < 0 or days > 30:
                continue
            tenant = p.lease_id.tenant_id if p.lease_id else False
            activity.append({
                'tone': 'success',
                'title': "Paiement reçu",
                'detail': "%s · %s" % (
                    self._fmt_fcfa(p.amount),
                    tenant.name if tenant else "—",
                ),
                'ago': self._fmt_ago(days),
                'sort_key': p.date.toordinal(),
            })

        # 3) Loyers en retard (échéances overdue)
        Installment = self.env['civora.lease.installment']
        overdue_installments = Installment.search(
            [('state', '=', 'overdue')],
            order='due_date desc, id desc', limit=limit,
        )
        for i in overdue_installments:
            if not i.due_date:
                continue
            days_overdue = (today - i.due_date).days
            if days_overdue <= 0:
                continue
            lease = i.lease_id
            tenant_name = (lease.tenant_id.name or "—") if lease and lease.tenant_id else "—"
            property_name = (lease.property_id.name or "—") if lease and lease.property_id else "—"
            activity.append({
                'tone': 'warning',
                'title': "Loyer en retard",
                'detail': "%s · %d jour(s) · %s" % (property_name, days_overdue, tenant_name),
                'ago': self._fmt_ago(min(days_overdue, 30)),
                'sort_key': i.due_date.toordinal(),
            })

        # Tri décroissant par date et limite
        activity.sort(key=lambda a: a.get('sort_key', 0), reverse=True)
        for a in activity:
            a.pop('sort_key', None)
        return activity[:limit]

    @api.model
    def _fmt_ago(self, days):
        if days == 0:
            return "aujourd'hui"
        if days == 1:
            return "hier"
        if days < 7:
            return "il y a %d jours" % days
        if days < 30:
            return "il y a %d sem." % (days // 7)
        return "il y a %d mois" % (days // 30)

    @api.model
    def check_property_availability(self, property_id, exclude_lease_id=False):
        """Vérifie si un bien est disponible pour un nouveau bail.

        Retourne un dict :
        - available (bool) : True si le bien peut recevoir un nouveau bail
        - existing_lease (dict|False) : infos du bail bloquant s'il y en a
        """
        if not property_id:
            return {'available': True, 'existing_lease': False}
        domain = [
            ('property_id', '=', property_id),
            ('state', '!=', 'ended'),
        ]
        if exclude_lease_id:
            domain.append(('id', '!=', exclude_lease_id))
        existing = self.search(domain, limit=1)
        if not existing:
            return {'available': True, 'existing_lease': False}
        return {
            'available': False,
            'existing_lease': {
                'id': existing.id,
                'name': existing.name,
                'tenant_name': existing.tenant_id.name or "—",
                'date_start': str(existing.date_start) if existing.date_start else False,
                'date_end': str(existing.date_end) if existing.date_end else False,
                'state': existing.state,
            },
        }

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for lease in self:
            if lease.date_end and lease.date_start and lease.date_end < lease.date_start:
                raise ValidationError("La date de fin doit être postérieure à la date d'entrée.")

    @api.constrains('payday')
    def _check_payday(self):
        for lease in self:
            if lease.payday and (lease.payday < 1 or lease.payday > 28):
                raise ValidationError(
                    "Le jour de paiement doit être compris entre 1 et 28 "
                    "(pour éviter les mois de 29 à 31 jours)."
                )

    @api.constrains('advance_months', 'caution_months', 'agency_months')
    def _check_initial_months(self):
        """Valide les nombres de mois d'avance/caution/agence."""
        for lease in self:
            for field_name, label in [
                ('advance_months', "mois d'avance"),
                ('caution_months', "mois de caution"),
                ('agency_months', "mois d'agence"),
            ]:
                v = lease[field_name] or 0
                if v < 0:
                    raise ValidationError(
                        "Le nombre de %s ne peut pas être négatif." % label
                    )
                if v > 24:
                    raise ValidationError(
                        "Le nombre de %s (%d) semble excessif. "
                        "Merci de vérifier la saisie (max 24)."
                        % (label, v)
                    )

    @api.constrains('property_id', 'state')
    def _check_unique_active_lease(self):
        """Un bien ne peut avoir qu'un seul bail actif ou brouillon à la fois.

        Règle métier : tant qu'un bail existe pour un bien et n'est pas
        résilié (state != 'ended'), aucun autre bail ne peut être créé
        pour le même bien.
        """
        for lease in self:
            if not lease.property_id or lease.state == 'ended':
                continue
            # Chercher un autre bail non résilié pour le même bien
            conflict = self.search([
                ('property_id', '=', lease.property_id.id),
                ('state', '!=', 'ended'),
                ('id', '!=', lease.id),
                ('company_id', '=', lease.company_id.id),
            ], limit=1)
            if conflict:
                raise ValidationError(
                    "Impossible de créer ou d'activer ce bail : le bien "
                    "« %s » a déjà un bail actif (%s) au nom de %s.\n\n"
                    "Pour reprendre ce bien, vous devez d'abord résilier "
                    "le bail existant."
                    % (
                        lease.property_id.name,
                        conflict.name,
                        conflict.tenant_id.name or "—",
                    )
                )

    _rent_positive = models.Constraint(
        'check (rent >= 0)',
        "Le loyer ne peut pas être négatif.",
    )
    _charges_positive = models.Constraint(
        'check (charges >= 0)',
        "Les charges ne peuvent pas être négatives.",
    )
    _deposit_positive = models.Constraint(
        'check (deposit >= 0)',
        "Le dépôt de garantie ne peut pas être négatif.",
    )
