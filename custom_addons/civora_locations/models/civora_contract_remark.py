# -*- coding: utf-8 -*-
"""Remarques emises par le locataire sur un contrat de bail.

Flux (option A — exclusif) :
  - Le locataire consulte le contrat via son lien /civora/contract/<token>
  - S'il n'est pas d'accord avec un article, il depose une remarque
  - Tant qu'une remarque est OUVERTE, la signature est bloquee : on ne signe
    pas un contrat que l'on conteste, cela rendrait le consentement ambigu
  - L'agence traite chaque remarque (acceptee / refusee) en y repondant
  - Quand plus aucune remarque n'est ouverte, la signature redevient possible

Chaque depot est horodate et trace (IP, user-agent) : en cas de litige, il
faut pouvoir demontrer qui a dit quoi et quand.
"""
from markupsafe import Markup

from odoo import api, fields, models

REMARK_STATE = [
    ('open', "En attente"),
    ('accepted', "Acceptée"),
    ('rejected', "Refusée"),
]

# Etats du contrat pendant lesquels une remarque peut encore etre deposee.
REMARK_ALLOWED_CONTRACT_STATES = ('signed_lessor',)


class CivoraContractRemark(models.Model):
    _name = 'civora.contract.remark'
    _description = "Remarque du locataire sur un contrat de bail"
    _order = 'create_date desc, id desc'

    contract_id = fields.Many2one(
        'civora.lease.contract', string="Contrat", required=True,
        ondelete='cascade', index=True,
    )
    lease_id = fields.Many2one(
        related='contract_id.lease_id', string="Bail", store=True, index=True,
    )
    company_id = fields.Many2one(
        related='contract_id.company_id', string="Société", store=True, index=True,
    )

    # ── Cible de la remarque ────────────────────────────────────────────
    # Une remarque vise soit une clause du contrat, soit une section fixe
    # (Article 1 les parties, Article 2 le bien, Article 3 les conditions
    # financieres) qui n'est pas portee par une clause.
    clause_id = fields.Many2one(
        'civora.lease.clause', string="Clause visée", ondelete='set null',
    )
    section_ref = fields.Char(
        string="Référence de l'article",
        help="Identifiant technique de la section visée (ex. 'parties', 'bien').",
    )
    section_label = fields.Char(
        string="Article", help="Libellé lisible de l'article visé.",
    )

    # ── Contenu ─────────────────────────────────────────────────────────
    body = fields.Text(string="Remarque du locataire", required=True)
    state = fields.Selection(
        REMARK_STATE, string="Statut", default='open', required=True, index=True,
    )
    response = fields.Text(string="Réponse de l'agence")
    responded_by = fields.Many2one('res.users', string="Traitée par", readonly=True)
    responded_at = fields.Datetime(string="Traitée le", readonly=True)

    # ── Tracabilite ─────────────────────────────────────────────────────
    author_name = fields.Char(string="Déposée par", readonly=True)
    ip = fields.Char(string="Adresse IP", readonly=True)
    user_agent = fields.Char(string="Navigateur", readonly=True)

    # ══════════════════════════════════════════════════════════════════
    # Depot depuis le portail
    # ══════════════════════════════════════════════════════════════════
    @api.model
    def civora_portal_create(self, contract, body, section_ref=None,
                             section_label=None, clause_id=None,
                             ip=None, user_agent=None):
        """Cree une remarque depuis le portail public et alerte l'agence.

        Appelee uniquement par le controleur, en sudo : le locataire n'a
        aucun droit ORM, il n'est pas authentifie.
        """
        text = (body or '').strip()
        if not text:
            return False

        remark = self.sudo().create({
            'contract_id': contract.id,
            'body': text[:4000],
            'section_ref': section_ref or False,
            'section_label': section_label or "Contrat",
            'clause_id': int(clause_id) if clause_id else False,
            'author_name': contract.lease_id.tenant_id.name or "Locataire",
            'ip': (ip or '')[:64],
            'user_agent': (user_agent or '')[:255],
        })
        remark._notify_agency()
        return remark

    def _notify_agency(self):
        """Message au chatter + activite planifiee pour l'agent.

        Le message seul ne suffit pas : personne ne surveille un chatter.
        L'activite, elle, apparait dans le tableau de bord de l'agent et
        ne disparait que lorsqu'il l'a traitee.
        """
        for r in self:
            contract = r.contract_id
            # Markup() est indispensable : depuis Odoo 17, message_post
            # echappe les chaines simples. Et l'operateur % de Markup echappe
            # automatiquement ses arguments — le texte du locataire, qui vient
            # d'un formulaire public, ne peut donc pas casser le balisage.
            contract.message_post(
                body=Markup(
                    "<p><b>Remarque du locataire</b> sur « %s »</p>"
                    "<blockquote>%s</blockquote>"
                ) % (r.section_label or "le contrat", (r.body or '')[:500]),
                subtype_xmlid='mail.mt_note',
            )
            agent = (
                contract.lease_id.agent_id
                if 'agent_id' in contract.lease_id._fields else False
            )
            user = agent if agent else contract.create_uid
            if not user:
                continue
            try:
                contract.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary="Remarque locataire sur %s" % (contract.name or "le contrat"),
                    note=(r.body or '')[:500],
                    user_id=user.id,
                )
            except Exception:  # noqa: BLE001
                # Une activite qui echoue ne doit jamais faire perdre la
                # remarque du locataire.
                pass

    # ══════════════════════════════════════════════════════════════════
    # Traitement par l'agence (RPC depuis l'onglet Contrat)
    # ══════════════════════════════════════════════════════════════════
    @api.model
    def civora_get_remarks(self, contract_id):
        """Liste des remarques d'un contrat, pour l'écran agence."""
        recs = self.search([('contract_id', '=', int(contract_id))])
        return {
            'rows': [{
                'id': r.id,
                'section_label': r.section_label or "Contrat",
                'body': r.body or '',
                'state': r.state,
                'state_label': dict(REMARK_STATE).get(r.state, r.state),
                'response': r.response or '',
                'author_name': r.author_name or '',
                'ip': r.ip or '',
                'created': fields.Datetime.to_string(r.create_date) if r.create_date else '',
                'responded_at': (fields.Datetime.to_string(r.responded_at)
                                 if r.responded_at else ''),
                'responded_by': r.responded_by.name or '',
            } for r in recs],
            'total': len(recs),
            'open': len(recs.filtered(lambda x: x.state == 'open')),
        }

    @api.model
    def civora_answer_remark(self, remark_id, state, response=None):
        """Accepte ou refuse une remarque, avec une réponse motivée."""
        if state not in ('accepted', 'rejected'):
            return {'success': False, 'error': "Statut invalide."}
        r = self.browse(int(remark_id))
        if not r.exists():
            return {'success': False, 'error': "Remarque introuvable."}
        text = (response or '').strip()
        if not text:
            return {'success': False,
                    'error': "Une réponse est obligatoire : le locataire doit "
                             "comprendre la décision de l'agence."}
        r.write({
            'state': state,
            'response': text,
            'responded_by': self.env.user.id,
            'responded_at': fields.Datetime.now(),
        })
        label = "acceptée" if state == 'accepted' else "refusée"
        r.contract_id.message_post(
            body=Markup("<p>Remarque sur « %s » <b>%s</b>.</p>"
                        "<blockquote>%s</blockquote>")
                 % (r.section_label or "le contrat", label, text[:500]),
            subtype_xmlid='mail.mt_note',
        )
        return {'success': True, 'remarks': self.civora_get_remarks(r.contract_id.id)}

    @api.model
    def civora_reopen_remark(self, remark_id):
        """Remet une remarque en attente (erreur de traitement)."""
        r = self.browse(int(remark_id))
        if not r.exists():
            return {'success': False, 'error': "Remarque introuvable."}
        r.write({'state': 'open', 'responded_by': False, 'responded_at': False})
        return {'success': True, 'remarks': self.civora_get_remarks(r.contract_id.id)}
