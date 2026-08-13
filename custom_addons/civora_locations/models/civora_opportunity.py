# -*- coding: utf-8 -*-
from markupsafe import Markup

from odoo import api, fields, models


class CivoraOpportunity(models.Model):
    """Extension de civora.opportunity pour le pont vers les baux.

    Chaque opportunité de type 'location' gagnée peut donner naissance à un ou
    plusieurs baux CIVORA. Le lien est optionnel — la création est déclenchée
    manuellement par l'agent (pas de création silencieuse) mais un message est
    posté dans le chatter dès que les conditions sont réunies pour signaler
    l'action à faire.
    """
    _inherit = 'civora.opportunity'

    lease_ids = fields.One2many(
        'civora.lease', 'opportunity_id',
        string="Baux générés",
        help="Baux CIVORA créés à partir de cette opportunité.",
    )
    lease_count = fields.Integer(
        string="Nb baux", compute='_compute_lease_count',
    )

    @api.depends('lease_ids')
    def _compute_lease_count(self):
        for opp in self:
            opp.lease_count = len(opp.lease_ids)

    def write(self, vals):
        """Poste un message dans le chatter quand une opportunité de location
        passe en 'gagnée' sans avoir de bail lié — pour inciter l'agent à
        déclencher manuellement la création du bail.
        """
        # Snapshot avant modification pour détecter les transitions is_won
        was_won = {opp.id: opp.is_won for opp in self}
        res = super().write(vals)
        for opp in self:
            became_won = (not was_won.get(opp.id, False)) and opp.is_won
            if became_won and opp.transaction == 'location' and not opp.lease_ids:
                opp.message_post(
                    body=Markup(
                        "🎯 <b>Opportunité de location gagnée</b> — un bail peut "
                        "être créé à partir de cette opportunité. "
                        "Ouvrez la fiche 360° du prospect pour lancer la création."
                    ),
                    subject="Opportunité prête pour bail",
                )
        return res

    def action_prepare_lease_vals(self):
        """Retourne un dict de valeurs préfillées pour créer un bail depuis
        cette opportunité. Utilisé par le LeaseDrawer en mode 'defaultOpportunityId'.

        Ne crée PAS le bail — c'est le drawer qui déclenche la création côté OWL,
        avec possibilité d'ajuster les valeurs avant sauvegarde.
        """
        self.ensure_one()
        return {
            'opportunity_id': self.id,
            'property_id': self.property_id.id if self.property_id else False,
            'tenant_id': self.partner_id.id if self.partner_id else False,
            'agent_id': self.agent_id.id if self.agent_id else False,
            'rent': self.expected_amount or 0.0,
            'property_name': self.property_id.name if self.property_id else "",
            'tenant_name': self.partner_id.name if self.partner_id else "",
            'agent_name': self.agent_id.name if self.agent_id else "",
        }
