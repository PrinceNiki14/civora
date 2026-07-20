# -*- coding: utf-8 -*-

from datetime import datetime
import time
from odoo import api, models
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT, format_amount

from itertools import groupby


class ReportHrCgrae(models.AbstractModel):
    _name = 'report.hr_cmu.report_hr_cmu'

    @api.model
    def _get_report_values(self, docids, data):
        ids = data['ids']
        doc_ids = ids
        docs = self.env['hr.cmu.wizard'].browse(data['ids'])
        obj_model = 'hr.cmu.wizard'
        return {
            'doc_ids': doc_ids,
            'doc_model': obj_model,
            'data': data,
            'docs': docs,
            'time': time,
            'format_amount': format_amount,
        }