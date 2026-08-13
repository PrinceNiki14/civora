# -*- coding: utf-8 -*-
from markupsafe import Markup

from odoo import api, fields, models

CIVORA_LEAD_STATUS = [
    ('nouveau', "Nouveau"),
    ('a_qualifier', "À qualifier"),
    ('qualifie', "Qualifié"),
    ('rejete', "Rejeté"),
]
CIVORA_TRANSACTION = [
    ('vente', "Vente"),
    ('location', "Location"),
    ('saisonnier', "Saisonnier"),
]


class CivoraLead(models.Model):
    """Piste (lead) : interet entrant avant qualification."""
    _name = 'civora.lead'
    _description = "Piste CIVORA"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'score desc, create_date desc'

    name = fields.Char(string="Titre", required=True, index=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string="Contact", tracking=True)
    contact_name = fields.Char(string="Nom du contact")
    email = fields.Char(string="Email")
    phone = fields.Char(string="Téléphone")
    source_id = fields.Many2one('civora.contact.source', string="Source", tracking=True)
    status = fields.Selection(CIVORA_LEAD_STATUS, string="Statut", required=True, default='nouveau', index=True, tracking=True)
    score = fields.Integer(string="Score IA", tracking=True)
    transaction = fields.Selection(CIVORA_TRANSACTION, string="Recherche", tracking=True)
    budget_min = fields.Monetary(string="Budget min", currency_field='currency_id')
    budget_max = fields.Monetary(string="Budget max", currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency', string="Devise", required=True,
        default=lambda self: self.env.company.currency_id,
    )
    property_id = fields.Many2one('civora.property', string="Bien d'intérêt", tracking=True)
    agent_id = fields.Many2one('res.users', string="Agent", tracking=True)
    description = fields.Text(string="Description")
    opportunity_id = fields.Many2one('civora.opportunity', string="Opportunité créée", readonly=True)
    visit_request_id = fields.Many2one('civora.visit.request', string="Demande de visite d'origine")
    company_id = fields.Many2one(
        'res.company', string="Societe", required=True, index=True,
        default=lambda self: self.env.company,
    )

    def action_reject(self):
        for lead in self:
            lead.status = 'rejete'

    # ══════════════════════════════════════════════════════════════════
    # Resolution du contact CIVORA
    # ══════════════════════════════════════════════════════════════════
    def _civora_resolve_partner(self):
        """Retourne le contact CIVORA de la piste, en le creant si besoin.

        Une piste issue d'une demande de visite ne porte que contact_name,
        phone et email : le prospect n'existe nulle part dans l'annuaire.
        Sans cette resolution, l'opportunite naissait sans contact rattache.

        Rapprochement volontairement STRICT : email exact, ou telephone
        identique. On n'utilise pas civora_find_duplicates, qui rapproche
        aussi par nom seul — acceptable pour alerter un humain a la saisie,
        beaucoup trop permissif pour une fusion automatique : deux
        homonymes deviendraient un seul contact.

        Retourne le contact, ou False si la piste ne porte pas assez
        d'informations pour creer une fiche exploitable.
        """
        self.ensure_one()
        if self.partner_id:
            return self.partner_id

        Partner = self.env['res.partner']
        name = (self.contact_name or '').strip()
        email = (self.email or '').strip()
        phone = (self.phone or '').strip()

        # Garde-fou : sans nom ni moyen de contact, on creerait une fiche
        # vide qui polluerait l'annuaire.
        if not name or not (email or phone):
            return False

        partner = Partner.browse()

        if email:
            partner = Partner.search([('email', '=ilike', email)], limit=1)

        if not partner and phone:
            digits = ''.join(c for c in phone if c.isdigit())
            if len(digits) >= 8:
                tail = digits[-8:]
                partner = Partner.search([
                    '|', ('phone', 'ilike', tail), ('civora_whatsapp', 'ilike', tail),
                ], limit=1)

        if partner:
            # Contact existant : on complete uniquement ce qui manque.
            # Jamais d'ecrasement — les donnees saisies par l'agence font foi.
            fill = {}
            if email and not partner.email:
                fill['email'] = email
            if phone and not partner.phone:
                fill['phone'] = phone
            if self.agent_id and not partner.civora_agent_id:
                fill['civora_agent_id'] = self.agent_id.id
            if self.source_id and not partner.civora_source_id:
                fill['civora_source_id'] = self.source_id.id
            if not partner.civora_is_contact:
                fill['civora_is_contact'] = True
            if fill:
                partner.write(fill)
            self.partner_id = partner.id
            return partner

        # Creation.
        #
        # RGPD : AUCUN opt-in n'est pose. La mention du formulaire public
        # (« vous acceptez d'etre recontacte au sujet de ce bien ») couvre le
        # rappel commercial sur ce bien precis, pas l'inscription a des
        # campagnes marketing. C'est a l'agence de recueillir ce consentement
        # separement.
        partner = Partner.create({
            'name': name,
            'email': email or False,
            'phone': phone or False,
            'civora_is_contact': True,
            'civora_status': 'qualifie',
            'civora_source_id': self.source_id.id or False,
            'civora_agent_id': self.agent_id.id or False,
            'company_id': self.company_id.id or self.env.company.id,
        })
        self.partner_id = partner.id
        partner.message_post(
            body=Markup("Contact créé automatiquement lors de la qualification "
                        "de la piste <b>%s</b>.") % (self.name or ""),
            subtype_xmlid='mail.mt_note',
        )
        return partner

    def action_qualify(self):
        """Qualifie la piste, cree le contact CIVORA puis l'opportunite."""
        Opp = self.env['civora.opportunity']
        for lead in self:
            if lead.opportunity_id:
                lead.status = 'qualifie'
                continue

            # Le contact est resolu AVANT la creation de l'opportunite :
            # c'est ce qui manquait, l'opportunite naissait orpheline.
            partner = lead._civora_resolve_partner()

            opp = Opp.create({
                'name': lead.name,
                'partner_id': partner.id if partner else False,
                'property_id': lead.property_id.id or False,
                'transaction': lead.transaction or False,
                'expected_amount': lead.budget_max or lead.budget_min or 0.0,
                'score': lead.score,
                'agent_id': lead.agent_id.id or False,
                'lead_id': lead.id,
                'description': lead.description or False,
                'company_id': lead.company_id.id,
            })
            lead.opportunity_id = opp.id
            lead.status = 'qualifie'
        return True

    @api.model
    def create_from_visit_requests(self):
        """Cree des pistes a partir des demandes de visite non encore converties."""
        VR = self.env['civora.visit.request']
        existing = self.search([('visit_request_id', '!=', False)]).mapped('visit_request_id').ids
        reqs = VR.search([('id', 'not in', existing)])
        count = 0
        for r in reqs:
            prop = r.property_id
            self.create({
                'name': "Visite : %s" % (prop.name or r.name or "bien"),
                'contact_name': r.name or False,
                'phone': r.phone or False,
                'email': r.email or False,
                'property_id': prop.id or False,
                'transaction': prop.transaction or False,
                'agent_id': prop.agent_id.id or False,
                'status': 'nouveau',
                'visit_request_id': r.id,
                'company_id': r.company_id.id or self.env.company.id,
            })
            count += 1
        return count

    @api.model
    def action_auto_assign_hot(self, min_score=85):
        """Distribue les pistes chaudes (score >= min_score) sans agent aux
        agents internes de la societe, en round-robin equitable.

        Renvoie un dict :
          {'assigned': N, 'agents': K, 'skipped': M}
        - assigned : nombre de pistes attribuees
        - agents   : nombre d'agents ayant recu au moins une piste
        - skipped  : pistes chaudes non attribuables (aucun agent disponible)

        Regles :
          * On ne touche pas aux pistes deja assignees.
          * On ne touche pas aux pistes rejetees.
          * On se limite a la societe courante.
          * Les pistes deja qualifiees en opportunite sont ignorees.
        """
        company = self.env.company
        agents = self.env['res.users'].sudo().search([
            ('share', '=', False),
            ('active', '=', True),
            ('company_ids', 'in', [company.id]),
        ])
        hot = self.search([
            ('company_id', '=', company.id),
            ('score', '>=', min_score),
            ('agent_id', '=', False),
            ('status', '!=', 'rejete'),
            ('opportunity_id', '=', False),
        ])
        if not hot:
            return {'assigned': 0, 'agents': 0, 'skipped': 0}
        if not agents:
            return {'assigned': 0, 'agents': 0, 'skipped': len(hot)}

        # Round-robin : on commence par l'agent avec le moins de pistes actives,
        # pour lisser la charge existante.
        #
        # read_group() a ete retire de l'ORM en Odoo 18 : on passe par
        # _read_group(domain, groupby, aggregates), qui renvoie des tuples
        # (valeur_de_groupe, agregat) et non plus des dictionnaires.
        active_leads_by_agent = {a.id: 0 for a in agents}
        counts = self.env['civora.lead']._read_group(
            [('company_id', '=', company.id),
             ('agent_id', 'in', agents.ids),
             ('status', 'not in', ['rejete', 'qualifie'])],
            ['agent_id'], ['__count'],
        )
        for agent, count in counts:
            if agent and agent.id in active_leads_by_agent:
                active_leads_by_agent[agent.id] = count

        # Tri stable par charge croissante puis par id (pour deterministe).
        sorted_agents = sorted(agents, key=lambda a: (active_leads_by_agent[a.id], a.id))
        n_agents = len(sorted_agents)

        # On regroupe les pistes par agent avant d'ecrire : une ecriture par
        # agent au lieu d'une par piste. Sur un lot de plusieurs centaines de
        # pistes chaudes, la difference est structurelle.
        batches = {}
        for i, lead in enumerate(hot):
            batches.setdefault(sorted_agents[i % n_agents].id, []).append(lead.id)
        for agent_id, lead_ids in batches.items():
            self.browse(lead_ids).write({'agent_id': agent_id})

        return {
            'assigned': len(hot),
            'agents': len(batches),
            'skipped': 0,
        }
