# -*- coding: utf-8 -*-
from odoo import api, fields, models

# Types d'interaction — alignes 1:1 sur le front CIVORA (InteractionKind).
CIVORA_INTERACTION_KIND = [
    ('appel', "Appel"),
    ('email', "Email"),
    ('whatsapp', "WhatsApp"),
    ('sms', "SMS"),
    ('rdv', "RDV"),
    ('visite', "Visite"),
    ('note', "Note"),
    ('document', "Document"),
    ('role_change', "Changement de rôle"),
]


class CivoraInteraction(models.Model):
    """Interaction avec un contact (appel, email, WhatsApp, RDV, note...).

    Historise la relation avec un contact CIVORA et alimente la timeline 360°
    (ecran OWL). Aucune vue Odoo : pilote par les client actions CIVORA.
    """
    _name = 'civora.interaction'
    _description = "Interaction contact CIVORA"
    _order = 'date desc, id desc'
    _rec_name = 'title'
    _check_company_auto = True

    contact_id = fields.Many2one(
        'res.partner',
        string="Contact",
        required=True,
        index=True,
        ondelete='cascade',
        check_company=True,
        domain=[('civora_is_contact', '=', True)],
        help="Contact CIVORA concerne par l'interaction.",
    )
    kind = fields.Selection(
        CIVORA_INTERACTION_KIND,
        string="Type",
        required=True,
        default='note',
    )
    title = fields.Char(string="Titre", required=True)
    description = fields.Text(string="Description")
    agent_id = fields.Many2one(
        'res.users',
        string="Agent",
        required=True,
        index=True,
        default=lambda self: self.env.user,
        help="Utilisateur a l'origine de l'interaction.",
    )
    date = fields.Datetime(
        string="Date",
        required=True,
        default=fields.Datetime.now,
    )
    company_id = fields.Many2one(
        'res.company',
        string="Societe",
        required=True,
        index=True,
        default=lambda self: self.env.company,
        help="Societe proprietaire de l'interaction (isolation multi-societe).",
    )

    @api.model_create_multi
    def create(self, vals_list):
        # Herite la societe du contact quand il est rattache a une societe
        # precise (sinon on garde la societe courante de l'utilisateur).
        for vals in vals_list:
            if not vals.get('company_id') and vals.get('contact_id'):
                contact = self.env['res.partner'].browse(vals['contact_id'])
                if contact.company_id:
                    vals['company_id'] = contact.company_id.id
        return super().create(vals_list)
