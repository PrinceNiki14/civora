# -*- coding: utf-8 -*-

import time
from odoo import api, models
from odoo.tools.misc import format_amount


class ReportHrPayroll(models.AbstractModel):
    _name = 'report.hr_payroll_book.report_payroll_wizard'
    _description = 'HR Payroll Report Wizard'

    @api.model
    def _get_report_values(self, docids, data):
        doc_ids = data['ids']
        docs = self.env[data['model']].browse(data['ids'])
        obj_model = data['model']
        lang_code = self.env.context.get('lang') or 'fr_FR'
        lang = self.env['res.lang']
        lang_id = lang._lang_get(lang_code)
        date_format = lang_id.date_format

        return {
            'doc_ids': doc_ids,
            'doc_model': obj_model,
            'data': data,
            'docs': docs,
            'time': time,
            'format_amount': format_amount,
        }
