# -*- coding:utf-8 -*-

from odoo import models, fields, api, exceptions, _
import secrets


class ResCompany(models.Model):
    _inherit = "res.company"

    notification_email = fields.Char("Email de notification", required=False, default="noreply@bdo-fwa.com")

    def generate_password(self):
        employees = self.env['hr.employee'].search([('company_id', '=', self.id)])
        if employees:
            for emp in employees:
                if emp.password_payslip:
                    continue
                else:
                    password = secrets.token_urlsafe(10)
                    emp.password_payslip = password
        return
