# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
from dateutil.relativedelta import relativedelta


class NotificationConfiguration(models.Model):
    _name = "notify.configuration"
    _description = "Configuration de notification"

    name = fields.Char("Nom", required=True)
    day_before = fields.Integer("Nombre de jour avant notification", required=True)
    manager_id = fields.Many2one("res.users", "Manger RH", required=True)
    email_cc = fields.Many2many("res.users", string="Copie à")


class Notification(models.Model):
    _name = "notify.manager"
    _description = "Gestionnaire de notifications"

    def get_contract_end(self):
        contract_ids = self.env['hr.contract'].search([('state', '=', 'open')])
        notify_manager = self.env['notify.configuration'].search([])
        
        day_before = 0
        name = None
        email_to = None
        email_cc_ids = notify_manager.mapped("email_cc")
        email_cc = ''
        for cc in email_cc_ids:
            email_cc += cc.login + ';'
        
        for notify in notify_manager:
            day_before = notify.day_before
            name = notify.manager_id.name
            email_to = notify.manager_id.login
        
        for contract in contract_ids:
            if contract.date_end:
                today = datetime.now().date()
                
                if today == contract.date_end:
                    render_context = {
                        "name": name,
                        "employee": contract.employee_id.name,
                        'contract_date': contract.date_end,
                        'numero_contrat': contract.name,
                    }
                    template = self.env.ref('hr_contract_extension.end_contract_mail_template')
                    mail_body = template._render(render_context)

                    mail_id = self.env['mail.mail'].create({
                        'email_from': email_to,
                        'email_to': email_to,
                        'email_cc': email_cc,
                        'subject': 'Notification de fin de contrat',
                        'body_html': mail_body,
                    })
                    mail_id.send()
                
                if today != contract.date_end:
                    d = contract.date_end - relativedelta(months=day_before)
                    if d == today:
                        render_context = {
                            "name": name,
                            "employee": contract.employee_id.name,
                            'contract_date': contract.date_end,
                            'numero_contrat': contract.name,
                        }
                        template = self.env.ref('hr_contract_extension.end_contract_mail_template')
                        mail_body = template._render(render_context)

                        mail_id = self.env['mail.mail'].create({
                            'email_from': email_to,
                            'email_to': email_to,
                            'email_cc': email_cc,
                            'subject': 'Notification de fin de contrat',
                            'body_html': mail_body,
                        })
                        mail_id.send()
