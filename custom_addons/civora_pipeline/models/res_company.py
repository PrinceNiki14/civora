# -*- coding: utf-8 -*-
from odoo import api, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        Stage = self.env['civora.pipeline.stage'].sudo()
        for company in companies:
            Stage._create_default_stages_for_company(company)
        return companies
