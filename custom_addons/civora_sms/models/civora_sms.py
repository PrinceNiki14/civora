# -*- coding: utf-8 -*-
"""File d'envoi et historique des SMS CIVORA.

Point d'entrée unique pour tous les modules CIVORA :

    self.env['civora.sms'].civora_send(
        phone="+225 07 00 00 00 00",
        message="Votre contrat est prêt : https://…",
        partner=partner,          # optionnel
        record=contract,          # optionnel, pour retrouver l'historique
        immediate=True,           # tenter l'envoi tout de suite
    )

Un SMS n'est jamais envoyé sans laisser de trace : même un échec de
configuration produit un enregistrement en état « erreur », consultable.
"""
import logging
import unicodedata

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

SMS_STATE = [
    ('queued', "En file"),
    ('sent', "Envoyé"),
    ('error', "Échec"),
    ('cancelled', "Annulé"),
]

MAX_RETRY = 3

# Jeu de caractères GSM-7. Tout caractère absent de cet ensemble fait
# basculer le message entier en UCS-2 : 70 caractères par segment au lieu
# de 160, soit le double de segments facturés.
GSM7 = set(
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
    "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
)
# Ces caractères comptent double en GSM-7 (séquence d'échappement).
GSM7_EXTENDED = set("^{}\\[~]|€")


class CivoraSms(models.Model):
    _name = 'civora.sms'
    _description = "SMS CIVORA"
    _order = 'create_date desc, id desc'
    _rec_name = 'phone'

    phone = fields.Char(string="Numéro saisi", required=True)
    phone_normalized = fields.Char(string="Numéro normalisé", index=True, readonly=True)
    message = fields.Text(string="Message", required=True)
    state = fields.Selection(SMS_STATE, string="Statut", default='queued',
                             required=True, index=True)

    partner_id = fields.Many2one('res.partner', string="Destinataire",
                                 ondelete='set null', index=True)
    res_model = fields.Char(string="Modèle lié", index=True)
    res_id = fields.Integer(string="Enregistrement lié", index=True)

    company_id = fields.Many2one(
        'res.company', string="Société", required=True, index=True,
        default=lambda self: self.env.company,
    )

    encoding = fields.Selection([('gsm7', "GSM-7"), ('ucs2', "UCS-2")],
                                string="Codage", readonly=True)
    char_count = fields.Integer(string="Caractères", readonly=True)
    segments = fields.Integer(string="Segments facturés", readonly=True)

    provider_ticket = fields.Char(string="Ticket opérateur", readonly=True)
    provider_response = fields.Text(string="Réponse opérateur", readonly=True)
    error_message = fields.Text(string="Erreur", readonly=True)
    retry_count = fields.Integer(string="Tentatives", default=0, readonly=True)
    sent_at = fields.Datetime(string="Envoyé le", readonly=True)

    # ══════════════════════════════════════════════════════════════════
    # Normalisation et comptage
    # ══════════════════════════════════════════════════════════════════
    @api.model
    def civora_normalize_phone(self, phone):
        """Normalise vers le format attendu par HSMS : 2250700000000."""
        if not phone:
            return None
        cleaned = ''.join(c for c in str(phone) if c.isdigit() or c == '+')
        cleaned = cleaned.replace('+', '')
        if cleaned.startswith('00'):
            cleaned = cleaned[2:]
        # Numéro ivoirien local (10 chiffres depuis 2021) → préfixer 225.
        if len(cleaned) == 10 and not cleaned.startswith('225'):
            cleaned = '225' + cleaned
        # Ancien format à 8 chiffres : on refuse plutôt que de deviner.
        if len(cleaned) < 10:
            return None
        return cleaned

    @api.model
    def civora_deaccent(self, text):
        """Retire les accents sans altérer le sens du message."""
        if not text:
            return text
        return ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )

    @api.model
    def civora_measure(self, message):
        """Codage, longueur facturée et nombre de segments.

        C'est le calcul qui détermine la facture : un accent oublié double
        le coût d'une campagne.
        """
        text = message or ''
        is_gsm7 = all(c in GSM7 or c in GSM7_EXTENDED for c in text)
        if is_gsm7:
            length = sum(2 if c in GSM7_EXTENDED else 1 for c in text)
            single, multi = 160, 153
            encoding = 'gsm7'
        else:
            length = len(text)
            single, multi = 70, 67
            encoding = 'ucs2'
        if length == 0:
            segments = 0
        elif length <= single:
            segments = 1
        else:
            segments = -(-length // multi)  # division entière par excès
        return {'encoding': encoding, 'length': length, 'segments': segments}

    @api.model
    def civora_preview(self, message, company=None):
        """Renvoie le coût estimé d'un message, avant envoi."""
        company = company or self.env.company
        text = message or ''
        if company.civora_sms_deaccent:
            text = self.civora_deaccent(text)
        m = self.civora_measure(text)
        m['message'] = text
        return m

    # ══════════════════════════════════════════════════════════════════
    # API publique
    # ══════════════════════════════════════════════════════════════════
    @api.model
    def civora_send(self, phone, message, partner=None, record=None,
                    company=None, immediate=True):
        """Met un SMS en file et tente son envoi.

        Retourne un dict normalisé — l'appelant n'a jamais à gérer
        d'exception réseau.
        """
        company = company or (record.company_id if record and 'company_id' in record._fields
                              else self.env.company)
        if not company:
            company = self.env.company

        normalized = self.civora_normalize_phone(phone)
        text = message or ''
        if company.civora_sms_deaccent:
            text = self.civora_deaccent(text)
        measure = self.civora_measure(text)

        vals = {
            'phone': phone or '',
            'phone_normalized': normalized or False,
            'message': text,
            'company_id': company.id,
            'encoding': measure['encoding'],
            'char_count': measure['length'],
            'segments': measure['segments'],
            'state': 'queued',
        }
        if partner:
            vals['partner_id'] = partner.id
        if record:
            vals['res_model'] = record._name
            vals['res_id'] = record.id

        sms = self.sudo().create(vals)

        if not normalized:
            sms.write({'state': 'error',
                       'error_message': "Numéro de téléphone invalide ou incomplet."})
            return {'success': False, 'sms_id': sms.id,
                    'error': "Numéro de téléphone invalide ou incomplet."}

        if not company.civora_sms_enabled:
            sms.write({'state': 'error',
                       'error_message': "Les SMS ne sont pas activés pour cette société."})
            return {'success': False, 'sms_id': sms.id,
                    'error': "Les SMS ne sont pas activés pour cette société."}

        if immediate:
            sms._civora_deliver()
            return {
                'success': sms.state == 'sent',
                'sms_id': sms.id,
                'error': sms.error_message or None,
                'segments': sms.segments,
            }

        return {'success': True, 'sms_id': sms.id, 'queued': True,
                'segments': sms.segments}

    # ══════════════════════════════════════════════════════════════════
    # Livraison
    # ══════════════════════════════════════════════════════════════════
    def _civora_deliver(self):
        """Envoie effectivement les SMS du recordset."""
        for sms in self:
            if sms.state not in ('queued', 'error'):
                continue
            if sms.retry_count >= MAX_RETRY:
                continue
            company = sms.company_id
            if not company.civora_sms_enabled:
                sms.write({'state': 'error',
                           'error_message': "SMS désactivés pour cette société."})
                continue

            service = company.civora_sms_service()
            res = service.send(sms.phone_normalized, sms.message)

            if res.get('success'):
                sms.write({
                    'state': 'sent',
                    'sent_at': fields.Datetime.now(),
                    'provider_ticket': res.get('ticket') or False,
                    'provider_response': res.get('raw') or False,
                    'error_message': False,
                    'retry_count': sms.retry_count + 1,
                })
            else:
                sms.write({
                    'state': 'error',
                    'error_message': res.get('error') or "Échec inconnu",
                    'provider_response': res.get('raw') or False,
                    'retry_count': sms.retry_count + 1,
                })

    @api.model
    def cron_civora_process_sms_queue(self):
        """Traite la file : messages en attente et échecs relançables.

        Batché et committé par lots : un envoi groupé ne doit pas être
        perdu en entier parce que le dernier message a échoué.
        """
        pending = self.search([
            ('state', 'in', ('queued', 'error')),
            ('retry_count', '<', MAX_RETRY),
            ('phone_normalized', '!=', False),
        ], limit=500, order='id asc')

        processed = 0
        for sms in pending:
            if not sms.company_id.civora_sms_enabled:
                continue
            sms._civora_deliver()
            processed += 1
            if processed % 25 == 0:
                self.env.cr.commit()
        return {'processed': processed}

    # ══════════════════════════════════════════════════════════════════
    # Consultation (RPC)
    # ══════════════════════════════════════════════════════════════════
    @api.model
    def civora_sms_status(self, company_id=None):
        """État de la passerelle, pour l'écran de configuration."""
        company = (self.env['res.company'].browse(int(company_id))
                   if company_id else self.env.company)
        service = company.civora_sms_service()
        return {
            'enabled': bool(company.civora_sms_enabled),
            'configured': service.is_configured(),
            'sender_id': company.civora_sms_sender_id or '',
            'queued': self.search_count([('company_id', '=', company.id),
                                         ('state', '=', 'queued')]),
            'errors': self.search_count([('company_id', '=', company.id),
                                         ('state', '=', 'error')]),
            'sent_total': self.search_count([('company_id', '=', company.id),
                                             ('state', '=', 'sent')]),
        }

    @api.model
    def civora_check_balance(self, company_id=None):
        company = (self.env['res.company'].browse(int(company_id))
                   if company_id else self.env.company)
        return company.civora_sms_service().check_balance()

    @api.model
    def civora_send_test(self, phone, company_id=None):
        """Envoi de test, pour valider une configuration."""
        company = (self.env['res.company'].browse(int(company_id))
                   if company_id else self.env.company)
        return self.civora_send(
            phone,
            "Test CIVORA : votre passerelle SMS est operationnelle.",
            company=company, immediate=True,
        )

    def action_retry(self):
        """Relance manuelle depuis l'historique."""
        self.write({'retry_count': 0, 'state': 'queued', 'error_message': False})
        self._civora_deliver()
        return True
