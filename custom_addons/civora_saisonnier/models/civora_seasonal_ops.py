# -*- coding: utf-8 -*-
"""Operations saisonnieres CIVORA.

Ce fichier porte tout ce qui fait tourner une activite de location courte
duree au-dela de la reservation elle-meme : distribution multi-canaux,
messagerie voyageur, fichier voyageurs, services additionnels, incidents et
cautions, versements et reversements proprietaires, regles & frais, veille
tarifaire.

Chaque bloc de l'ecran Saisonnier s'appuie sur un vrai modele : rien n'est
ecrit en dur dans le front.
"""
from odoo import models, fields, api


# =====================================================================
#  DISTRIBUTION
# =====================================================================
class CivoraSeasonalChannel(models.Model):
    _name = "civora.seasonal.channel"
    _description = "Canal de distribution saisonnier"
    _order = "sequence, name"

    name = fields.Char(string="Canal", required=True)
    code = fields.Char(string="Code", required=True)
    emoji = fields.Char(string="Pictogramme", default="🌐")
    connected = fields.Boolean(string="Connecté", default=False)
    listing_count = fields.Integer(string="Annonces publiées")
    commission_rate = fields.Float(string="Commission (%)")
    last_sync_label = fields.Char(string="Dernière synchro", default="—")
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        "res.company", string="Société", default=lambda self: self.env.company)

    def action_toggle_connection(self):
        for rec in self:
            rec.connected = not rec.connected
            if not rec.connected:
                rec.listing_count = 0
                rec.last_sync_label = "—"
            else:
                rec.last_sync_label = "à l'instant"
        return True

    def action_sync(self):
        for rec in self.filtered("connected"):
            rec.last_sync_label = "à l'instant"
        return True


class CivoraSeasonalSyncState(models.Model):
    _name = "civora.seasonal.sync.state"
    _description = "État de synchronisation channel manager"
    _order = "sequence, id"

    name = fields.Char(string="Élément", required=True)
    percent = fields.Integer(string="Synchronisé (%)", default=100)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        "res.company", string="Société", default=lambda self: self.env.company)


class CivoraSeasonalConflict(models.Model):
    _name = "civora.seasonal.conflict"
    _description = "Conflit de synchronisation"
    _order = "id desc"

    name = fields.Char(string="Conflit", required=True)
    description = fields.Text(string="Détail")
    property_id = fields.Many2one("civora.property", string="Bien")
    resolved = fields.Boolean(string="Résolu")
    company_id = fields.Many2one(
        "res.company", string="Société", default=lambda self: self.env.company)

    def action_resolve(self):
        self.write({"resolved": True})
        return True


# =====================================================================
#  MESSAGERIE VOYAGEUR
# =====================================================================
class CivoraSeasonalGuest(models.Model):
    _name = "civora.seasonal.guest"
    _description = "Voyageur saisonnier"
    _order = "last_stay desc, id desc"

    name = fields.Char(string="Voyageur", required=True)
    partner_id = fields.Many2one("res.partner", string="Contact")
    email = fields.Char(string="Email")
    phone = fields.Char(string="Téléphone")
    country_code = fields.Char(string="Pays", default="CI")
    country_flag = fields.Char(string="Drapeau", default="🇨🇮")
    stay_count = fields.Integer(string="Séjours", default=0)
    night_count = fields.Integer(string="Nuits", default=0)
    total_spent = fields.Integer(string="Total dépensé (FCFA)", default=0)
    last_stay = fields.Date(string="Dernier séjour")
    rating = fields.Float(string="Note", default=0.0)
    tag = fields.Selection([
        ("vip", "VIP"),
        ("business", "Business"),
        ("famille", "Famille"),
        ("standard", "Standard"),
    ], string="Segment", default="standard")
    company_id = fields.Many2one(
        "res.company", string="Société", default=lambda self: self.env.company)

    def to_dict(self):
        self.ensure_one()
        return {
            "id": self.id,
            "name": self.name,
            "flag": self.country_flag or "",
            "country": self.country_code or "",
            "stays": self.stay_count,
            "nights": self.night_count,
            "total": self.total_spent,
            "last_stay": fields.Date.to_string(self.last_stay) if self.last_stay else "",
            "rating": self.rating,
            "tag": self.tag or "standard",
            "tag_label": dict(self._fields["tag"].selection).get(self.tag, ""),
            "email": self.email or "",
            "phone": self.phone or "",
        }


class CivoraSeasonalThread(models.Model):
    _name = "civora.seasonal.thread"
    _description = "Conversation voyageur"
    _order = "last_message_date desc, id desc"

    guest_id = fields.Many2one("civora.seasonal.guest", string="Voyageur", required=True)
    property_id = fields.Many2one("civora.property", string="Bien")
    reservation_id = fields.Many2one("civora.reservation", string="Réservation")
    channel = fields.Selection([
        ("airbnb", "Airbnb"),
        ("booking", "Booking"),
        ("direct", "Direct"),
        ("whatsapp", "WhatsApp"),
    ], string="Canal", default="direct", required=True)
    message_ids = fields.One2many("civora.seasonal.message", "thread_id", string="Messages")
    unread_count = fields.Integer(string="Non lus", compute="_compute_thread", store=True)
    last_message = fields.Char(string="Dernier message", compute="_compute_thread", store=True)
    last_message_date = fields.Datetime(string="Dernier échange", compute="_compute_thread", store=True)
    company_id = fields.Many2one(
        "res.company", string="Société", default=lambda self: self.env.company)

    @api.depends("message_ids", "message_ids.unread", "message_ids.message_date")
    def _compute_thread(self):
        for rec in self:
            msgs = rec.message_ids.sorted(lambda m: (m.message_date or fields.Datetime.now()))
            incoming = msgs.filtered(lambda m: m.direction == "in")
            rec.unread_count = len(incoming.filtered("unread"))
            rec.last_message = incoming[-1].body if incoming else (msgs[-1].body if msgs else "")
            rec.last_message_date = msgs[-1].message_date if msgs else False

    def action_mark_read(self):
        self.mapped("message_ids").filtered("unread").write({"unread": False})
        return True


class CivoraSeasonalMessage(models.Model):
    _name = "civora.seasonal.message"
    _description = "Message voyageur"
    _order = "message_date, id"

    thread_id = fields.Many2one(
        "civora.seasonal.thread", string="Conversation", required=True, ondelete="cascade")
    body = fields.Text(string="Message", required=True)
    direction = fields.Selection([
        ("in", "Reçu"),
        ("out", "Envoyé"),
    ], string="Sens", default="in", required=True)
    is_ai = fields.Boolean(string="Rédigé par l'IA")
    unread = fields.Boolean(string="Non lu", default=True)
    message_date = fields.Datetime(
        string="Date", default=lambda self: fields.Datetime.now(), required=True)
    company_id = fields.Many2one(
        "res.company", string="Société", related="thread_id.company_id", store=True)


class CivoraSeasonalReplyTemplate(models.Model):
    _name = "civora.seasonal.reply.template"
    _description = "Réponse rapide voyageur"
    _order = "sequence, id"

    name = fields.Char(string="Libellé", required=True)
    body = fields.Text(string="Contenu", required=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        "res.company", string="Société", default=lambda self: self.env.company)


# =====================================================================
#  SERVICES ADDITIONNELS
# =====================================================================
class CivoraSeasonalUpsell(models.Model):
    _name = "civora.seasonal.upsell"
    _description = "Service additionnel saisonnier"
    _order = "sequence, name"

    name = fields.Char(string="Service", required=True)
    price = fields.Integer(string="Prix (FCFA)")
    price_unit = fields.Char(string="Unité", default="")
    margin_pct = fields.Integer(string="Marge (%)")
    sales_count = fields.Integer(string="Ventes", default=0)
    revenue = fields.Integer(string="Revenus (FCFA)", compute="_compute_revenue", store=True)
    is_active = fields.Boolean(string="Actif", default=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        "res.company", string="Société", default=lambda self: self.env.company)

    @api.depends("price", "sales_count")
    def _compute_revenue(self):
        for rec in self:
            rec.revenue = rec.price * rec.sales_count

    def action_toggle_active(self):
        for rec in self:
            rec.is_active = not rec.is_active
        return True


class CivoraSeasonalUpsellLine(models.Model):
    """Service additionnel effectivement vendu sur un sejour.

    `sales_count` sur le service porte le cumul depuis la mise en service
    (reprise de donnees incluse) ; les lignes portent le detail par sejour
    et c'est d'elles que se deduit l'attach rate.
    """

    _name = "civora.seasonal.upsell.line"
    _description = "Vente de service additionnel"
    _order = "id desc"

    upsell_id = fields.Many2one(
        "civora.seasonal.upsell", string="Service", required=True, ondelete="cascade")
    reservation_id = fields.Many2one(
        "civora.reservation", string="Réservation", required=True, ondelete="cascade")
    quantity = fields.Integer(string="Quantité", default=1)
    amount = fields.Integer(string="Montant (FCFA)", compute="_compute_amount", store=True)
    company_id = fields.Many2one(
        "res.company", string="Société", default=lambda self: self.env.company)

    @api.depends("upsell_id.price", "quantity")
    def _compute_amount(self):
        for rec in self:
            rec.amount = (rec.upsell_id.price or 0) * (rec.quantity or 0)


# =====================================================================
#  INCIDENTS & CAUTIONS
# =====================================================================
class CivoraSeasonalIncident(models.Model):
    _name = "civora.seasonal.incident"
    _description = "Incident de séjour"
    _order = "incident_date desc, id desc"

    name = fields.Char(string="Référence", readonly=True, copy=False, default="/")
    property_id = fields.Many2one("civora.property", string="Bien", required=True)
    guest_id = fields.Many2one("civora.seasonal.guest", string="Voyageur")
    reservation_id = fields.Many2one("civora.reservation", string="Réservation")
    incident_date = fields.Date(string="Date", default=fields.Date.context_today, required=True)
    incident_type = fields.Selection([
        ("casse", "Casse"),
        ("depassement", "Dépassement occupants"),
        ("nuisances", "Nuisances"),
        ("fumee", "Fumée intérieur"),
        ("degat", "Dégât matériel"),
        ("autre", "Autre"),
    ], string="Type", required=True, default="casse")
    description = fields.Char(string="Description")
    amount = fields.Integer(string="Montant (FCFA)")
    severity = fields.Selection([
        ("faible", "Faible"),
        ("moyenne", "Moyenne"),
        ("haute", "Haute"),
    ], string="Sévérité", default="faible", required=True)
    state = fields.Selection([
        ("ouvert", "Ouvert"),
        ("averti", "Averti"),
        ("facture", "Facturé"),
        ("caution", "Caution retenue"),
        ("assurance", "Assurance"),
        ("resolu", "Résolu"),
    ], string="Statut", default="ouvert", required=True)
    company_id = fields.Many2one(
        "res.company", string="Société", default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "civora.seasonal.incident") or "/"
        return super().create(vals_list)


class CivoraSeasonalInsurance(models.Model):
    _name = "civora.seasonal.insurance"
    _description = "Couverture assurance saisonnier"

    name = fields.Char(string="Contrat", required=True, default="Assurance dommages")
    coverage = fields.Integer(string="Plafond de couverture (FCFA)", default=3000000)
    franchise = fields.Integer(string="Franchise (FCFA)", default=25000)
    is_active = fields.Boolean(string="Active", default=True)
    company_id = fields.Many2one(
        "res.company", string="Société", default=lambda self: self.env.company)


# =====================================================================
#  PAIEMENTS & REVENUS
# =====================================================================
class CivoraSeasonalPayout(models.Model):
    _name = "civora.seasonal.payout"
    _description = "Versement channel"
    _order = "payout_date desc, id desc"

    payout_date = fields.Date(string="Date", required=True, default=fields.Date.context_today)
    channel_id = fields.Many2one("civora.seasonal.channel", string="Canal", required=True)
    reference = fields.Char(string="Référence", required=True)
    gross_amount = fields.Integer(string="Brut (FCFA)")
    commission_amount = fields.Integer(string="Commission (FCFA)")
    net_amount = fields.Integer(string="Net (FCFA)", compute="_compute_net", store=True)
    state = fields.Selection([
        ("attente", "En attente"),
        ("verse", "Versé"),
    ], string="Statut", default="attente", required=True)
    company_id = fields.Many2one(
        "res.company", string="Société", default=lambda self: self.env.company)

    @api.depends("gross_amount", "commission_amount")
    def _compute_net(self):
        for rec in self:
            rec.net_amount = rec.gross_amount - rec.commission_amount

    def action_mark_paid(self):
        self.write({"state": "verse"})
        return True


class CivoraSeasonalOwnerStatement(models.Model):
    _name = "civora.seasonal.owner.statement"
    _description = "Relevé propriétaire saisonnier"
    _order = "id"

    name = fields.Char(string="Propriétaire", required=True)
    partner_id = fields.Many2one("res.partner", string="Contact propriétaire")
    property_id = fields.Many2one("civora.property", string="Bien")
    gross_amount = fields.Integer(string="Brut (FCFA)")
    channel_commission = fields.Integer(string="Commissions canaux (FCFA)")
    management_rate = fields.Float(string="Honoraires de gestion (%)", default=20.0)
    management_fee = fields.Integer(
        string="Honoraires (FCFA)", compute="_compute_amounts", store=True)
    net_amount = fields.Integer(
        string="Net à reverser (FCFA)", compute="_compute_amounts", store=True)
    sent = fields.Boolean(string="Relevé envoyé")
    company_id = fields.Many2one(
        "res.company", string="Société", default=lambda self: self.env.company)

    @api.depends("gross_amount", "channel_commission", "management_rate")
    def _compute_amounts(self):
        for rec in self:
            rec.management_fee = int(round(rec.gross_amount * rec.management_rate / 100.0))
            rec.net_amount = rec.gross_amount - rec.channel_commission - rec.management_fee

    def action_send_statement(self):
        self.write({"sent": True})
        return True


# =====================================================================
#  REGLES & FRAIS
# =====================================================================
class CivoraSeasonalRule(models.Model):
    _name = "civora.seasonal.rule"
    _description = "Règles de réservation saisonnière"

    name = fields.Char(string="Jeu de règles", default="Règles par défaut", required=True)
    min_nights = fields.Integer(string="Séjour minimum (nuits)", default=2)
    max_nights = fields.Integer(string="Séjour maximum (nuits)", default=30)
    notice_label = fields.Char(string="Préavis de réservation", default="Same-day OK")
    free_cancel_hours = fields.Integer(string="Annulation gratuite (h avant arrivée)", default=48)
    checkin_from = fields.Char(string="Check-in à partir de", default="14:00")
    checkin_to = fields.Char(string="Check-in jusqu'à", default="22:00")
    checkout_before = fields.Char(string="Check-out avant", default="11:00")
    children_allowed = fields.Boolean(string="Enfants acceptés", default=True)
    pets_policy = fields.Selection([
        ("oui", "Oui"),
        ("demande", "Sur demande"),
        ("non", "Non"),
    ], string="Animaux", default="demande")
    parties_allowed = fields.Boolean(string="Fêtes / événements autorisés", default=False)
    registration_number = fields.Char(string="N° enregistrement meublé")
    declaration_status = fields.Char(string="Déclaration trimestrielle", default="À jour")
    insurance_status = fields.Char(string="Assurance multi-risques", default="Active")
    fee_ids = fields.One2many("civora.seasonal.fee", "rule_id", string="Frais additionnels")
    auto_message_ids = fields.One2many(
        "civora.seasonal.auto.message", "rule_id", string="Messages automatiques")
    company_id = fields.Many2one(
        "res.company", string="Société", default=lambda self: self.env.company)


class CivoraSeasonalFee(models.Model):
    _name = "civora.seasonal.fee"
    _description = "Frais additionnel saisonnier"
    _order = "sequence, id"

    rule_id = fields.Many2one("civora.seasonal.rule", string="Jeu de règles", ondelete="cascade")
    name = fields.Char(string="Frais", required=True)
    amount_label = fields.Char(string="Montant", required=True)
    is_auto = fields.Boolean(string="Appliqué automatiquement")
    sequence = fields.Integer(default=10)


class CivoraSeasonalAutoMessage(models.Model):
    _name = "civora.seasonal.auto.message"
    _description = "Message automatique saisonnier"
    _order = "sequence, id"

    rule_id = fields.Many2one("civora.seasonal.rule", string="Jeu de règles", ondelete="cascade")
    name = fields.Char(string="Message", required=True)
    is_active = fields.Boolean(string="Actif", default=True)
    sequence = fields.Integer(default=10)

    def action_toggle(self):
        for rec in self:
            rec.is_active = not rec.is_active
        return True


# =====================================================================
#  VEILLE TARIFAIRE & DEMANDE
# =====================================================================
class CivoraSeasonalCompetitor(models.Model):
    _name = "civora.seasonal.competitor"
    _description = "Concurrent (rate shopper)"
    _order = "is_self, distance_km"

    name = fields.Char(string="Établissement", required=True)
    distance_km = fields.Float(string="Distance (km)")
    rating = fields.Float(string="Note")
    occupancy = fields.Integer(string="Occupation (%)")
    price_night = fields.Integer(string="Tarif nuit (FCFA)")
    trend_7d = fields.Integer(string="Tendance 7j (%)")
    is_self = fields.Boolean(string="C'est nous")
    company_id = fields.Many2one(
        "res.company", string="Société", default=lambda self: self.env.company)


class CivoraSeasonalDemandPace(models.Model):
    _name = "civora.seasonal.demand.pace"
    _description = "Pace de demande"
    _order = "sequence, id"

    name = fields.Char(string="Période", required=True)
    percent = fields.Integer(string="Rythme de réservation (%)")
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        "res.company", string="Société", default=lambda self: self.env.company)


class CivoraSeasonalEvent(models.Model):
    _name = "civora.seasonal.event"
    _description = "Événement local"
    _order = "sequence, id"

    name = fields.Char(string="Événement", required=True)
    period_label = fields.Char(string="Période")
    impact_label = fields.Char(string="Impact estimé")
    is_hot = fields.Boolean(string="Forte demande")
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        "res.company", string="Société", default=lambda self: self.env.company)


# =====================================================================
#  BOOKING ENGINE
# =====================================================================
class CivoraSeasonalFunnelStep(models.Model):
    _name = "civora.seasonal.funnel.step"
    _description = "Étape du funnel de réservation directe"
    _order = "sequence, id"

    name = fields.Char(string="Étape", required=True)
    visitors = fields.Integer(string="Volume")
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        "res.company", string="Société", default=lambda self: self.env.company)


class CivoraSeasonalBookingEntry(models.Model):
    _name = "civora.seasonal.booking.entry"
    _description = "Point d'entrée booking engine"
    _order = "sequence, id"

    name = fields.Char(string="Point d'entrée", required=True)
    entry_type = fields.Selection([
        ("search", "Search bar"),
        ("property", "Property page"),
        ("campaign", "Campaign"),
    ], string="Type", default="property")
    sessions = fields.Integer(string="Sessions")
    conversion = fields.Float(string="Conversion (%)")
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        "res.company", string="Société", default=lambda self: self.env.company)


class CivoraSeasonalBookingConfig(models.Model):
    _name = "civora.seasonal.booking.config"
    _description = "Configuration du moteur de réservation"

    name = fields.Char(string="Moteur", default="Moteur de réservation", required=True)
    domain = fields.Char(string="Domaine réservation", default="book.civora.ci")
    payment_methods = fields.Char(string="Paiement", default="Stripe · MTN · Orange")
    languages = fields.Char(string="Multilingue", default="FR · EN · ES")
    embed_snippet = fields.Text(string="Snippet d'intégration")
    company_id = fields.Many2one(
        "res.company", string="Société", default=lambda self: self.env.company)


# =====================================================================
#  GUEST JOURNEY
# =====================================================================
class CivoraSeasonalJourneyStep(models.Model):
    _name = "civora.seasonal.journey.step"
    _description = "Étape du parcours voyageur"
    _order = "sequence, id"

    name = fields.Char(string="Étape", required=True)
    offset_label = fields.Char(string="Décalage", default="T+0")
    sequence = fields.Integer(default=10)
    action_ids = fields.One2many(
        "civora.seasonal.journey.action", "step_id", string="Actions")
    company_id = fields.Many2one(
        "res.company", string="Société", default=lambda self: self.env.company)


class CivoraSeasonalJourneyAction(models.Model):
    _name = "civora.seasonal.journey.action"
    _description = "Action du parcours voyageur"
    _order = "sequence, id"

    step_id = fields.Many2one(
        "civora.seasonal.journey.step", string="Étape", required=True, ondelete="cascade")
    channel = fields.Selection([
        ("email", "Email"),
        ("sms", "SMS"),
        ("whatsapp", "WhatsApp"),
        ("upsell", "Upsell"),
    ], string="Canal", default="email", required=True)
    name = fields.Char(string="Contenu", required=True)
    is_ai = fields.Boolean(string="Généré par l'IA")
    sequence = fields.Integer(default=10)
