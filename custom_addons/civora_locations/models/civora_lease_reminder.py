# -*- coding: utf-8 -*-
import logging
from datetime import timedelta

from markupsafe import Markup

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


CIVORA_REMINDER_CHANNEL = [
    ('email', "Email"),
    ('whatsapp', "WhatsApp"),
    ('sms', "SMS"),
    ('phone', "Appel téléphonique"),
    ('letter', "Courrier postal"),
]

CIVORA_REMINDER_SEVERITY = [
    ('soft', "Léger (1-15j)"),
    ('moderate', "Modéré (15-30j)"),
    ('firm', "Ferme (30j+)"),
    ('legal', "Mise en demeure"),
]

CIVORA_REMINDER_STATE = [
    ('draft', "Brouillon"),
    ('sent', "Envoyée"),
    ('cancelled', "Annulée"),
]


class CivoraLeaseReminder(models.Model):
    """Relance locative : trace d'une communication de relance pour impayé.

    Modèle purement de tracing pour l'instant : la relance est préparée par
    l'agent, éventuellement envoyée hors application, puis marquée comme
    envoyée. L'envoi réel (email/WhatsApp) sera branché dans un increment
    ultérieur avec les crons automatiques.
    """
    _name = 'civora.lease.reminder'
    _description = "Relance locative CIVORA"
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'
    _rec_name = 'name'
    _check_company_auto = True

    name = fields.Char(
        string="Référence",
        copy=False, index=True, tracking=True,
        default=lambda self: self._default_name(),
    )
    lease_id = fields.Many2one(
        'civora.lease', string="Bail",
        required=True, index=True, ondelete='cascade', tracking=True,
    )
    tenant_id = fields.Many2one(
        'res.partner', string="Locataire",
        related='lease_id.tenant_id', store=True, readonly=True,
    )
    property_id = fields.Many2one(
        'civora.property', string="Bien",
        related='lease_id.property_id', store=True, readonly=True,
    )
    company_id = fields.Many2one(
        'res.company', string="Société",
        related='lease_id.company_id', store=True, readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency', string="Devise",
        related='lease_id.currency_id', readonly=True,
    )

    date = fields.Date(
        string="Date de relance",
        default=fields.Date.context_today, required=True, tracking=True,
    )
    channel = fields.Selection(
        CIVORA_REMINDER_CHANNEL, string="Canal",
        default='email', required=True, tracking=True,
    )
    severity = fields.Selection(
        CIVORA_REMINDER_SEVERITY, string="Sévérité",
        default='soft', required=True, tracking=True,
    )
    arrears_amount = fields.Monetary(
        string="Impayés au moment de la relance",
        currency_field='currency_id',
        help="Montant total impayé au moment où la relance a été préparée.",
    )
    arrears_days = fields.Integer(
        string="Jours de retard max",
        help="Nombre de jours de retard de la plus ancienne échéance impayée.",
    )
    subject = fields.Char(string="Sujet", required=True, tracking=True)
    body = fields.Text(string="Corps du message")
    sent_by = fields.Many2one(
        'res.users', string="Envoyée par",
        default=lambda self: self.env.user, tracking=True,
    )
    state = fields.Selection(
        CIVORA_REMINDER_STATE, string="Statut",
        default='draft', required=True, tracking=True,
    )
    installment_ids = fields.Many2many(
        'civora.lease.installment', 'civora_reminder_installment_rel',
        'reminder_id', 'installment_id',
        string="Échéances concernées",
    )
    mail_message_id = fields.Many2one(
        'mail.mail', string="Email envoyé",
        readonly=True, ondelete='set null',
        help="Référence de l'email envoyé (canal email uniquement).",
    )

    @api.model
    def _default_name(self):
        seq = self.env['ir.sequence'].next_by_code('civora.lease.reminder')
        return seq or "/"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == "/":
                vals['name'] = self._default_name()
        return super().create(vals_list)

    # ═══════════════════════════════════════════════════════════════════
    # Modeles de message — source unique
    # ═══════════════════════════════════════════════════════════════════
    # Ces modeles vivaient en dur dans reminder_drawer.js, signes
    # "L'equipe CIVORA". Sur un produit en marque blanche, un locataire
    # doit lire le nom de SON agence : CIVORA est l'editeur, pas le
    # bailleur. Ils sont donc remontes ici, ou le nom de societe est
    # disponible, et l'ecran les consomme via civora_get_templates().
    SUBJECT_TEMPLATES = {
        'soft': "Rappel amiable : loyer {periods} en attente",
        'moderate': "Relance : régularisation loyer {periods} — {days} jours de retard",
        'firm': "Relance ferme : loyer {periods} impayé depuis {days} jours",
        'legal': "Mise en demeure : impayé locatif ({periods}, {days} jours de retard)",
    }

    BODY_TEMPLATES = {
        'soft':
            "Bonjour {tenant},\n\n"
            "Nous constatons que votre loyer pour la période {periods} présente "
            "un retard de paiement de {days} jour(s), pour un montant de {amount}. "
            "Il s'agit sans doute d'un simple oubli — nous vous invitons à "
            "régulariser votre situation dès que possible.\n\n"
            "Cordialement,\n{company}",
        'moderate':
            "Bonjour {tenant},\n\n"
            "Malgré notre précédent rappel, votre loyer pour {periods} reste "
            "impayé ({days} jour(s) de retard), soit {amount} restant dû. "
            "Merci de bien vouloir procéder à la régularisation sous 7 jours ou "
            "de nous contacter pour convenir d'un échéancier.\n\n"
            "Cordialement,\n{company}",
        'firm':
            "Bonjour {tenant},\n\n"
            "Votre situation locative présente un retard significatif de "
            "{days} jour(s) sur la période {periods}, pour un montant de {amount}. "
            "Nous vous demandons de régulariser sans délai, sous peine "
            "d'ouverture d'une procédure formelle.\n\n"
            "Cordialement,\n{company}",
        'legal':
            "Objet : MISE EN DEMEURE\n\n"
            "Madame, Monsieur {tenant},\n\n"
            "Nous vous mettons formellement en demeure de régler la somme de "
            "{amount} due au titre de votre loyer pour la période {periods}, "
            "en retard de {days} jour(s), dans un délai de {delay} jours à "
            "compter de la réception de la présente.\n\n"
            "À défaut de règlement dans ce délai, nous serons contraints "
            "d'engager les procédures de recouvrement prévues par la loi.\n\n"
            "{company}",
    }

    # Delai legal de regularisation accorde par une mise en demeure.
    FORMAL_NOTICE_DELAY_DAYS = 15

    # Temporisation entre deux relances d'un meme bail, cote detection
    # automatique. Relancer tous les jours ne fait pas payer plus vite,
    # ca fait changer d'agence.
    COOLDOWN_DAYS = 7

    @api.model
    def _template_context(self, lease, installments=None):
        """Valeurs de substitution des modeles, pour un bail donne."""
        today = fields.Date.context_today(self)
        insts = installments if installments is not None else lease.installment_ids.filtered(
            lambda i: i.state in ('overdue', 'partial')
            and i.due_date and i.due_date < today
        ).sorted('due_date')

        amount = sum(i.amount_remaining or 0.0 for i in insts)
        days = (today - insts[0].due_date).days if insts and insts[0].due_date else 0
        periods = ", ".join(i.period_label or "" for i in insts) or "en cours"
        currency = lease.currency_id

        return {
            'tenant': (lease.tenant_id.name or "") if lease.tenant_id else "",
            'company': (lease.company_id.name or "Votre agence") if lease.company_id else "Votre agence",
            'property': (lease.property_id.name or "") if lease.property_id else "",
            'periods': periods,
            'days': days,
            'amount': ("%s %s" % ('{:,.0f}'.format(amount).replace(',', ' '),
                                  currency.name if currency else "")).strip(),
            'amount_raw': amount,
            'delay': self.FORMAL_NOTICE_DELAY_DAYS,
            'installments': insts,
        }

    @api.model
    def civora_get_templates(self, lease_id):
        """Retourne les modeles rendus pour chaque severite.

        Consomme par le drawer OWL : l'ecran n'a plus de texte en dur.
        """
        lease = self.env['civora.lease'].browse(int(lease_id))
        if not lease.exists():
            return {}
        ctx = self._template_context(lease)
        fmt = {k: v for k, v in ctx.items() if k != 'installments'}
        out = {}
        for sev in self.SUBJECT_TEMPLATES:
            out[sev] = {
                'subject': self.SUBJECT_TEMPLATES[sev].format(**fmt),
                'body': self.BODY_TEMPLATES[sev].format(**fmt),
            }
        out['_context'] = fmt
        return out

    @api.model
    def check_email_prerequisites(self, lease_id):
        """Vérifie que les prérequis d'envoi email sont réunis pour un bail.
        Utilisé par le drawer OWL pour afficher un aperçu et prévenir avant envoi.

        Retourne :
        - ok (bool)
        - company_email (str|False)
        - tenant_email (str|False)
        - tenant_name (str|False)
        - errors (list[str]) : messages d'erreur explicites
        """
        lease = self.env['civora.lease'].browse(lease_id)
        errors = []
        company_email = (lease.company_id.email or "").strip() if lease.company_id else ""
        tenant_email = ""
        tenant_name = ""
        if lease.tenant_id:
            tenant_email = (lease.tenant_id.email or "").strip()
            tenant_name = lease.tenant_id.name or ""
        if not company_email:
            errors.append(
                "L'email de votre société n'est pas configuré. "
                "Ajoutez-le dans Paramètres > Sociétés."
            )
        if not tenant_email:
            errors.append(
                "Le locataire n'a pas d'adresse email. "
                "Ajoutez-la dans sa fiche contact."
            )
        return {
            'ok': not errors,
            'company_email': company_email,
            'tenant_email': tenant_email,
            'tenant_name': tenant_name,
            'errors': errors,
        }

    def _send_email_notification(self):
        """Construit et envoie l'email de relance via mail.mail.
        Retourne le mail.mail créé.

        Odoo utilise automatiquement l'ir.mail_server (courrier sortant)
        configuré au niveau système. Si aucun serveur n'est configuré,
        l'email restera en état 'outgoing' jusqu'à envoi manuel.
        """
        self.ensure_one()
        from odoo.exceptions import UserError
        lease = self.lease_id
        if not lease:
            raise UserError("Le bail associé est introuvable.")

        company_email = (lease.company_id.email or "").strip() if lease.company_id else ""
        if not company_email:
            raise UserError(
                "L'email de la société n'est pas configuré. "
                "Ajoutez-le dans Paramètres > Sociétés avant d'envoyer."
            )
        tenant = lease.tenant_id
        if not tenant or not (tenant.email or "").strip():
            raise UserError(
                "Le locataire n'a pas d'adresse email. "
                "Ajoutez-la dans sa fiche contact avant d'envoyer."
            )

        # Conversion du corps texte en HTML minimal (préservation des sauts de ligne)
        body_html = "<div style=\"font-family:Arial,sans-serif;font-size:14px;line-height:1.5;color:#0f1e36;\">"
        body_html += (self.body or "").replace("\n", "<br/>")
        body_html += "</div>"

        # Nom d'expéditeur : "NomSociete <email@domaine>"
        company_name = lease.company_id.name or "CIVORA"
        email_from = f"{company_name} <{company_email}>"

        mail_values = {
            'subject': self.subject or "Relance CIVORA",
            'body_html': body_html,
            'email_from': email_from,
            'email_to': tenant.email,
            'reply_to': company_email,
            'author_id': self.env.user.partner_id.id,
            'recipient_ids': [(6, 0, [tenant.id])],
            'model': 'civora.lease.reminder',
            'res_id': self.id,
        }
        mail = self.env['mail.mail'].sudo().create(mail_values)
        # Envoi immédiat (raise_exception=False → si SMTP down, reste en outgoing)
        mail.send(raise_exception=False)
        self.mail_message_id = mail.id
        return mail

    def _send_sms_notification(self):
        """Envoie la relance par SMS via la passerelle CIVORA.

        Dependance SOUPLE a civora_sms : le module doit pouvoir s'installer
        et fonctionner sans la passerelle. Meme pattern que
        civora_lease_contract.civora_send_link_sms().

        Retourne un dict {success, error, segments} — jamais d'exception
        reseau ne remonte jusqu'a l'ecran.
        """
        self.ensure_one()
        lease = self.lease_id
        Sms = self.env.get('civora.sms')
        if Sms is None:
            return {'success': False,
                    'error': "Le module SMS n'est pas installé."}

        company = lease.company_id or self.env.company
        if not company.civora_sms_is_ready():
            return {'success': False,
                    'error': "La passerelle SMS n'est pas configurée pour « %s »."
                             % (company.name or "cette société")}

        tenant = lease.tenant_id
        phone = (tenant.phone or "").strip() if tenant else ""
        if not phone:
            return {'success': False,
                    'error': "Le locataire n'a pas de numéro de téléphone."}

        # Le corps est deja redige par le gestionnaire ou le modele de
        # relance. On le tronque a 3 segments : au-dela, un SMS de relance
        # n'est plus lu et coute cher.
        text = (self.body or self.subject or "").strip()
        if len(text) > 450:
            text = text[:447] + "..."

        res = Sms.sudo().civora_send(
            phone, text, partner=tenant, record=lease,
            company=company, immediate=True,
        )
        return {
            'success': bool(res.get('success')),
            'error': res.get('error'),
            'segments': res.get('segments') or 1,
            'target': phone,
        }

    def action_mark_sent(self):
        """Marque la relance comme envoyée.

        Pour le canal 'email' : envoie réellement l'email via mail.mail
        (utilise l'ir.mail_server configuré au niveau système).
        Pour les autres canaux (WhatsApp/SMS/téléphone/courrier) : trace
        simplement l'action dans le chatter du bail.
        """
        channel_labels = dict(CIVORA_REMINDER_CHANNEL)
        severity_labels = dict(CIVORA_REMINDER_SEVERITY)
        for rem in self:
            email_sent_msg = ""
            if rem.channel == 'sms':
                res = rem._send_sms_notification()
                if res.get('success'):
                    email_sent_msg = Markup(" · <b>SMS envoyé</b> (%s segment(s))") % (
                        res.get('segments') or 1)
                else:
                    email_sent_msg = Markup(" · <b style='color:#e53e3e'>Échec SMS</b> : %s") % (
                        res.get('error') or "erreur inconnue")
            elif rem.channel == 'email':
                mail = rem._send_email_notification()
                if mail.state == 'sent':
                    email_sent_msg = Markup(" · <b>Email envoyé</b>")
                elif mail.state == 'outgoing':
                    email_sent_msg = Markup(" · <b>Email en file d'attente</b>")
                elif mail.state == 'exception':
                    email_sent_msg = Markup(" · <b style='color:#e53e3e'>Erreur d'envoi</b>")
                    # On garde quand même le statut 'sent' côté reminder,
                    # l'utilisateur peut renvoyer depuis Paramètres > Emails
            rem.state = 'sent'
            if rem.lease_id:
                rem.lease_id.message_post(
                    body=Markup("Relance envoyée : <b>%s</b> · Canal : %s "
                                "· Sévérité : %s%s") % (
                        rem.subject or "—",
                        channel_labels.get(rem.channel, rem.channel),
                        severity_labels.get(rem.severity, rem.severity),
                        email_sent_msg,
                    ),
                    subject="Relance envoyée",
                )
        return True

    # ═══════════════════════════════════════════════════════════════════
    # Detection automatique — file a valider
    # ═══════════════════════════════════════════════════════════════════
    # Choix assume : le cron ne DECLENCHE JAMAIS d'envoi. Il prepare des
    # relances en brouillon qu'un gestionnaire valide. Un SMS parti tout
    # seul chez un bon client qui a paye la veille coute plus cher a
    # l'agence que le loyer concerne — et ce genre d'incident ne se
    # decouvre qu'apres, en clientele.
    @api.model
    def _cron_detect_arrears(self):
        """Prepare une relance brouillon par bail nouvellement en retard.

        Deux garde-fous :
        - un bail deja porteur d'une relance en brouillon est ignore (sinon
          la file se remplit d'un doublon par jour) ;
        - un bail relance dans les 7 derniers jours est ignore (le temps de
          laisser le paiement arriver).
        """
        Lease = self.env['civora.lease']
        today = fields.Date.context_today(self)
        rows = Lease.get_arrears_portfolio()
        if not rows:
            return True

        lease_ids = [r['lease_id'] for r in rows]

        pending = set(self.search([
            ('lease_id', 'in', lease_ids),
            ('state', '=', 'draft'),
        ]).mapped('lease_id').ids)

        recent = set(self.search([
            ('lease_id', 'in', lease_ids),
            ('state', '=', 'sent'),
            ('date', '>=', today - timedelta(days=self.COOLDOWN_DAYS)),
        ]).mapped('lease_id').ids)

        created = 0
        for row in rows:
            lid = row['lease_id']
            if lid in pending or lid in recent:
                continue
            lease = Lease.browse(lid)
            try:
                ctx = self._template_context(lease)
                if not ctx['installments']:
                    continue
                fmt = {k: v for k, v in ctx.items() if k != 'installments'}
                sev = row['severity']
                # Le canal par defaut suit ce dont on dispose reellement.
                tenant = lease.tenant_id
                channel = 'email' if (tenant and (tenant.email or '').strip()) else (
                    'sms' if (tenant and (tenant.phone or '').strip()) else 'phone')
                self.create({
                    'lease_id': lid,
                    'channel': channel,
                    'severity': sev,
                    'subject': self.SUBJECT_TEMPLATES[sev].format(**fmt),
                    'body': self.BODY_TEMPLATES[sev].format(**fmt),
                    'arrears_amount': ctx['amount_raw'],
                    'arrears_days': ctx['days'],
                    'installment_ids': [(6, 0, [i.id for i in ctx['installments']])],
                    'state': 'draft',
                })
                created += 1
            except Exception as e:
                _logger.warning(
                    "CIVORA detection impayes — echec sur le bail %s : %s",
                    lease.name or lid, e)

        if created:
            _logger.info("CIVORA : %d relance(s) preparee(s) en brouillon.", created)
        return True

    @api.model
    def civora_get_pending_queue(self):
        """Relances en attente de validation, pour le bandeau de l'ecran."""
        drafts = self.search([('state', '=', 'draft')], order='arrears_days desc')
        return [{
            'id': r.id,
            'lease_id': r.lease_id.id,
            'lease_ref': r.lease_id.name or "—",
            'tenant_name': (r.tenant_id.name or "—") if r.tenant_id else "—",
            'channel': r.channel,
            'severity': r.severity,
            'subject': r.subject or "",
            'amount': r.arrears_amount or 0.0,
            'days': r.arrears_days or 0,
        } for r in drafts]

    # ═══════════════════════════════════════════════════════════════════
    # Mise en demeure
    # ═══════════════════════════════════════════════════════════════════
    @api.model
    def civora_create_formal_notice(self, lease_id):
        """Cree une relance de severite 'legal' et retourne son id.

        La mise en demeure n'est pas un email au ton durci : c'est la piece
        qui ouvre la voie au recouvrement contentieux. Elle est donc tracee
        comme un document a part entiere, avec le detail des echeances, et
        materialisee par un PDF.
        """
        lease = self.env['civora.lease'].browse(int(lease_id))
        if not lease.exists():
            return {'success': False, 'error': "Bail introuvable."}

        ctx = self._template_context(lease)
        if not ctx['installments']:
            return {'success': False,
                    'error': "Ce bail n'a aucune échéance en retard."}

        fmt = {k: v for k, v in ctx.items() if k != 'installments'}
        reminder = self.create({
            'lease_id': lease.id,
            'channel': 'letter',
            'severity': 'legal',
            'subject': self.SUBJECT_TEMPLATES['legal'].format(**fmt),
            'body': self.BODY_TEMPLATES['legal'].format(**fmt),
            'arrears_amount': ctx['amount_raw'],
            'arrears_days': ctx['days'],
            'installment_ids': [(6, 0, [i.id for i in ctx['installments']])],
        })
        lease.message_post(
            body=Markup("Mise en demeure <b>%s</b> établie — %s dû sur %d "
                        "échéance(s), %d jour(s) de retard.") % (
                reminder.name, fmt['amount'],
                len(ctx['installments']), fmt['days']),
            subject="Mise en demeure",
        )
        return {'success': True, 'reminder_id': reminder.id,
                'name': reminder.name}

    def civora_notice_lines(self):
        """Lignes detaillees pour le PDF de mise en demeure."""
        self.ensure_one()
        today = fields.Date.context_today(self)
        lines = []
        for inst in self.installment_ids.sorted('due_date'):
            lines.append({
                'period': inst.period_label or "—",
                'due_date': inst.due_date,
                'amount_due': inst.amount_due or 0.0,
                'amount_paid': inst.amount_paid or 0.0,
                'amount_remaining': inst.amount_remaining or 0.0,
                'days': (today - inst.due_date).days if inst.due_date else 0,
            })
        return lines

    def civora_notice_deadline(self):
        """Date limite de regularisation portee au PDF."""
        self.ensure_one()
        base = self.date or fields.Date.context_today(self)
        return base + timedelta(days=self.FORMAL_NOTICE_DELAY_DAYS)

    # ═══════════════════════════════════════════════════════════════════
    # Relance groupee
    # ═══════════════════════════════════════════════════════════════════
    @api.model
    def civora_bulk_preview(self, lease_ids, channel='email'):
        """Simule une relance groupee : qui part, qui est exclu et pourquoi.

        Rien n'est cree ici. Un gestionnaire doit pouvoir voir exactement ce
        qui va se passer AVANT de declencher un envoi de masse : une relance
        partie chez un bon client qui a paye la veille coute plus cher que
        le loyer concerne.
        """
        Lease = self.env['civora.lease']
        leases = Lease.browse([int(i) for i in (lease_ids or [])]).exists()
        today = fields.Date.context_today(self)

        eligible, excluded = [], []
        for lease in leases:
            ctx = self._template_context(lease)
            reason = None

            if not ctx['installments']:
                reason = "Plus aucune échéance en retard"
            elif channel == 'email' and not (lease.tenant_id.email or "").strip():
                reason = "Pas d'adresse email"
            elif channel in ('sms', 'whatsapp') and not (lease.tenant_id.phone or "").strip():
                reason = "Pas de numéro de téléphone"
            else:
                already = self.search_count([
                    ('lease_id', '=', lease.id),
                    ('date', '=', today),
                    ('state', '=', 'sent'),
                ])
                if already:
                    reason = "Déjà relancé aujourd'hui"

            row = {
                'lease_id': lease.id,
                'lease_ref': lease.name or "—",
                'tenant_name': (lease.tenant_id.name or "—") if lease.tenant_id else "—",
                'property_name': (lease.property_id.name or "—") if lease.property_id else "—",
                'amount': ctx['amount_raw'],
                'days': ctx['days'],
                'severity': Lease._arrears_classify(ctx['days'])[0],
            }
            if reason:
                row['reason'] = reason
                excluded.append(row)
            else:
                eligible.append(row)

        # La passerelle SMS peut etre absente ou non configuree : on le dit
        # avant l'envoi, pas apres.
        channel_ready, channel_error = True, None
        if channel == 'sms':
            company = self.env.company
            if self.env.get('civora.sms') is None:
                channel_ready, channel_error = False, "Le module SMS n'est pas installé."
            elif not company.civora_sms_is_ready():
                channel_ready, channel_error = False, (
                    "La passerelle SMS n'est pas configurée pour « %s »."
                    % (company.name or "cette société"))

        return {
            'eligible': eligible,
            'excluded': excluded,
            'eligible_count': len(eligible),
            'excluded_count': len(excluded),
            'total_amount': sum(r['amount'] for r in eligible),
            'channel_ready': channel_ready,
            'channel_error': channel_error,
        }

    @api.model
    def civora_bulk_send(self, lease_ids, channel='email', severity=None):
        """Cree et envoie une relance par bail eligible.

        La severite est calculee bail par bail si elle n'est pas imposee :
        relancer un retard de 5 jours avec le meme ton qu'un retard de
        90 jours detruit la relation client dans un cas et la credibilite
        de l'agence dans l'autre.

        Chaque envoi est isole : l'echec d'un bail n'interrompt jamais le
        lot. Le detail est retourne pour affichage.
        """
        Lease = self.env['civora.lease']
        preview = self.civora_bulk_preview(lease_ids, channel=channel)
        if not preview['channel_ready']:
            return {'success': False, 'error': preview['channel_error'],
                    'sent': 0, 'failed': 0, 'results': []}

        results, sent, failed = [], 0, 0
        for row in preview['eligible']:
            lease = Lease.browse(row['lease_id'])
            sev = severity or row['severity']
            try:
                ctx = self._template_context(lease)
                fmt = {k: v for k, v in ctx.items() if k != 'installments'}
                reminder = self.create({
                    'lease_id': lease.id,
                    'channel': channel,
                    'severity': sev,
                    'subject': self.SUBJECT_TEMPLATES[sev].format(**fmt),
                    'body': self.BODY_TEMPLATES[sev].format(**fmt),
                    'arrears_amount': ctx['amount_raw'],
                    'arrears_days': ctx['days'],
                    'installment_ids': [(6, 0, [i.id for i in ctx['installments']])],
                })
                reminder.action_mark_sent()
                sent += 1
                results.append({'lease_ref': row['lease_ref'],
                                'tenant_name': row['tenant_name'],
                                'ok': True, 'severity': sev})
            except Exception as e:
                # Le lot doit survivre a un bail mal configure.
                failed += 1
                _logger.warning(
                    "CIVORA relance groupee — echec sur le bail %s : %s",
                    lease.name or lease.id, e)
                results.append({'lease_ref': row['lease_ref'],
                                'tenant_name': row['tenant_name'],
                                'ok': False, 'error': str(e)})

        return {
            'success': True,
            'sent': sent,
            'failed': failed,
            'skipped': preview['excluded_count'],
            'results': results,
        }

    def action_cancel(self):
        for rem in self:
            rem.state = 'cancelled'
        return True

    def action_reset_to_draft(self):
        for rem in self:
            rem.state = 'draft'
        return True
