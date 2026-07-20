# -*- coding: utf-8 -*-

from datetime import datetime
import time
from odoo import api, models
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT, format_amount

from itertools import groupby


class ReportHrCgrae(models.AbstractModel):
    _name = 'report.hr_cotisation_emp.report_cotisation_emp'

    @api.model
    def _get_report_values(self, docids, data):
        ids = data['ids']
        doc_ids = ids
        docs = self.env['hr.cotisation.emp'].browse(data['ids'])
        obj_model = 'hr.cotisation.emp'
        return {
            'doc_ids': doc_ids,
            'doc_model': obj_model,
            'data': data,
            'docs': docs,
            'time': time,
            'format_amount': format_amount,
        }