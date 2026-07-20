# -*- coding: utf-8 -*-
import time
import babel
from odoo import models, fields, api, tools, _
from datetime import datetime
from odoo.tools.misc import format_date


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def action_mail_payslip_send(self):
        return {
            'name': _('Envoyer le bulletin par mail'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            "view_type": "form",
            'res_model': 'mail.payslip.wizard',
            'target': 'new',
            'view_id': self.env.ref('mail_payslip.mail_payslip_wizard_form_view').id,
            'context': {
                'active_model': 'hr.payslip',
                'active_ids': self.ids,
            },
        }


