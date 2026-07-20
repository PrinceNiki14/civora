# -*- coding: utf-8 -*-

from collections import defaultdict
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class HrContract(models.Model):
    _inherit = 'hr.contract'

    def _generate_work_entries(self, date_start, date_stop, force=False):
        self = self.with_context(tracking_disable=True)
        canceled_contracts = self.filtered(lambda c: c.state == 'cancel')
        if canceled_contracts:
            raise UserError(
                _("Sorry, generating work entries from cancelled contracts is not allowed.") + '\n%s' % (
                    ', '.join(canceled_contracts.mapped('name'))))
        
        vals_list = []
        date_start = fields.Datetime.to_datetime(date_start)
        date_stop = datetime.combine(fields.Datetime.to_datetime(date_stop), datetime.max.time())
        self.write({'last_generation_date': fields.Date.today()})

        intervals_to_generate = defaultdict(lambda: self.env['hr.contract'])
        
        self.filtered(lambda c: c.date_generated_from == c.date_generated_to).write({
            'date_generated_from': date_start,
            'date_generated_to': date_start,
        })
        
        for contract in self:
            contract_start = fields.Datetime.to_datetime(contract.date_start)
            contract_stop = datetime.combine(
                fields.Datetime.to_datetime(contract.date_end or datetime.max.date()),
                datetime.max.time()
            )
            
            if date_start > contract_stop or date_stop < contract_start:
                continue
            
            date_start_work_entries = max(date_start, contract_start)
            date_stop_work_entries = min(date_stop, contract_stop)
            
            if force:
                intervals_to_generate[(date_start_work_entries, date_stop_work_entries)] |= contract
                continue

            is_static_work_entries = contract.has_static_work_entries()
            last_generated_from = min(contract.date_generated_from, contract_stop)
            
            if last_generated_from > date_start_work_entries:
                if is_static_work_entries:
                    contract.date_generated_from = date_start_work_entries
                intervals_to_generate[(date_start_work_entries, last_generated_from)] |= contract

            last_generated_to = max(contract.date_generated_to, contract_start)
            if last_generated_to < date_stop_work_entries:
                if is_static_work_entries:
                    contract.date_generated_to = date_stop_work_entries
                intervals_to_generate[(last_generated_to, date_stop_work_entries)] |= contract

        for interval, contracts in intervals_to_generate.items():
            date_from, date_to = interval
            vals_list.extend(contracts._get_work_entries_values(date_from, date_to))

        if not vals_list:
            return self.env['hr.work.entry']

        return self.env['hr.work.entry'].create(vals_list)


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    def action_notify_eric_payslips_ready(self):
        try:
            ir_mail_server = self.env['ir.mail_server']

            body_html = f"""
            <html>
            <body>
                <p>Bonjour Eric,</p>

                <p>Un nouveau lot de fiches de paie est prêt pour validation :</p>

                <ul>
                    <li><strong>Nom du lot :</strong> {self.name}</li>
                    <li><strong>Période :</strong> Du {self.date_start} au {self.date_end}</li>
                    <li><strong>Société :</strong> {self.company_id.name}</li>
                    <li><strong>Nombre de fiches de paie :</strong> {len(self.slip_ids)}</li>
                </ul>

                <p>Merci de procéder à la validation des fiches de paie.</p>

                <p>Cordialement,<br/>
                Le système de paie</p>
            </body>
            </html>
            """

            message = ir_mail_server.build_email(
                email_from=self.env.user.email or 'digital@absgroupe.net',
                email_to='eric.konan@absgroupe.net',
                subject=f'Fiches de paie prêtes pour validation - {self.name}',
                body=body_html,
                subtype='html'
            )

            ir_mail_server.send_email(message)
            self.message_post(body="Notification envoyée avec succès")

        except Exception as e:
            error_message = f"Erreur d'envoi d'e-mail : {str(e)}"
            self.env['mail.mail'].create({
                'subject': 'Erreur d\'envoi de notification',
                'body_html': error_message,
                'email_from': self.env.user.email or 'odoo@votre_entreprise.com',
                'email_to': self.env.user.email
            })
            raise UserError(f"Détails de l'erreur : {error_message}")


class HrPayrollStructure(models.Model):
    _inherit = "hr.payroll.structure"

    number_days = fields.Float(string='Nombres de jours')
    number_hours = fields.Float(string='Nombres d\'heures')


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.constrains('barcode', 'company_id')
    def _check_unique_barcode_per_company(self):
        for record in self:
            if record.barcode:
                existing_product = self.env['product.product'].search([
                    ('barcode', '=', record.barcode),
                    ('company_id', '=', record.company_id.id),
                    ('id', '!=', record.id)
                ], limit=1)

                if existing_product:
                    raise ValidationError(
                        _("Ce code-barres existe déjà dans cette société. Impossible de créer cet article."))
