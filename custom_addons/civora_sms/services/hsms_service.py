# -*- coding: utf-8 -*-
"""Service d'envoi SMS via l'API HSMS v2 (hsms.ci).

Différences avec l'implémentation d'origine, toutes motivées par un usage
en production multi-agences :

- Les identifiants sont lus sur la SOCIÉTÉ, pas dans les paramètres
  système : chaque agence a son compte et son sender ID.
- Le token Bearer est mis en cache et partagé entre les envois. La version
  d'origine ré-authentifiait à chaque instanciation du service, soit un
  appel réseau supplémentaire par SMS lors d'un envoi groupé.
- Une réponse 401 déclenche une ré-authentification unique puis un nouvel
  essai, au lieu de perdre le message.
"""
import logging
import time

import requests

_logger = logging.getLogger(__name__)

HSMS_BASE_URL = "https://hsms.ci"
HSMS_TOKEN_URL = "%s/api/v2/sms/token/" % HSMS_BASE_URL
HSMS_SEND_URL = "%s/api/v2/sms/send/" % HSMS_BASE_URL
HSMS_BALANCE_URL = "%s/api/v2/sms/check-balance/" % HSMS_BASE_URL

REQUEST_TIMEOUT = 15          # secondes
TOKEN_TTL = 25 * 60           # HSMS ne documente pas la durée de vie du
                              # token : on reste volontairement conservateur.

# Cache mémoire par (base de données, société). Le worker qui envoie un lot
# réutilise ainsi le même token pour tous les messages.
_TOKEN_CACHE = {}


class HSMSError(Exception):
    """Erreur remontée par la passerelle SMS."""


class HSMSService:

    def __init__(self, company):
        self.company = company
        self.email = (company.civora_sms_email or '').strip()
        self.password = (company.civora_sms_password or '').strip()
        self.client_id = (company.civora_sms_client_id or '').strip()
        self.client_secret = (company.civora_sms_client_secret or '').strip()
        self.sender_id = (company.civora_sms_sender_id or '').strip()
        self._cache_key = (company.env.cr.dbname, company.id)

    # ── Configuration ──────────────────────────────────────────────────
    def is_configured(self):
        return bool(self.email and self.password
                    and self.client_id and self.client_secret)

    def _require_config(self):
        if not self.is_configured():
            raise HSMSError(
                "La passerelle SMS n'est pas configurée pour la société « %s ». "
                "Renseignez les identifiants HSMS dans Paramètres → CIVORA SMS."
                % (self.company.name or "—")
            )

    # ── Token ──────────────────────────────────────────────────────────
    def _cached_token(self):
        entry = _TOKEN_CACHE.get(self._cache_key)
        if entry and entry[1] > time.time():
            return entry[0]
        return None

    def _authenticate(self, force=False):
        self._require_config()
        if not force:
            token = self._cached_token()
            if token:
                return token
        try:
            resp = requests.post(
                HSMS_TOKEN_URL,
                json={"email": self.email, "password": self.password},
                timeout=REQUEST_TIMEOUT,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.Timeout:
            raise HSMSError("Délai dépassé lors de l'authentification SMS.")
        except requests.exceptions.RequestException as e:
            raise HSMSError("Passerelle SMS injoignable : %s" % e)
        except ValueError:
            raise HSMSError("Réponse d'authentification illisible.")

        if not data.get('success') or not data.get('token'):
            raise HSMSError("Authentification refusée : %s"
                            % data.get('message', "identifiants invalides"))

        token = data['token']
        _TOKEN_CACHE[self._cache_key] = (token, time.time() + TOKEN_TTL)
        _logger.info("CIVORA SMS : token HSMS obtenu pour la société %s",
                     self.company.id)
        return token

    def invalidate_token(self):
        _TOKEN_CACHE.pop(self._cache_key, None)

    # ── Envoi ──────────────────────────────────────────────────────────
    def send(self, phone, message, _retry=True):
        """Envoie un SMS. Retourne un dict normalisé, ne lève jamais.

        Le retour est volontairement uniforme pour que l'appelant enregistre
        toujours une trace, succès ou échec.
        """
        try:
            self._require_config()
        except HSMSError as e:
            return {'success': False, 'error': str(e), 'ticket': None, 'raw': None}

        try:
            token = self._authenticate()
        except HSMSError as e:
            return {'success': False, 'error': str(e), 'ticket': None, 'raw': None}

        payload = {
            "clientid": self.client_id,
            "clientsecret": self.client_secret,
            "message": message,
            "telephone": phone,
            "unicode": False,
        }
        if self.sender_id:
            payload["sender"] = self.sender_id

        try:
            resp = requests.post(
                HSMS_SEND_URL, json=payload, timeout=REQUEST_TIMEOUT,
                headers={"Authorization": "Bearer %s" % token,
                         "Content-Type": "application/json"},
            )
        except requests.exceptions.Timeout:
            return {'success': False, 'error': "Délai dépassé côté opérateur.",
                    'ticket': None, 'raw': None}
        except requests.exceptions.RequestException as e:
            return {'success': False, 'error': "Réseau : %s" % e,
                    'ticket': None, 'raw': None}

        # Token expiré côté opérateur : on ré-authentifie une seule fois.
        if resp.status_code in (401, 403) and _retry:
            self.invalidate_token()
            try:
                self._authenticate(force=True)
            except HSMSError as e:
                return {'success': False, 'error': str(e), 'ticket': None, 'raw': None}
            return self.send(phone, message, _retry=False)

        try:
            resp.raise_for_status()
            data = resp.json()
        except (requests.exceptions.RequestException, ValueError) as e:
            return {'success': False, 'error': "Réponse opérateur invalide : %s" % e,
                    'ticket': None, 'raw': (resp.text or '')[:500]}

        if not data.get('success'):
            return {'success': False,
                    'error': data.get('message') or "Refus de l'opérateur",
                    'ticket': None, 'raw': str(data)[:500]}

        ticket = None
        tasks = data.get('tasks') or {}
        if isinstance(tasks, dict) and phone in tasks:
            ticket = (tasks[phone] or {}).get('ticket')

        _logger.info("CIVORA SMS envoyé à %s | ticket=%s", _mask(phone), ticket)
        return {'success': True, 'error': None, 'ticket': ticket,
                'raw': str(data)[:500]}

    # ── Solde ──────────────────────────────────────────────────────────
    def check_balance(self):
        try:
            self._require_config()
            token = self._authenticate()
        except HSMSError as e:
            return {'success': False, 'error': str(e), 'balance': None}
        try:
            resp = requests.post(
                HSMS_BALANCE_URL,
                json={"clientid": self.client_id,
                      "clientsecret": self.client_secret},
                timeout=REQUEST_TIMEOUT,
                headers={"Authorization": "Bearer %s" % token,
                         "Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:  # noqa: BLE001
            return {'success': False, 'error': str(e), 'balance': None}
        if not data.get('success'):
            return {'success': False,
                    'error': data.get('message') or "Refus de l'opérateur",
                    'balance': None}
        return {'success': True, 'error': None, 'balance': data.get('balance', 0)}


def _mask(phone):
    """Masque un numéro dans les journaux : 225070***12."""
    p = phone or ''
    return "%s***%s" % (p[:6], p[-2:]) if len(p) > 8 else "***"
