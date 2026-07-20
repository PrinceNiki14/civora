# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    password_payslip = fields.Char("Mot de passe pour les bulletins", char=255, required=False)

    def action_mail_payslip_send(self):
        return {
            'name': _('Envoyer le mot de passe via mail'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            "view_type": "form",
            'res_model': 'mail.password.notification_wizard',
            'target': 'new',
            'view_id': self.env.ref('mail_payslip.mail_pawword_notifwizard_form_view').id,
            'context': {
                'active_model': 'hr.employee',
                'active_ids': self.ids,
            },
        }