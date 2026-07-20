# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _
from PyPDF2 import PdfFileWriter, PdfFileReader
from odoo.tools.misc import format_date
from datetime import datetime, date
import time
import io
import base64

class mail_payslip_wizard(models.TransientModel):
    _name = 'mail.payslip.wizard'
    _description = "Mail Payslip"

    def _get_payslips(self):
        return self.env['hr.payslip'].browse(self._context.get('active_ids'))

    payslip_ids = fields.Many2many('hr.payslip', string="Payslips", required=True,
        default=_get_payslips)

    def generte_encrypted_pdf(self, payslip, password):
        report = self.env.ref('hr_payroll.action_report_payslip')
        #pdf_string = report.sudo()._render_qweb_pdf([payslip.id])[0]
        print('payslip', payslip)
        pdf_string = self.env['ir.actions.report'].sudo()._render_qweb_pdf(report, payslip.id)[0]

        # write the payslip PDF content into a "memory file"
        unencrypted_file = io.BytesIO()
        unencrypted_file.write(pdf_string)

        # make a copy of the PDF file, and encrypt it
        pdf_file_reader = PdfFileReader(unencrypted_file)
        pdf_file_writer = PdfFileWriter()
        for page in pdf_file_reader.pages:
            pdf_file_writer.addPage(page)
        pdf_file_writer.encrypt(password)

        # write the encrypted payslip PDF content into a "memory file"
        encrypted_file = io.BytesIO()
        pdf_file_writer.write(encrypted_file)
        unencrypted_file.close()

        return encrypted_file

    def send_via_mail(self):
        if not self.env.user.email:
            raise exceptions.UserError(
                _('Email required, Please configure your mail address in '
                  'Preferences to be able to send outgoing mails.'))

        for payslip in self.payslip_ids:
            if not payslip.employee_id.work_email:
                pass
            # generate a password to be set on the encrypted payslip 
            # last 4 digits of the employee's identification number or '2021'
            initial_name = "".join(x[0] for x in payslip.employee_id.name.split())

            password = payslip.employee_id.password_payslip
            encrypted_payslip_pdf = self.generte_encrypted_pdf(payslip, str(password))
            self.create_mail_with_attachment(payslip, encrypted_payslip_pdf)

    def create_mail_with_attachment(self, payslip, payslip_pdf):
        """create the mail with attachment"""
        month_year = format_date(self.env, payslip.date_from, date_format="MMMM y")
        render_context = {
            "name": payslip.employee_id.name,
            "month_year": month_year,
            "user_name": self.env.user.name,
        }
        template = self.env.ref('mail_payslip.payslip_mail_template')
        #mail_body = template.render(render_context, engine='ir.qweb', minimal_qcontext=True)

        mail_id = self.env['mail.mail'].create({
            'email_from': self.env.company.notification_email,
            'email_to': payslip.employee_id.work_email,
            'subject': 'Votre bulletin de salaire de %s' % month_year,
            'body_html': _('Bonjour %s, <br/><br/>'
                           'Veuillez trouver en pièce jointe votre bulletin de salaire du mois der <t t-esc="month_year"/>.'
                           '<br/><br/>Cordialement,<br/> %s.') % (payslip.employee_id.name, self.env.user.name),
        })
        attachment = self.env['ir.attachment'].create({
            'name': "payslip.pdf",
            'datas': base64.b64encode(payslip_pdf.getvalue()),
            'res_model': 'mail.mail',
            'res_id': mail_id.id,
        })
        mail_id.write({'attachment_ids': [(6, 0, [attachment.id])]})
        mail_id.send()
        payslip_pdf.close()

    def action_mail_payslip_send(self):
        return {
            'name': 'Envoyer le bulletin par mail',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            "view_type": "form",
            'res_model': 'mail.payslip.wizard',
            'target': 'new',
            'view_id': self.env.ref('mail_payslip.mail_payslip_wizard_form_view').id,
            #'context': {'active_id': self.id},
        }

    def action_register_payment(self):
        ''' Open the account.payment.register wizard to pay the selected journal entries.
        :return: An action opening the account.payment.register wizard.
        '''
        return {
            'name': _('Register Payment'),
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'context': {
                'active_model': 'account.move',
                'active_ids': self.ids,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }