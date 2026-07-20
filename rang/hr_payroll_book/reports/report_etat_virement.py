# -*- coding: utf-8 -*-

from datetime import datetime
import time
from odoo import api, models
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT, format_amount

from itertools import groupby


class ReportOrdreVirement(models.AbstractModel):
    _name = 'report.hr_payroll_book.report_ordre_virement'

    @api.model
    def _get_report_values(self, docids, data):
        print(data)
        doc_ids = data['ids']
        docs = self.env[data['model']].browse(data['ids'])
        obj_model = data['model']
        lang_code = self.env.context.get('lang') or 'fr_FR'
        lang = self.env['res.lang']
        lang_id = lang._lang_get(lang_code)
        date_format = lang_id.date_format
        report_obj = self.env['ir.actions.report']
        report = report_obj._get_report_from_name('hr_payroll_book.report_ordre_virement')

        return {
            'doc_ids': doc_ids,
            'doc_model': obj_model,
            'data': data,
            'docs': docs,
            'time': time,
            'format_amount': format_amount,
        }

