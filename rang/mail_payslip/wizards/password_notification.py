# -*- coding:utf-8 -*-

from odoo import models, fields, _


class MailPasswordNotifcationWizard(models.TransientModel):
    _name = 'mail.password.notification_wizard'
    _description = "Mail password notificaiton"

    def _get_employees(self):
        return self.env['hr.employee'].browse(self._context.get('active_ids'))

    employee_ids = fields.Many2many("hr.employee", string="Employees", required=True, default=_get_employees)

    def send_email(self):
        for emp in self.employee_ids:
            mail_id = self.env['mail.mail'].create({
                'email_from': self.env.company.notification_email,
                'email_to': emp.work_email,
                'subject': 'Votre mot de passe pour les bulletins',
                'body_html': _('Hello,<br/><br/>Votre mot de passe pour ouvrir les bulletins est : <strong>%s</strong>.'
                               '<br/><br/><font style="font-size: 12px;">** Veuillez le garder précieusement et supprimer le message pour plus de sécurité.'
                               '<br/>Cordialement.</font>') % emp.password_payslip
            })
            mail_id.send()


