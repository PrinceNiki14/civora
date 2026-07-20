# -*- coding:utf-8 -*-


from odoo import api, fields, models, exceptions


class HrPayrollInverse(models.TransientModel):
    _name = 'hr.payroll.inverse'

    # def _get_lines(self):
    #     active_id = self._context.get('active_id')
    #     print(active_id)
    #     if active_id:
    #         slip = self.env['hr.payslip'].browse(active_id)
    #         if slip:
    #             print(slip.input_line_ids)
    #             input_list = []
    #             for input in slip.input_line_ids:
    #                 input_list.append({'rule_id': input.id})
    #             print(input_list)
    #             self.line_ids = [(0, 0, d) for d in input_list]
    #             print(self.line_ids)
    #             #return [(0, 0, {'rule_id': input.id})for input in slip.input_line_ids]
    #
    #     #return []

    def _get_lines(self):
        active_id = self._context.get('active_id')
        if active_id:
            slip = self.env['hr.payslip'].browse(active_id)
            if slip:
                return [(0, 0, {'rule_id': inp.input_type_id.id}) for inp in slip.input_line_ids]
        return []

    def computeSlip(self):
        payslip = self.env['hr.payslip'].browse(self._context.get('active_id'))
        #input = self.line_ids.filtered(lambda l: l.is_used).rule_id
        input = payslip.input_line_ids.filtered(lambda l: l.input_type_id.code == 'SURSA')
        # #input = self.env['hr.payslip.input.type'].search([('code', '=', 'SURSA')])
        # print('input', input)
        amount = 0
        if payslip:
            payslip.compute_sheet()
            if self.type_calcul == 'net':
                amount = self.montant - payslip.net_wage
            elif self.type_calcul == 'brut_total':
                amount = self.montant - payslip.brut_total
            else:
                amount = self.montant - payslip.brut
            while amount != 0:
                print(amount)
                amount_input = input.amount + amount
                input.write({'amount': amount_input})
                payslip.sudo().compute_sheet()
                if self.type_calcul == 'net':
                    amount = self.montant - payslip.net_wage
                elif self.type_calcul == 'brut_total':
                    amount = self.montant - payslip.brut_total
                else:
                    amount = self.montant - payslip.brut

    line_ids = fields.One2many('hr.payroll.inverse.line', 'inverse_id', 'Lignes', required=False, default=_get_lines)
    type_calcul = fields.Selection([('brut', 'Par le brut'), ('brut_total', 'Par le brut Total'),
                                    ('net', 'Par le net')], 'Méthode de calcul', required=True)
    montant = fields.Integer("Montant")


class HrPayrollInverseLine(models.TransientModel):
    _name = 'hr.payroll.inverse.line'

    #rule_id = fields.Many2one('hr.payslip.input', 'Règle salariale', required=False)
    rule_id = fields.Many2one('hr.payslip.input.type', 'Règle salariale', required=False)
    is_used = fields.Boolean("Variable Ã  utilisée", default=False)
    inverse_id = fields.Many2one('hr.payroll.inverse', 'Calcul inverse', required=False)
