# -*- coding: utf-8 -*-

import qrcode
import base64
from io import BytesIO
from odoo import fields, models, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    qr_code = fields.Binary("QR Code", compute="_compute_qr_code", store=False)
    hourly_cost = fields.Float(string="Hourly Cost")

    @api.depends('name', 'job_id', 'work_phone', 'matricule_cnps')
    def _compute_qr_code(self):
        for employee in self:
            data = f"Nom et prenoms: {employee.name}, Poste: {employee.job_id.name if employee.job_id else ''}, Mobile: {employee.work_phone}, N° CNPS: {employee.matricule_cnps}"
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill='black', back_color='white')
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            qr_image = base64.b64encode(buffer.getvalue())
            employee.qr_code = qr_image
