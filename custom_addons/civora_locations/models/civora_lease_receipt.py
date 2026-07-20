# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError

MONTHS_FR = [
    "", "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]


def _amount_to_words_fr(n):
    """Convertit un entier en toutes lettres (francais), pour les quittances.
    Gere jusqu'aux milliards, suffisant pour des montants en FCFA."""
    n = int(round(n or 0))
    if n == 0:
        return "zéro"

    units = ["", "un", "deux", "trois", "quatre", "cinq", "six", "sept",
             "huit", "neuf", "dix", "onze", "douze", "treize", "quatorze",
             "quinze", "seize", "dix-sept", "dix-huit", "dix-neuf"]
    tens = ["", "", "vingt", "trente", "quarante", "cinquante", "soixante",
            "soixante", "quatre-vingt", "quatre-vingt"]

    def _below_100(x):
        if x < 20:
            return units[x]
        t, u = divmod(x, 10)
        if t in (7, 9):
            base = tens[t]
            rest = _below_100(10 + u)
            link = "-" if base else ""
            # 71 = soixante-et-onze ; 71..79 / 91..99
            if u == 1 and t == 7:
                return "soixante-et-" + units[11]
            return base + link + rest
        word = tens[t]
        if u == 0:
            # quatre-vingts (avec s) si exactement 80
            if t == 8:
                return "quatre-vingts"
            return word
        if u == 1 and t in (2, 3, 4, 5, 6):
            return word + "-et-un"
        return word + "-" + units[u]

    def _below_1000(x):
        if x == 0:
            return ""
        c, r = divmod(x, 100)
        out = ""
        if c:
            if c == 1:
                out = "cent"
            else:
                out = units[c] + " cent"
            # "cents" pluriel si multiple exact et > 1
            if r == 0 and c > 1:
                out += "s"
        if r:
            out = (out + " " + _below_100(r)).strip()
        return out

    parts = []
    milliards, reste = divmod(n, 1_000_000_000)
    millions, reste = divmod(reste, 1_000_000)
    milliers, unites = divmod(reste, 1000)

    if milliards:
        parts.append(_below_1000(milliards) + " milliard" + ("s" if milliards > 1 else ""))
    if millions:
        parts.append(_below_1000(millions) + " million" + ("s" if millions > 1 else ""))
    if milliers:
        if milliers == 1:
            parts.append("mille")
        else:
            # "quatre-vingts mille" -> "quatre-vingt mille" (s supprime devant mille)
            parts.append(_below_1000(milliers).replace("quatre-vingts", "quatre-vingt")
                         .replace("cents", "cent") + " mille"
                         if _below_1000(milliers).endswith(("quatre-vingts", "cents"))
                         else _below_1000(milliers) + " mille")
    if unites:
        parts.append(_below_1000(unites))

    return " ".join(p for p in parts if p).strip()


class CivoraLeaseReceipt(models.Model):
    """Quittance de loyer : atteste qu'un locataire a regle son loyer et ses
    charges pour une periode donnee. Peut etre generee depuis un paiement
    encaisse, ou manuellement pour une periode choisie."""
    _name = 'civora.lease.receipt'
    _description = "Quittance de loyer CIVORA"
    _order = 'period_year desc, period_month desc, id desc'
    _rec_name = 'name'

    name = fields.Char(string="N° de quittance", required=True, copy=False, index=True,
                       default=lambda self: self._default_name())
    lease_id = fields.Many2one(
        'civora.lease', string="Bail", required=True, ondelete='cascade', index=True,
    )
    payment_id = fields.Many2one(
        'civora.lease.payment', string="Paiement", ondelete='set null',
        help="Paiement encaissé à l'origine de cette quittance (le cas échéant).",
    )
    tenant_id = fields.Many2one(related='lease_id.tenant_id', string="Locataire", store=True, readonly=True)
    property_id = fields.Many2one(related='lease_id.property_id', string="Bien", store=True, readonly=True)
    owner_id = fields.Many2one(related='lease_id.owner_id', string="Propriétaire", store=True, readonly=True)

    period_month = fields.Integer(string="Mois", required=True, default=lambda self: fields.Date.context_today(self).month)
    period_year = fields.Integer(string="Année", required=True, default=lambda self: fields.Date.context_today(self).year)
    period_label = fields.Char(string="Période", compute='_compute_period_label', store=True)

    currency_id = fields.Many2one(related='lease_id.currency_id', string="Devise", store=True, readonly=True)
    rent = fields.Monetary(string="Loyer", currency_field='currency_id')
    charges = fields.Monetary(string="Charges", currency_field='currency_id')
    amount_total = fields.Monetary(string="Total", currency_field='currency_id', compute='_compute_total', store=True)
    amount_words = fields.Char(string="Montant en lettres", compute='_compute_amount_words')

    date_issued = fields.Date(string="Date d'émission", required=True, default=fields.Date.context_today)
    date_paid = fields.Date(string="Date de paiement")
    method = fields.Selection(
        [('virement', "Virement bancaire"), ('wave', "Wave"), ('orange_money', "Orange Money"),
         ('mtn_momo', "MTN MoMo"), ('cheque', "Chèque"), ('especes', "Espèces"), ('autre', "Autre")],
        string="Mode de paiement",
    )
    note = fields.Text(string="Mention particulière")
    company_id = fields.Many2one(related='lease_id.company_id', string="Société", store=True, index=True, readonly=True)

    @api.model
    def _default_name(self):
        seq = self.env['ir.sequence'].next_by_code('civora.lease.receipt')
        return seq or "/"

    @api.depends('period_month', 'period_year')
    def _compute_period_label(self):
        for rec in self:
            m = rec.period_month or 0
            month_name = MONTHS_FR[m] if 1 <= m <= 12 else ""
            rec.period_label = (month_name + " " + str(rec.period_year or "")).strip().capitalize()

    @api.depends('rent', 'charges')
    def _compute_total(self):
        for rec in self:
            rec.amount_total = (rec.rent or 0.0) + (rec.charges or 0.0)

    @api.depends('amount_total', 'currency_id')
    def _compute_amount_words(self):
        for rec in self:
            words = _amount_to_words_fr(rec.amount_total)
            unit = "francs CFA"
            rec.amount_words = (words + " " + unit).strip().capitalize()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == "/":
                vals['name'] = self._default_name()
        return super().create(vals_list)

    @api.constrains('period_month')
    def _check_month(self):
        for rec in self:
            if rec.period_month and (rec.period_month < 1 or rec.period_month > 12):
                raise ValidationError("Le mois doit être compris entre 1 et 12.")

    def action_print(self):
        self.ensure_one()
        return self.env.ref('civora_locations.action_report_lease_receipt').report_action(self)

    # --- API appelee depuis l'UI OWL -----------------------------------
    @api.model
    def create_from_payment(self, payment_id):
        """Genere une quittance a partir d'un paiement encaisse."""
        payment = self.env['civora.lease.payment'].browse(payment_id).exists()
        if not payment:
            raise ValidationError("Paiement introuvable.")
        lease = payment.lease_id
        d = payment.date or fields.Date.context_today(self)
        # Repartition loyer/charges : on privilegie les valeurs du bail, borne
        # au montant reellement encaisse.
        rent = min(lease.rent or 0.0, payment.amount or 0.0)
        charges = max(0.0, (payment.amount or 0.0) - rent)
        receipt = self.create([{
            'lease_id': lease.id,
            'payment_id': payment.id,
            'period_month': d.month,
            'period_year': d.year,
            'rent': rent,
            'charges': charges,
            'date_paid': payment.date,
            'method': payment.method,
        }])
        return receipt.id

    @api.model
    def create_for_period(self, lease_id, month, year):
        """Genere une quittance pour une periode choisie manuellement."""
        lease = self.env['civora.lease'].browse(lease_id).exists()
        if not lease:
            raise ValidationError("Bail introuvable.")
        receipt = self.create([{
            'lease_id': lease.id,
            'period_month': int(month),
            'period_year': int(year),
            'rent': lease.rent,
            'charges': lease.charges,
            'date_paid': False,
        }])
        return receipt.id
