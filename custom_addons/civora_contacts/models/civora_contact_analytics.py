# -*- coding: utf-8 -*-
"""Methodes analytiques pour les onglets "Scoring IA" et "Interactions".

Regroupees dans un fichier dedie pour ne pas alourdir res_partner.py et
garder une frontiere claire entre le calcul du score (res_partner.py) et
son exploitation statistique (ici).

Toutes les methodes sont publiques (appelables en RPC depuis OWL) et
respectent les regles d'isolation multi-societe : aucun sudo() n'est
utilise sur les recordsets metier, les ir.rule s'appliquent donc
normalement.

Performance : concu pour des bases de grande agence (100k+ contacts).
Aucune methode ne charge l'integralite des enregistrements en memoire —
on s'appuie sur search_count / _read_group / search_read limite.
"""
from odoo import api, fields, models

# ══════════════════════════════════════════════════════════════════════
# Tranches de score — alignees sur le front CIVORA (ScoringView)
# ══════════════════════════════════════════════════════════════════════
SCORE_BUCKETS = [
    {'code': 'chaud',    'emoji': '\U0001F525', 'label': "Chaud",    'min': 85, 'max': 100, 'tone': 'success'},
    {'code': 'qualifie', 'emoji': '\u2B50',     'label': "Qualifié", 'min': 60, 'max': 84,  'tone': 'success'},
    {'code': 'tiede',    'emoji': '\U0001F331', 'label': "Tiède",    'min': 30, 'max': 59,  'tone': 'warning'},
    {'code': 'froid',    'emoji': '\u2744',     'label': "Froid",    'min': 0,  'max': 29,  'tone': 'danger'},
]

# ══════════════════════════════════════════════════════════════════════
# Ponderations REELLES de la formule v10.1.0 (civora_compute_ai_score).
# Toute modification de la formule doit etre repercutee ici — c'est la
# source d'affichage de l'onglet Scoring, elle doit rester honnete.
# ══════════════════════════════════════════════════════════════════════
SCORE_WEIGHTS = [
    {
        'code': 'activity', 'label': "Activité récente", 'weight': 30,
        'desc': "Interactions sur 30 / 60 / 90 jours (10 / 6 / 3 pts par interaction)",
    },
    {
        'code': 'engagement', 'label': "Engagement financier", 'weight': 25,
        'desc': "Bien détenu (10) · Bail actif (10) · Budget renseigné (5)",
    },
    {
        'code': 'seniority', 'label': "Ancienneté relation", 'weight': 20,
        'desc': "3 ans et + (20) · 2 ans (15) · 1 an (10) · au prorata en deçà",
    },
    {
        'code': 'completeness', 'label': "Complétude des données", 'weight': 15,
        'desc': "Email · Téléphone · Rôle · Source · Agent (3 pts chacun)",
    },
    {
        'code': 'consent', 'label': "Consentements RGPD", 'weight': 10,
        'desc': "Opt-in Email (4) · SMS (3) · WhatsApp (3)",
    },
]

# Ajustements hors ponderation, affiches separement pour transparence
SCORE_ADJUSTMENTS = [
    {'label': "Statut « Chaud »", 'effect': "+10 pts", 'tone': 'success'},
    {'label': "Statut « À risque »", 'effect': "plafonné à 60", 'tone': 'warning'},
    {'label': "Statut « Inactif »", 'effect': "plafonné à 40", 'tone': 'danger'},
    {'label': "2 baux en retard ou plus", 'effect': "−15 pts", 'tone': 'danger'},
]

# Canaux du widget "Canaux 30 jours" — role_change exclu (evenement d'audit,
# pas un canal de communication).
FEED_CHANNELS = [
    {'code': 'email',    'label': "Email",    'icon': 'fa-envelope-o', 'variant': 'info'},
    {'code': 'whatsapp', 'label': "WhatsApp", 'icon': 'fa-whatsapp',   'variant': 'success'},
    {'code': 'sms',      'label': "SMS",      'icon': 'fa-comment-o',  'variant': 'neutral'},
    {'code': 'appel',    'label': "Appel",    'icon': 'fa-phone',      'variant': 'accent'},
    {'code': 'visite',   'label': "Visite",   'icon': 'fa-map-marker', 'variant': 'warning'},
    {'code': 'rdv',      'label': "RDV",      'icon': 'fa-calendar-o', 'variant': 'info'},
    {'code': 'note',     'label': "Note",     'icon': 'fa-sticky-note-o', 'variant': 'neutral'},
    {'code': 'document', 'label': "Document", 'icon': 'fa-file-o',     'variant': 'neutral'},
]
FEED_KINDS = [c['code'] for c in FEED_CHANNELS]


def _humanize_delta(now, dt):
    """Rend un delai relatif en francais : « il y a 12 min », « hier »…"""
    if not dt:
        return ""
    seconds = (now - dt).total_seconds()
    if seconds < 0:
        return "à venir"
    minutes = int(seconds // 60)
    if minutes < 1:
        return "à l'instant"
    if minutes < 60:
        return "il y a %d min" % minutes
    hours = minutes // 60
    if hours < 24:
        return "il y a %dh" % hours
    days = hours // 24
    if days == 1:
        return "hier"
    if days < 30:
        return "il y a %dj" % days
    months = days // 30
    if months < 12:
        return "il y a %d mois" % months
    years = days // 365
    return "il y a %d an%s" % (years, "s" if years > 1 else "")


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ══════════════════════════════════════════════════════════════════
    # Onglet "Scoring IA"
    # ══════════════════════════════════════════════════════════════════
    @api.model
    def civora_get_scoring_analytics(self):
        """Statistiques de distribution du score IA + recommandations.

        Retourne un payload complet pour l'onglet Scoring :
        - kpis        : total / moyenne / verrouilles / date dernier calcul
        - buckets     : 4 tranches avec effectif et part du portefeuille
        - weights     : les 5 ponderations REELLES de la formule v10.1.0
        - adjustments : bonus/malus statut, affiches pour transparence
        - reco        : 3 recommandations calculees (a closer / relancer / reclasser)
        - top / flop  : 10 meilleurs et 10 plus faibles scores
        """
        base = [('civora_is_contact', '=', True)]
        total = self.search_count(base)

        # --- KPIs globaux -------------------------------------------------
        avg = 0.0
        if total:
            avg = self._civora_avg_score(base)

        locked = self.search_count(base + [('civora_ai_score_manual', '=', True)])

        last_rec = self.search(
            base + [('civora_ai_score_updated', '!=', False)],
            limit=1, order='civora_ai_score_updated desc',
        )
        last_update = (
            fields.Datetime.to_string(last_rec.civora_ai_score_updated)
            if last_rec else ''
        )

        # --- Distribution par tranche ------------------------------------
        buckets = []
        for b in SCORE_BUCKETS:
            count = self.search_count(base + [
                ('civora_ai_score', '>=', b['min']),
                ('civora_ai_score', '<=', b['max']),
            ])
            buckets.append({
                'code': b['code'],
                'emoji': b['emoji'],
                'label': b['label'],
                'range': '%d-%d' % (b['min'], b['max']) if b['min'] else '< %d' % (b['max'] + 1),
                'min': b['min'],
                'max': b['max'],
                'tone': b['tone'],
                'count': count,
                'pct': round(count * 100.0 / total, 1) if total else 0.0,
            })

        # --- Top / Flop ---------------------------------------------------
        fields_list = ['name', 'civora_ai_score', 'civora_status',
                       'civora_agent_id', 'civora_last_interaction_date']
        top = self.search_read(
            base, fields_list, limit=10, order='civora_ai_score desc, name asc')
        flop = self.search_read(
            base, fields_list, limit=10, order='civora_ai_score asc, name asc')

        return {
            'kpis': {
                'total': total,
                'avg': round(avg, 1),
                'locked': locked,
                'last_update': last_update,
                'scored': self.search_count(base + [('civora_ai_score', '>', 0)]),
            },
            'buckets': buckets,
            'weights': SCORE_WEIGHTS,
            'adjustments': SCORE_ADJUSTMENTS,
            'reco': self._civora_scoring_reco(base),
            'top': [self._civora_score_row(r) for r in top],
            'flop': [self._civora_score_row(r) for r in flop],
        }

    @api.model
    def civora_request_score_recompute(self):
        """Programme un recalcul global des scores IA.

        Volontairement ASYNCHRONE : cron_civora_recompute_all_scores committe
        par lots de 500, ce qui est legitime dans un cron mais casserait la
        transaction d'une requete HTTP — et depasserait le timeout du worker
        sur un portefeuille de grande agence.

        On declenche donc le cron existant, qui sera pris en charge par le
        scheduler dans la minute, dans sa propre transaction.
        """
        pending = self.search_count([
            ('civora_is_contact', '=', True),
            ('civora_ai_score_manual', '=', False),
        ])
        cron = self.env.ref(
            'civora_contacts.cron_civora_recompute_ai_scores',
            raise_if_not_found=False,
        )
        if not cron:
            return {'queued': False, 'pending': pending,
                    'error': "Tâche planifiée introuvable."}
        cron.sudo()._trigger()
        return {'queued': True, 'pending': pending}

    def _civora_avg_score(self, domain):
        """Moyenne du score via agregation SQL (pas de chargement memoire).

        Repli defensif sur une lecture de la seule colonne score si la
        signature de _read_group venait a changer.
        """
        try:
            groups = self._read_group(domain, [], ['civora_ai_score:avg'])
            if groups and groups[0] and groups[0][0] is not None:
                return float(groups[0][0])
            return 0.0
        except Exception:  # noqa: BLE001 - repli volontairement large
            rows = self.search_read(domain, ['civora_ai_score'])
            if not rows:
                return 0.0
            return sum(r['civora_ai_score'] or 0 for r in rows) / float(len(rows))

    def _civora_score_row(self, r):
        """Normalise une ligne contact pour l'affichage Top/Flop."""
        agent = r.get('civora_agent_id')
        return {
            'id': r['id'],
            'name': r.get('name') or '',
            'score': r.get('civora_ai_score') or 0,
            'status': r.get('civora_status') or '',
            'agent': agent[1] if agent else '',
            'last_interaction': (
                fields.Datetime.to_string(r['civora_last_interaction_date'])
                if r.get('civora_last_interaction_date') else ''
            ),
        }

    def _civora_scoring_reco(self, base):
        """Trois recommandations calculees sur des criteres explicites.

        Chaque bloc renvoie un effectif reel + les 10 premiers contacts
        concernes (cliquables vers la fiche 360°). Aucun chiffre decoratif.
        """
        now = fields.Datetime.now()
        d7 = fields.Datetime.subtract(now, days=7)
        d14 = fields.Datetime.subtract(now, days=14)
        cols = ['name', 'civora_ai_score', 'civora_status',
                'civora_agent_id', 'civora_last_interaction_date']

        # 1) A closer : score eleve + contact recent + pas eteint
        dom_close = base + [
            ('civora_ai_score', '>=', 85),
            ('civora_last_interaction_date', '>=', d7),
            ('civora_status', 'not in', ['inactif', 'a_risque']),
        ]
        # 2) A relancer : score exploitable mais silence radio > 14j
        dom_revive = base + [
            ('civora_ai_score', '>=', 30),
            ('civora_ai_score', '<', 85),
            '|',
            ('civora_last_interaction_date', '=', False),
            ('civora_last_interaction_date', '<', d14),
        ]
        # 3) A reclasser : incoherence entre le score et le statut CRM
        dom_reclass = base + [
            '|', '|',
            '&', ('civora_ai_score', '>=', 85), ('civora_status', '!=', 'chaud'),
            '&', ('civora_ai_score', '<', 30), ('civora_status', 'in', ['chaud', 'qualifie']),
            '&', ('civora_ai_score', '>=', 60), ('civora_status', '=', 'inactif'),
        ]

        def block(domain, order):
            rows = self.search_read(domain, cols, limit=10, order=order)
            return {
                'count': self.search_count(domain),
                'items': [self._civora_score_row(r) for r in rows],
            }

        return {
            'to_close': block(dom_close, 'civora_ai_score desc, name asc'),
            'to_revive': block(dom_revive, 'civora_ai_score desc, name asc'),
            'to_reclass': block(dom_reclass, 'civora_ai_score desc, name asc'),
        }


class CivoraInteraction(models.Model):
    _inherit = 'civora.interaction'

    # ══════════════════════════════════════════════════════════════════
    # Onglet "Interactions"
    # ══════════════════════════════════════════════════════════════════
    @api.model
    def civora_get_feed_meta(self):
        """Metadonnees statiques du flux (canaux + agents disponibles)."""
        agents = self.env['res.users'].search_read(
            [('share', '=', False)], ['name'], order='name')
        return {
            'channels': FEED_CHANNELS,
            'agents': [{'id': a['id'], 'name': a['name']} for a in agents],
        }

    @api.model
    def civora_get_global_feed(self, offset=0, limit=30, kind=None,
                               agent_id=None, days=None):
        """Flux global multi-contacts, trie du plus recent au plus ancien.

        Les evenements 'role_change' sont exclus : ce sont des traces
        d'audit deja visibles dans la timeline de la fiche 360°, pas des
        interactions commerciales.
        """
        now = fields.Datetime.now()
        domain = [('kind', 'in', FEED_KINDS)]
        if kind and kind in FEED_KINDS:
            domain.append(('kind', '=', kind))
        if agent_id:
            domain.append(('agent_id', '=', int(agent_id)))
        if days:
            domain.append(('date', '>=', fields.Datetime.subtract(now, days=int(days))))

        total = self.search_count(domain)
        recs = self.search_read(
            domain,
            ['contact_id', 'kind', 'title', 'description', 'agent_id', 'date'],
            offset=int(offset), limit=int(limit), order='date desc, id desc',
        )
        # Libelles maitrises localement : le flux est restreint a FEED_KINDS,
        # inutile de dependre d'une API privee du framework.
        labels = {c['code']: c['label'] for c in FEED_CHANNELS}

        rows = []
        for r in recs:
            contact = r.get('contact_id')
            agent = r.get('agent_id')
            rows.append({
                'id': r['id'],
                'contact_id': contact[0] if contact else False,
                'contact_name': contact[1] if contact else "—",
                'kind': r.get('kind') or '',
                'kind_label': labels.get(r.get('kind'), r.get('kind') or ''),
                'title': r.get('title') or '',
                'description': r.get('description') or '',
                'agent_name': agent[1] if agent else '',
                'date': fields.Datetime.to_string(r['date']) if r.get('date') else '',
                'ago': _humanize_delta(now, r['date']) if r.get('date') else '',
            })

        return {
            'rows': rows,
            'total': total,
            'has_more': int(offset) + len(rows) < total,
        }

    def _civora_count_distinct(self, domain, field_name):
        """Nombre de valeurs distinctes d'un champ, via agregation SQL."""
        try:
            groups = self._read_group(domain, [field_name], [])
            return len([g for g in groups if g and g[0]])
        except Exception:  # noqa: BLE001 - repli defensif
            return 0

    @api.model
    def civora_get_channel_stats(self, days=30):
        """Repartition par canal sur N jours + KPIs de l'onglet.

        Le pourcentage affiche est la part relative au canal dominant
        (barre pleine = canal le plus utilise), ce qui rend les volumes
        comparables visuellement quel que soit l'ordre de grandeur.
        """
        now = fields.Datetime.now()
        since = fields.Datetime.subtract(now, days=int(days))
        domain = [('kind', 'in', FEED_KINDS), ('date', '>=', since)]

        counts = {}
        try:
            for kind, count in self._read_group(domain, ['kind'], ['__count']):
                counts[kind] = count
        except Exception:  # noqa: BLE001 - repli si signature differente
            for code in FEED_KINDS:
                counts[code] = self.search_count(domain + [('kind', '=', code)])

        total = sum(counts.values())
        top = max(counts.values()) if counts else 0

        channels = []
        for c in FEED_CHANNELS:
            n = counts.get(c['code'], 0)
            channels.append({
                'code': c['code'],
                'label': c['label'],
                'icon': c['icon'],
                'variant': c['variant'],
                'count': n,
                'pct': round(n * 100.0 / top, 1) if top else 0.0,
                'share': round(n * 100.0 / total, 1) if total else 0.0,
            })
        channels.sort(key=lambda x: x['count'], reverse=True)

        # KPIs : agents actifs et contacts touches sur la periode.
        # On compte des GROUPES, pas des enregistrements — indispensable sur
        # une base ou 30 jours peuvent representer des centaines de milliers
        # d'interactions.
        agents_active = self._civora_count_distinct(domain, 'agent_id')
        contacts_touched = self._civora_count_distinct(domain, 'contact_id')

        dominant = channels[0] if channels and channels[0]['count'] else None

        return {
            'days': int(days),
            'total': total,
            'channels': channels,
            'dominant_label': dominant['label'] if dominant else "—",
            'dominant_count': dominant['count'] if dominant else 0,
            'agents_active': agents_active,
            'contacts_touched': contacts_touched,
        }
