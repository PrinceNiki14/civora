# -*- coding:utf-8 -*-

from odoo import api, fields, models


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    @api.depends('type')
    def _get_tranche(self):
        for record in self:
            type_search = 'm'
            if record.type != 'm':
                type_search = 'j'
            result = self.env['hr.cnps.setting'].search([('type', '=', type_search)], limit=1)
            record.tranche_id = result.id if result else False

    tranche_id = fields.Many2one('hr.cnps.setting', 'Tranche', compute='_get_tranche', store=True)
