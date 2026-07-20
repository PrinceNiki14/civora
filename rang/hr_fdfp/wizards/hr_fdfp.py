# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import format_amount, format_date
from itertools import groupby


class RapportCmu(models.Model):
    _name = "hr.fdfp"

    start_date = fields.Date("Date début", required=True)
    end_date = fields.Date("Date Fin", required=True)
    company_id = fields.Many2one("res.company", "Unité", default=lambda self: self.env.company.id, required=True)
    lot_id = fields.Many2one("hr.payslip.run", "Lot")
    line_ids = fields.One2many("hr.fdfp.line", "hr_fdfp_id")

    @api.onchange("lot_id")
    @api.depends("lot_id")
    def onChangeLot(self):
        if self.lot_id:
            self.start_date = self.lot_id.date_start
            self.end_date = self.lot_id.date_end

    def _get_fdfp_data(self):
        for rec in self:
            rec.env['hr.fdfp.line'].search([]).sudo().unlink()
            fdfp_data_ids = self.env["hr.payslip"].search([('date_from', '>=', rec.start_date),
                                                           ('date_to', '<=', rec.end_date),
                                                           ('payslip_run_id', '=', self.lot_id.id),
                                                           (
                                                               'company_id', '=',
                                                               rec.company_id.id)]) if self.lot_id else (
                self.env["hr.payslip"].search([('date_from', '>=', rec.start_date),
                                               ('date_to', '<=', rec.end_date),
                                               ('company_id', '=', rec.company_id.id)]))
            if fdfp_data_ids:
                fdfp_data_list = []
                line_ids = fdfp_data_ids.mapped('line_ids')
                TAXEFPR_line = line_ids.filtered(lambda x: x.code == 'TAXEFPR')
                TAXEFPC_line = line_ids.filtered(lambda x: x.code == 'TAXEFPC')
                TAXEAP_line = line_ids.filtered(lambda x: x.code == 'TAXEAP')
                TAXEFPR = 0
                TAXEFPC = 0
                TAXEAP = 0
                BASE = 0
                TAXEFPR_name = self.env["hr.salary.rule"].search([('code', '=', 'TAXEFPR')], limit=1).name
                TAXEFPC_name = self.env["hr.salary.rule"].search([('code', '=', 'TAXEFPC')], limit=1).name
                TAXEAP_name = self.env["hr.salary.rule"].search([('code', '=', 'TAXEAP')], limit=1).name
                for line in TAXEFPR_line:
                    TAXEFPR += line.total
                for line in TAXEFPC_line:
                    TAXEFPC += line.total
                for line in TAXEAP_line:
                    TAXEAP += line.total
                for line in line_ids:
                    if line.code == 'BASE_IMP':
                        BASE += line.total
                # if TAXEFPR_name:
                #     fdfp_data_list.append({
                #         'name': TAXEFPR_name,
                #         'amount': TAXEFPR
                #     })
                # if TAXEFPC_name:
                #     fdfp_data_list.append({
                #         'name': TAXEFPC_name,
                #         'amount': TAXEFPC
                #     })
                # if TAXEAP_name:
                #     fdfp_data_list.append({
                #         'name': TAXEAP_name,
                #         'amount': TAXEAP
                #     })
                total_fdfp = TAXEFPC + TAXEFPR + TAXEAP
                print(fdfp_data_list)
                self.line_ids = [(0, 0, d) for d in fdfp_data_list]
                return {
                    'TAXEAP': TAXEAP,
                    'TAXEFPC': TAXEFPC,
                    'TAXEFPR': TAXEFPR,
                    'BASE': BASE,
                }
            else:
                return {
                    'TAXEAP': 0,
                    'TAXEFPC': 0,
                    'TAXEFPR': 0,
                    'BASE': 0,
                }

    def _print_report(self, data):
        return self.env["ir.actions.report"].search([("report_name", "=", 'hr_fdfp.report_hr_fdfp')],
                                                    limit=1, ).report_action(self, data=data)

    def print_fdfp(self):
        self.ensure_one()
        fdfp_data = self._get_fdfp_data()
        data = {'ids': self.id,
                'form': self.read(['company_id', 'start_date', 'end_date'])[0],
                'model': 'hr.fdfp',
                'TAXEAP': fdfp_data['TAXEAP'],
                'TAXEFPC': fdfp_data['TAXEFPC'],
                'TAXEFPR': fdfp_data['TAXEFPR'],
                'BASE': fdfp_data['BASE'],
                }
        return self._print_report(data)


class RapportfdfpLine(models.Model):
    _name = "hr.fdfp.line"

    name = fields.Char()
    amount = fields.Float()
    hr_fdfp_id = fields.Many2one("hr.fdfp")
