# -*- coding: utf-8 -*-
"""
civora.lease.contract — Contrat de bail numérique CIVORA.

Cycle de vie :
  draft          → Brouillon (en cours de rédaction)
  pending_lessor → En attente signature bailleur
  signed_lessor  → Bailleur a signé, envoyé au locataire
  signed_tenant  → Locataire a signé (contrat finalisé)
  cancelled      → Annulé

Signature :
  - Bailleur signe dans CIVORA (canvas JS → base64 PNG stocké dans sign_lessor)
  - Un token UUID unique est généré à l'envoi
  - Le locataire reçoit un lien /civora/contract/<token> (page publique, inc. C)
  - Après signature locataire : signed_at_tenant + sign_tenant remplis
"""
import uuid
from datetime import date

import logging

from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


# --- Helpers montant en lettres (réutilise la logique de civora_lease_receipt) ---
_UNITS = ["", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf",
          "dix", "onze", "douze", "treize", "quatorze", "quinze", "seize",
          "dix-sept", "dix-huit", "dix-neuf"]
_TENS = ["", "", "vingt", "trente", "quarante", "cinquante", "soixante",
         "soixante", "quatre-vingt", "quatre-vingt"]


def _two_digits(n):
    if n < 20:
        return _UNITS[n]
    t, u = divmod(n, 10)
    if t == 7:
        return "soixante-" + _UNITS[10 + u]
    if t == 9:
        return "quatre-vingt-" + _UNITS[u] if u else "quatre-vingts"
    return _TENS[t] + ("-et-" + _UNITS[u] if u == 1 and t not in (8, 9) else
                       ("-" + _UNITS[u] if u else ("s" if t == 8 else "")))


def _hundreds(n):
    h, r = divmod(n, 100)
    prefix = ("cent" if h == 1 else (_UNITS[h] + "-cent" + ("s" if r == 0 and h > 1 else ""))) if h else ""
    return (prefix + ("-" if prefix and r else "") + _two_digits(r)) if prefix or r else "zéro"


def _amount_to_words_fr(amount):
    n = int(round(amount))
    if n == 0:
        return "zéro"
    parts = []
    if n >= 1_000_000_000:
        b, n = divmod(n, 1_000_000_000)
        parts.append(_hundreds(b) + " milliard" + ("s" if b > 1 else ""))
    if n >= 1_000_000:
        m, n = divmod(n, 1_000_000)
        parts.append(_hundreds(m) + " million" + ("s" if m > 1 else ""))
    if n >= 1_000:
        k, n = divmod(n, 1_000)
        parts.append(("mille" if k == 1 else _hundreds(k) + "-mille"))
    if n:
        parts.append(_hundreds(n))
    return " ".join(parts)


def _months_between(d1, d2):
    """Nombre de mois entiers entre deux dates."""
    return max(1, (d2.year - d1.year) * 12 + d2.month - d1.month)


CONTRACT_STATE = [
    ('draft', "Brouillon"),
    ('pending_lessor', "En attente signature bailleur"),
    ('signed_lessor', "Bailleur signé — envoyé au locataire"),
    ('signed_tenant', "Signé des deux parties"),
    ('expired', "Expiré"),
    ('terminated', "Rompu"),
    ('cancelled', "Annulé"),
]


class CivoraLeaseContract(models.Model):
    _name = 'civora.lease.contract'
    _description = "Contrat de bail numérique"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'
    _check_company_auto = True

    # ── Identification ──────────────────────────────────────────────────
    name = fields.Char(
        string="Référence", copy=False, index=True, readonly=True,
        default=lambda self: self._default_ref(),
    )
    lease_id = fields.Many2one(
        'civora.lease', string="Bail", required=True, ondelete='cascade',
        index=True, check_company=True, tracking=True,
    )
    state = fields.Selection(
        CONTRACT_STATE, string="État", default='draft', required=True,
        tracking=True,
    )
    token = fields.Char(
        string="Token de signature", copy=False, index=True, readonly=True,
    )

    # ── Données dénormalisées au moment de la génération ────────────────
    # (snapshot : le contrat PDF doit refléter les données au moment de la signature)
    snapshot_data = fields.Text(
        string="Données snapshot (JSON)",
        help="JSON des données interpolées au moment de la génération du contrat.",
        copy=False,
    )

    # ── Clauses sélectionnées pour ce contrat ────────────────────────────
    clause_ids = fields.Many2many(
        'civora.lease.clause',
        'contract_clause_rel',
        'contract_id', 'clause_id',
        string="Clauses",
    )

    # ── Signatures ──────────────────────────────────────────────────────
    sign_lessor = fields.Binary(
        string="Signature bailleur (PNG base64)",
        attachment=False, copy=False,
    )
    signed_at_lessor = fields.Datetime(
        string="Date signature bailleur", readonly=True, copy=False,
    )
    signed_by_lessor = fields.Char(
        string="Signataire bailleur", readonly=True, copy=False,
    )
    # ── Remarques du locataire ──────────────────────────────────────────
    remark_ids = fields.One2many(
        'civora.contract.remark', 'contract_id', string="Remarques du locataire",
    )
    remark_open_count = fields.Integer(
        string="Remarques en attente", compute='_compute_remark_counts',
    )
    remark_count = fields.Integer(
        string="Remarques", compute='_compute_remark_counts',
    )

    # ── Traçabilité de la signature locataire ───────────────────────────
    # Sans IP ni user-agent, une signature électronique n'a quasiment aucune
    # valeur probante en cas de contestation.
    sign_tenant_ip = fields.Char(string="IP du signataire", readonly=True, copy=False)
    sign_tenant_ua = fields.Char(string="Navigateur du signataire", readonly=True, copy=False)

    sign_tenant = fields.Binary(
        string="Signature locataire (PNG base64)",
        attachment=False, copy=False,
    )
    signed_at_tenant = fields.Datetime(
        string="Date signature locataire", readonly=True, copy=False,
    )

    # ── Computed depuis le bail ─────────────────────────────────────────
    company_id = fields.Many2one(
        related='lease_id.company_id', store=True, readonly=True,
    )
    tenant_id = fields.Many2one(
        related='lease_id.tenant_id', store=True, readonly=True,
    )
    property_id = fields.Many2one(
        related='lease_id.property_id', store=True, readonly=True,
    )
    lease_type = fields.Selection(
        related='lease_id.lease_type', store=True, readonly=True,
    )

    # ── Métadonnées ─────────────────────────────────────────────────────
    date_issued = fields.Date(
        string="Date d'émission", default=fields.Date.context_today, readonly=True,
    )
    # Période couverte par ce contrat (snapshot depuis le bail à la signature)
    date_start = fields.Date(
        string="Début du contrat",
        help="Date de prise d'effet du contrat (snapshot depuis le bail).",
    )
    date_end = fields.Date(
        string="Fin du contrat",
        help="Date de fin de validité du contrat (snapshot depuis le bail).",
    )
    is_expired = fields.Boolean(
        string="Expiré",
        compute='_compute_is_expired',
        store=True,
        help="Vrai si la date de fin du contrat est passée.",
    )
    note = fields.Text(string="Note interne")

    # ── Rupture de contrat ──────────────────────────────────────────────
    date_terminated = fields.Date(
        string="Date de rupture", copy=False, readonly=True,
        help="Date effective de rupture du contrat.",
    )
    termination_reason = fields.Selection(
        [
            ('mutual_agreement', "Accord mutuel des parties"),
            ('tenant_notice', "Congé donné par le locataire"),
            ('lessor_notice', "Congé donné par le bailleur"),
            ('non_payment', "Non-paiement (clause résolutoire)"),
            ('breach', "Manquement grave aux obligations"),
            ('property_sale', "Vente du bien"),
            ('force_majeure', "Force majeure"),
            ('other', "Autre motif"),
        ],
        string="Motif de rupture", copy=False, readonly=True,
    )
    termination_note = fields.Text(
        string="Détails de la rupture", copy=False, readonly=True,
    )
    terminated_by = fields.Char(
        string="Rupture prononcée par", copy=False, readonly=True,
    )

    @api.depends('date_end', 'state')
    def _compute_is_expired(self):
        today = fields.Date.context_today(self)
        for c in self:
            c.is_expired = bool(c.date_end and c.date_end < today
                                and c.state in ('signed_lessor', 'signed_tenant'))

    @api.model
    def cron_update_expired_contracts(self):
        """Cron quotidien : passe les contrats signés dont la période est
        terminée à l'état 'expired'."""
        today = fields.Date.context_today(self)
        to_expire = self.search([
            ('state', 'in', ('signed_lessor', 'signed_tenant')),
            ('date_end', '<', today),
        ])
        if to_expire:
            to_expire.write({'state': 'expired'})
        return True

    # ───────────────────────────────────────────────────────────────────
    # Séquence / référence
    # ───────────────────────────────────────────────────────────────────
    @api.model
    def _default_ref(self):
        year = date.today().year
        return "CTR-%s-DRAFT" % year

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or 'DRAFT' in (vals.get('name') or ''):
                year = date.today().year
                # Référence : CTR-HABITATION-XXXXXXXX ou CTR-COMMERCIAL-XXXXXXXX
                suffix = uuid.uuid4().hex[:8].upper()
                lease_type = vals.get('lease_type', 'residentiel')
                type_label = 'HABITATION' if lease_type == 'residentiel' else 'COMMERCIAL'
                vals['name'] = "CTR-%s-%s" % (type_label, suffix)
        contracts = super().create(vals_list)
        # Pré-remplir les clauses depuis le jeu de clauses du type de bail
        for contract in contracts:
            if not contract.clause_ids and contract.lease_id:
                contract._prefill_clauses()
        return contracts

    def write(self, vals):
        """Détecte le passage à 'signed_tenant' pour déclencher l'échéancier."""
        # Contrats qui vont basculer à signed_tenant
        triggering = self.env['civora.lease.contract']
        if vals.get('state') == 'signed_tenant':
            triggering = self.filtered(lambda c: c.state != 'signed_tenant')
        res = super().write(vals)
        # Générer l'échéancier du bail lié pour chaque contrat qui vient d'être
        # signé des deux parties (uniquement s'il n'existe pas déjà)
        for contract in triggering:
            if contract.lease_id:
                contract.lease_id.generate_installments(force=False)
        return res

    # ───────────────────────────────────────────────────────────────────
    # Pré-remplissage des clauses
    # ───────────────────────────────────────────────────────────────────
    def _prefill_clauses(self):
        """Cherche le jeu de clauses actif pour ce type de bail + société.

        Fallback 1 : cherche dans toutes les sociétés accessibles par l'utilisateur.
        Fallback 2 : si aucun jeu, prend toutes les clauses actives du bon type
                     pour la société (ou toute société accessible).
        """
        self.ensure_one()
        lease_type = self.lease_id.lease_type
        company_id = self.lease_id.company_id.id

        # 1. Jeu exact : même société + même type
        clause_set = self.env['civora.lease.clause.set'].search([
            ('lease_type', '=', lease_type),
            ('company_id', '=', company_id),
            ('active', '=', True),
        ], limit=1, order='id desc')

        # 2. Fallback : n'importe quelle société accessible, même type
        if not clause_set:
            clause_set = self.env['civora.lease.clause.set'].search([
                ('lease_type', '=', lease_type),
                ('active', '=', True),
            ], limit=1, order='id desc')

        if clause_set and clause_set.clause_ids:
            self.clause_ids = [(6, 0, clause_set.clause_ids.ids)]
            return

        # 3. Fallback absolu : toutes les clauses actives du bon type
        clauses = self.env['civora.lease.clause'].search([
            ('lease_type', '=', lease_type),
            ('active', '=', True),
        ], order='sequence asc, id asc')
        if clauses:
            self.clause_ids = [(6, 0, clauses.ids)]

    # ───────────────────────────────────────────────────────────────────
    # Interpolation des placeholders
    # ───────────────────────────────────────────────────────────────────
    def _build_context(self):
        """Construit le dictionnaire de substitution pour ce contrat."""
        self.ensure_one()
        lease = self.lease_id
        company = lease.company_id or self.env.company
        tenant = lease.tenant_id
        prop = lease.property_id
        owner = lease.owner_id

        def fmt_money(amount):
            return "%s %s" % (
                "{:,.0f}".format(amount or 0).replace(",", " "),
                (lease.currency_id.name or "FCFA"),
            )

        def fmt_date(d):
            if not d:
                return ""
            MONTHS_FR = ["janvier", "février", "mars", "avril", "mai", "juin",
                         "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
            return "%d %s %d" % (d.day, MONTHS_FR[d.month - 1], d.year)

        duree_mois = 0
        duree_lettres = ""
        if lease.date_start and lease.date_end:
            duree_mois = _months_between(lease.date_start, lease.date_end)
            duree_lettres = _amount_to_words_fr(duree_mois)
        # Textes prêts à insérer dans les clauses (évite les () vides)
        if duree_mois:
            duree_texte = "%s (%d) mois" % (duree_lettres, duree_mois)
            fin_texte = fmt_date(lease.date_end)
        else:
            duree_texte = "indéterminée"
            fin_texte = "indéterminée"

        total_mensuel = (lease.rent or 0) + (lease.charges or 0)
        # Total à verser à la signature = 1 mois loyer + 1 mois caution
        total_entree = total_mensuel + (lease.deposit or 0)

        freq_map = {
            'monthly': 'mensuellement', 'quarterly': 'trimestriellement',
            'yearly': 'annuellement', False: 'mensuellement',
        }

        ctx = {
            # Bailleur (société)
            'bailleur': company.name or "",
            'bailleur_adresse': " ".join(filter(None, [company.street, company.city])),
            'bailleur_tel': company.phone or "",
            'bailleur_email': company.email or "",
            'bailleur_rccm': company.company_registry or "",
            'ville': company.city or "",
            # Locataire
            'locataire': tenant.name if tenant else "",
            'locataire_tel': tenant.phone if tenant else "",
            'locataire_email': tenant.email if tenant else "",
            'locataire_profession': (tenant.function if tenant else "") or "",
            # Propriétaire
            'proprietaire': owner.name if owner else (company.name or ""),
            # Bien
            'bien': prop.name if prop else "",
            'bien_adresse': " ".join(filter(None, [
                prop.street if prop else "",
                prop.city if prop else "",
            ])),
            # Type de bail
            'type_bail': dict(lease._fields['lease_type'].selection).get(lease.lease_type, ""),
            # Dates
            'date_debut': fmt_date(lease.date_start),
            'date_fin': fin_texte,
            'date_signature': fmt_date(self.date_issued or fields.Date.context_today(self)),
            # Durée
            'duree_mois': str(duree_mois) if duree_mois else "",
            'duree_lettres': duree_lettres,
            'duree_texte': duree_texte,
            # Financier
            'loyer': fmt_money(lease.rent),
            'charges': fmt_money(lease.charges),
            'total_mensuel': fmt_money(total_mensuel),
            'depot_garantie': fmt_money(lease.deposit),
            'total_entree': fmt_money(total_entree),
            'loyer_lettres': _amount_to_words_fr(lease.rent or 0),
            'total_lettres': _amount_to_words_fr(total_mensuel),
            'devise': lease.currency_id.name if lease.currency_id else "FCFA",
            # Paiement
            'frequence': freq_map.get(getattr(lease, 'payment_frequency', False), 'mensuellement'),
            'jour_paiement': str(lease.payday or 1),
            # Références
            'ref_contrat': self.name or "",
            'nb_chambres': str(getattr(prop, 'nb_rooms', '') or "") if prop else "",
        }
        return ctx

    def _interpolate(self, html_body, ctx):
        """Remplace tous les {{placeholder}} dans un corps HTML."""
        if not html_body:
            return ""
        result = html_body
        for key, value in ctx.items():
            result = result.replace("{{%s}}" % key, str(value))
        return result

    def _render_clauses(self):
        """Retourne la liste (numero, titre, corps_interpolé) pour le PDF."""
        self.ensure_one()
        ctx = self._build_context()
        rendered = []
        for clause in self.clause_ids.sorted('sequence'):
            rendered.append({
                'numero': clause.numero or "",
                'name': clause.name,
                'body': self._interpolate(clause.body, ctx),
            })
        return rendered

    # ───────────────────────────────────────────────────────────────────
    # API publique appelable depuis le JS (RPC)
    # ───────────────────────────────────────────────────────────────────
    @api.depends('remark_ids.state')
    def _compute_remark_counts(self):
        for c in self:
            c.remark_count = len(c.remark_ids)
            c.remark_open_count = len(c.remark_ids.filtered(lambda r: r.state == 'open'))

    def civora_can_sign(self):
        """Le locataire peut-il signer ? (option A : remarque = blocage)

        Retourne (autorise, motif). Un contrat contesté ne doit pas être
        signé : soit le locataire signe, soit il demande des modifications.
        """
        self.ensure_one()
        if self.state != 'signed_lessor':
            return False, "Ce contrat n'est pas en attente de votre signature."
        if self.remark_open_count:
            return False, (
                "Vous avez %d remarque(s) en attente de réponse. "
                "La signature sera de nouveau possible une fois que l'agence "
                "y aura répondu." % self.remark_open_count
            )
        return True, ""

    def render_clauses(self):
        """Wrapper public pour appel RPC depuis OWL."""
        self.ensure_one()
        return self._render_clauses()

    def reload_clauses(self):
        """Wrapper public : recharge les clauses depuis le jeu par défaut."""
        self.ensure_one()
        self._prefill_clauses()
        return self._render_clauses()

    def get_signatures(self):
        """Retourne les signatures décodées en base64 string.

        Nécessaire car un searchRead sur un fields.Binary retourne True/False
        et non le contenu du champ (optimisation Odoo).
        """
        self.ensure_one()
        return {
            'sign_lessor': self.sign_lessor.decode() if self.sign_lessor else False,
            'sign_tenant': self.sign_tenant.decode() if self.sign_tenant else False,
        }

    def action_update_dates(self, date_start, date_end):
        """Met à jour les dates de début et fin du contrat.

        Autorisé uniquement en brouillon ou signé bailleur (avant que
        le locataire ne signe). Les dates sont snapshotées : elles
        représentent la période contractuelle et sont indépendantes
        du bail sous-jacent une fois le contrat signé.
        """
        self.ensure_one()
        if self.state not in ('draft', 'pending_lessor', 'signed_lessor'):
            raise UserError(
                "Les dates ne peuvent plus être modifiées à ce stade "
                "(contrat déjà signé par le locataire, expiré ou annulé)."
            )
        # Conversion string ISO → date si nécessaire
        from datetime import date as _date
        def _parse(v):
            if not v:
                return False
            if isinstance(v, _date):
                return v
            return fields.Date.from_string(v)

        ds = _parse(date_start)
        de = _parse(date_end)
        if ds and de and de < ds:
            raise UserError("La date de fin doit être postérieure à la date de début.")
        self.write({
            'date_start': ds or False,
            'date_end':   de or False,
        })
        return True

    def action_terminate_contract(self, date_terminated, reason, note=None):
        """Prononce la rupture d'un contrat signé.

        - Seuls les contrats en état 'signed_lessor' ou 'signed_tenant'
          peuvent être rompus (un brouillon se supprime, un annulé/expiré
          n'a plus lieu d'être rompu).
        - date_terminated : date effective de rupture (obligatoire)
        - reason : clé de la selection termination_reason (obligatoire)
        - note : détails libres (optionnel)
        - Log dans le chatter du bail + du contrat.
        """
        self.ensure_one()
        if self.state not in ('signed_lessor', 'signed_tenant'):
            raise UserError(
                "Seul un contrat signé peut être rompu. "
                "Utilisez le bouton 'Annuler' pour un contrat en brouillon."
            )
        # Validation des paramètres
        from datetime import date as _date
        if not date_terminated:
            raise UserError("La date de rupture est requise.")
        if not reason:
            raise UserError("Le motif de rupture est requis.")
        valid_reasons = dict(self._fields['termination_reason'].selection).keys()
        if reason not in valid_reasons:
            raise UserError("Motif de rupture invalide.")
        # Conversion date
        if not isinstance(date_terminated, _date):
            date_terminated = fields.Date.from_string(date_terminated)
        # Cohérence : la date de rupture ne peut pas être antérieure au début
        if self.date_start and date_terminated < self.date_start:
            raise UserError(
                "La date de rupture ne peut pas être antérieure à la date "
                "de début du contrat."
            )
        # Écrire l'état + traces
        user = self.env.user
        reason_label = dict(self._fields['termination_reason'].selection).get(reason)
        self.write({
            'state': 'terminated',
            'date_terminated': date_terminated,
            'termination_reason': reason,
            'termination_note': (note or '').strip() or False,
            'terminated_by': user.name,
        })
        # Log dans le chatter du contrat
        body_contract = Markup(
            "<b>⚠ Contrat rompu</b><br/>"
            "Date de rupture : <b>%s</b><br/>"
            "Motif : <b>%s</b><br/>"
            "Rupture prononcée par : %s"
        ) % (date_terminated.strftime('%d/%m/%Y'), reason_label, user.name)
        if note:
            body_contract += Markup("<br/>Détails : %s") % note
        self.message_post(body=body_contract, subtype_xmlid='mail.mt_note')
        # Log dans le chatter du bail
        if self.lease_id:
            body_lease = Markup(
                "Le contrat <b>%s</b> a été rompu le <b>%s</b> "
                "— Motif : <b>%s</b>."
            ) % (self.name, date_terminated.strftime('%d/%m/%Y'), reason_label)
            self.lease_id.message_post(body=body_lease, subtype_xmlid='mail.mt_note')
        return True

    @api.model
    def get_lease_contracts_history(self, lease_id):
        """Retourne la liste des contrats précédents d'un bail (hors actif).

        Un contrat est considéré 'précédent' s'il est expiré, annulé, ou
        si un contrat plus récent existe pour le même bail.
        """
        # Contrat actif (le plus récent non annulé / non expiré)
        active = self.search([
            ('lease_id', '=', lease_id),
            ('state', 'not in', ('cancelled', 'expired')),
        ], order='id desc', limit=1)
        # Tous les autres contrats du bail
        domain = [('lease_id', '=', lease_id)]
        if active:
            domain.append(('id', '!=', active.id))
        history = self.search(domain, order='id desc')
        result = []
        for c in history:
            result.append({
                'id': c.id,
                'name': c.name,
                'state': c.state,
                'date_start': str(c.date_start) if c.date_start else False,
                'date_end': str(c.date_end) if c.date_end else False,
                'date_issued': str(c.date_issued) if c.date_issued else False,
                'signed_at_tenant': str(c.signed_at_tenant) if c.signed_at_tenant else False,
                'is_expired': c.is_expired,
                'date_terminated': str(c.date_terminated) if c.date_terminated else False,
                'termination_reason': c.termination_reason or False,
            })
        return result

    def render_html_preview(self):
        """Retourne un dict complet pour afficher l'aperçu HTML façon PDF."""
        self.ensure_one()
        company = self.company_id or self.env.company
        lease = self.lease_id
        tenant = lease.tenant_id
        prop = lease.property_id
        owner = lease.owner_id
        currency = lease.currency_id

        def fmt_money(amount):
            symbol = currency.name if currency else "FCFA"
            return "%s %s" % ("{:,.0f}".format(amount or 0).replace(",", " "), symbol)

        def fmt_date(d):
            if not d:
                return ""
            MONTHS_FR = ["janvier", "février", "mars", "avril", "mai", "juin",
                         "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
            return "%d %s %d" % (d.day, MONTHS_FR[d.month - 1], d.year)

        return {
            'id': self.id,
            'name': self.name,
            'state': self.state,
            'date_issued': fmt_date(self.date_issued or fields.Date.context_today(self)),
            'lease_type': self.lease_id.lease_type,
            'lease_type_label': dict(self.lease_id._fields['lease_type'].selection).get(self.lease_id.lease_type, ""),
            # Bailleur
            'company_name': company.name or "",
            'company_logo': (company.logo or b'').decode() if company.logo else "",
            'company_street': company.street or "",
            'company_city': company.city or "",
            'company_phone': company.phone or "",
            'company_email': company.email or "",
            'company_rccm': company.company_registry or "",
            # Locataire
            'tenant_name': tenant.name if tenant else "",
            'tenant_function': (tenant.function if tenant else "") or "",
            'tenant_phone': tenant.phone if tenant else "",
            'tenant_email': tenant.email if tenant else "",
            # Propriétaire
            'owner_name': owner.name if owner else "",
            # Bien
            'property_name': prop.name if prop else "",
            'property_city': prop.city if prop else "",
            'property_street': prop.street if prop else "",
            # Conditions financières
            'rent':    fmt_money(lease.rent),
            'charges': fmt_money(lease.charges),
            'deposit': fmt_money(lease.deposit),
            'total_monthly': fmt_money((lease.rent or 0) + (lease.charges or 0)),
            'date_start': fmt_date(lease.date_start),
            'date_end': fmt_date(lease.date_end) if lease.date_end else "Indéterminée",
            # Clauses interpolées
            'clauses': self._render_clauses(),
            # Signatures
            'sign_lessor': self.sign_lessor.decode() if self.sign_lessor else False,
            'signed_by_lessor': self.signed_by_lessor or "",
            'signed_at_lessor': str(self.signed_at_lessor) if self.signed_at_lessor else "",
            'sign_tenant': self.sign_tenant.decode() if self.sign_tenant else False,
            'signed_at_tenant': str(self.signed_at_tenant) if self.signed_at_tenant else "",
        }

    # ───────────────────────────────────────────────────────────────────
    # Actions workflow
    # ───────────────────────────────────────────────────────────────────
    def action_send_for_lessor_signature(self):
        """Passe l'état à 'pending_lessor' — le bailleur doit signer dans CIVORA."""
        for contract in self:
            if contract.state != 'draft':
                raise UserError("Seuls les contrats en brouillon peuvent être soumis à signature.")
            if not contract.clause_ids:
                raise UserError("Le contrat ne contient aucune clause. Ajoutez des articles avant de continuer.")
            contract.state = 'pending_lessor'

    def action_lessor_signed(self, sign_data_b64):
        """Enregistre la signature du bailleur et génère le token locataire."""
        self.ensure_one()
        if self.state not in ('draft', 'pending_lessor'):
            raise UserError("Ce contrat ne peut plus être signé par le bailleur.")
        token = uuid.uuid4().hex
        user = self.env.user
        # Snapshot période depuis le bail (elle pourrait changer après)
        self.write({
            'state': 'signed_lessor',
            'sign_lessor': sign_data_b64,
            'signed_at_lessor': fields.Datetime.now(),
            'signed_by_lessor': user.name,
            'token': token,
            'date_start': self.lease_id.date_start,
            'date_end': self.lease_id.date_end,
        })
        return token

    def action_cancel(self):
        for contract in self:
            if contract.state == 'signed_tenant':
                raise UserError("Un contrat déjà signé des deux parties ne peut pas être annulé ici.")
            contract.state = 'cancelled'

    def action_reset_draft(self):
        for contract in self:
            if contract.state in ('signed_lessor', 'signed_tenant'):
                raise UserError("Impossible de remettre en brouillon un contrat déjà signé.")
            contract.write({'state': 'draft', 'token': False})

    # ───────────────────────────────────────────────────────────────────
    # Génération PDF
    # ───────────────────────────────────────────────────────────────────
    def action_print_contract(self):
        self.ensure_one()
        return self.env.ref('civora_locations.action_report_lease_contract').report_action(self)

    # ───────────────────────────────────────────────────────────────────
    # RPC publique appelée par le portail locataire (inc. D)
    # ───────────────────────────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════
    # Envoi du lien de signature au locataire (email / SMS)
    # ══════════════════════════════════════════════════════════════════
    def _civora_sign_url(self):
        """URL publique de signature, construite depuis web.base.url.

        On n'utilise pas l'origine du navigateur : le lien part vers
        l'exterieur, il doit porter l'URL publique de l'instance meme si
        l'agent travaille derriere un proxy ou en local.
        """
        self.ensure_one()
        base = self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url', default='')
        return "%s/civora/contract/%s" % (base.rstrip('/'), self.token or '')

    @api.model
    def civora_link_channels(self, contract_id):
        """Disponibilite des canaux d'envoi, pour l'ecran agence.

        Permet de desactiver un bouton avec une raison explicite plutot que
        de laisser l'agent cliquer dans le vide.
        """
        c = self.browse(int(contract_id))
        if not c.exists():
            return {'email': {'ok': False, 'reason': "Contrat introuvable."},
                    'sms': {'ok': False, 'reason': "Contrat introuvable."}}

        tenant = c.lease_id.tenant_id
        company = c.company_id or self.env.company

        # ── Email
        email_ok, email_reason = True, ""
        if not (tenant.email or '').strip():
            email_ok, email_reason = False, "Ce locataire n'a pas d'adresse email."
        elif not (company.email or '').strip():
            email_ok, email_reason = False, (
                "La societe n'a pas d'adresse email : renseignez-la dans "
                "Parametres > Societes.")

        # ── SMS : dependance souple au module civora_sms
        Sms = self.env.get('civora.sms')
        sms_ok, sms_reason = True, ""
        if Sms is None:
            sms_ok, sms_reason = False, "Le module CIVORA SMS n'est pas installe."
        elif not (tenant.phone or '').strip():
            sms_ok, sms_reason = False, "Ce locataire n'a pas de numero de telephone."
        elif not company.civora_sms_is_ready():
            sms_ok, sms_reason = False, (
                "La passerelle SMS n'est pas activee ou pas configuree.")

        return {
            'email': {'ok': email_ok, 'reason': email_reason,
                      'target': tenant.email or ''},
            'sms': {'ok': sms_ok, 'reason': sms_reason,
                    'target': tenant.phone or ''},
        }

    @api.model
    def civora_send_link_email(self, contract_id):
        """Envoie le lien de signature par email au locataire."""
        c = self.browse(int(contract_id))
        if not c.exists():
            return {'success': False, 'error': "Contrat introuvable."}
        if c.state != 'signed_lessor':
            return {'success': False,
                    'error': "Ce contrat n'est pas en attente de signature locataire."}

        tenant = c.lease_id.tenant_id
        company = c.company_id or self.env.company
        target = (tenant.email or '').strip()
        sender = (company.email or '').strip()
        if not target:
            return {'success': False, 'error': "Ce locataire n'a pas d'adresse email."}
        if not sender:
            return {'success': False,
                    'error': "La societe n'a pas d'adresse email configuree."}

        url = c._civora_sign_url()
        prop = c.lease_id.property_id
        body = Markup(
            '<div style="margin:0;padding:24px 0;background:#f4f6fb;">'
            '<table role="presentation" cellpadding="0" cellspacing="0" border="0"'
            ' width="100%%" style="max-width:600px;margin:0 auto;background:#ffffff;'
            'border-radius:12px;overflow:hidden;font-family:Arial,Helvetica,sans-serif;">'
            '<tr><td style="height:4px;background:#00ab68;font-size:0;">&nbsp;</td></tr>'
            '<tr><td style="padding:30px 32px 8px;">'
            '<p style="margin:0 0 16px;font-size:15px;line-height:1.6;color:#1c2b45;">'
            'Bonjour %s,</p>'
            '<p style="margin:0 0 16px;font-size:15px;line-height:1.6;color:#1c2b45;">'
            'Votre contrat de bail <b>%s</b>%s est pret a etre signe. '
            'Vous pouvez le lire integralement, le telecharger, et signer '
            'en ligne depuis le lien ci-dessous.</p>'
            '<p style="margin:0 0 20px;font-size:14px;line-height:1.6;color:#6b7a94;">'
            'Si un article ne vous convient pas, vous pouvez deposer une '
            'remarque directement sur la page : notre equipe y repondra '
            'avant signature.</p>'
            '</td></tr>'
            '<tr><td align="center" style="padding:0 32px 28px;">'
            '<a href="%s" style="display:inline-block;background:#00ab68;color:#ffffff;'
            'text-decoration:none;border-radius:8px;padding:13px 30px;font-size:15px;'
            'font-weight:bold;">Consulter et signer mon contrat</a>'
            '<p style="margin:14px 0 0;font-size:12px;color:#94a3b8;word-break:break-all;">'
            '%s</p>'
            '</td></tr>'
            '<tr><td style="padding:16px 32px 26px;border-top:1px solid #e2e8f0;'
            'font-size:12px;line-height:1.6;color:#6b7a94;">'
            '<b style="color:#091a36;">%s</b>%s%s'
            '</td></tr></table></div>'
        ) % (
            tenant.name or "",
            c.name or "",
            (" (%s)" % prop.name) if prop and prop.name else "",
            url, url,
            company.name or "",
            Markup("<br/>%s") % company.phone if company.phone else "",
            Markup("<br/>%s") % company.email if company.email else "",
        )

        try:
            self.env['mail.mail'].sudo().create({
                'subject': "Votre contrat de bail %s est pret a signer" % (c.name or ""),
                'body_html': body,
                'email_from': sender,
                'email_to': target,
                'reply_to': sender,
                'auto_delete': False,
            }).send()
        except Exception as e:  # noqa: BLE001
            _logger.exception("CIVORA : echec envoi email du lien de signature")
            return {'success': False, 'error': "Echec de l'envoi : %s" % e}

        c.message_post(
            body=Markup("Lien de signature envoye par email a <b>%s</b>.") % target,
            subtype_xmlid='mail.mt_note',
        )
        return {'success': True, 'target': target}

    @api.model
    def civora_send_link_sms(self, contract_id):
        """Envoie le lien de signature par SMS au locataire.

        Le lien est raccourci : un lien de contrat complet fait ~75
        caracteres et fait basculer le message sur un second segment
        facture.
        """
        c = self.browse(int(contract_id))
        if not c.exists():
            return {'success': False, 'error': "Contrat introuvable."}
        if c.state != 'signed_lessor':
            return {'success': False,
                    'error': "Ce contrat n'est pas en attente de signature locataire."}

        Sms = self.env.get('civora.sms')
        if Sms is None:
            return {'success': False,
                    'error': "Le module CIVORA SMS n'est pas installe."}

        tenant = c.lease_id.tenant_id
        company = c.company_id or self.env.company
        phone = (tenant.phone or '').strip()
        if not phone:
            return {'success': False,
                    'error': "Ce locataire n'a pas de numero de telephone."}

        url = c._civora_sign_url()
        ShortLink = self.env.get('civora.short.link')
        if ShortLink is not None:
            url = ShortLink.sudo().civora_shorten(
                url, res_model=c._name, res_id=c.id, company=company)

        message = "%s: votre contrat de bail %s est pret a signer. %s" % (
            (company.civora_sms_sender_id or company.name or "CIVORA")[:20],
            c.name or "",
            url,
        )
        res = Sms.sudo().civora_send(
            phone, message, partner=tenant, record=c,
            company=company, immediate=True,
        )
        if not res.get('success'):
            return {'success': False, 'error': res.get('error') or "Echec de l'envoi."}

        c.message_post(
            body=Markup("Lien de signature envoye par SMS au <b>%s</b> "
                        "(%s segment(s)).") % (phone, res.get('segments') or 1),
            subtype_xmlid='mail.mt_note',
        )
        return {'success': True, 'target': phone, 'segments': res.get('segments')}

    # ═══════════════════════════════════════════════════════════════════
    @api.model
    def get_contract_by_token(self, token):
        """Retourne les données du contrat pour l'affichage public."""
        contract = self.sudo().search([('token', '=', token), ('state', '=', 'signed_lessor')], limit=1)
        if not contract:
            return False
        ctx = contract._build_context()
        return {
            'id': contract.id,
            'name': contract.name,
            'state': contract.state,
            'tenant_name': ctx.get('locataire'),
            'lessor_name': ctx.get('bailleur'),
            'property_name': ctx.get('bien'),
            'clauses': contract._render_clauses(),
            'sign_lessor': contract.sign_lessor.decode() if contract.sign_lessor else False,
            'signed_by_lessor': contract.signed_by_lessor,
            'signed_at_lessor': str(contract.signed_at_lessor) if contract.signed_at_lessor else False,
        }

    @api.model
    def tenant_sign(self, token, sign_data_b64):
        """Enregistre la signature locataire depuis le portail public."""
        contract = self.sudo().search([('token', '=', token), ('state', '=', 'signed_lessor')], limit=1)
        if not contract:
            return {'ok': False, 'error': 'Contrat introuvable ou déjà signé.'}
        contract.write({
            'state': 'signed_tenant',
            'sign_tenant': sign_data_b64,
            'signed_at_tenant': fields.Datetime.now(),
        })
        # Notifier le bailleur
        contract.message_post(
            body=Markup("✅ Le locataire <b>%s</b> a signé le contrat <b>%s</b>.")
                 % (contract.tenant_id.name, contract.name),
            subtype_xmlid='mail.mt_note',
        )
        return {'ok': True, 'contract_id': contract.id}
