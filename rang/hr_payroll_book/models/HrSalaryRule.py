# -*- encoding: utf-8 -*-

##############################################################################
#
# Copyright (c) 2015 - SIIGCI - jonathan.arra@gmail.com
# Author: Jean Jonathan ARRA
#
# Fichier du module hr_payroll_ci_raport
# ##############################################################################



from odoo import fields, models, _, api
from odoo.tools.safe_eval import safe_eval

class HrPayslipSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'
    _order = 'sequence'

    appears_on_payroll = fields.Boolean(string='Apparaît sur le Livre de paie', default=False,
        help ="Utilisé pour afficher la règle salariale sur le livre de paie")

    @api.model
    def init(self):
        # Custom SQL to update or init data
        self.env.cr.execute("UPDATE hr_salary_rule SET appears_on_payroll = True")


    def _compute_rule(self, localdict):

        """
        :param localdict: dictionary containing the current computation environment
        :return: returns a tuple (amount, qty, rate)
        :rtype: (float, float, float)
        """
        self.ensure_one()
        if self.amount_select == 'fix':
            try:
                return self.amount_fix or 0.0, float(safe_eval(self.quantity, localdict)), 100.0
            except Exception as e:
                self._raise_error(localdict, _("Wrong quantity defined for:"), e)
        if self.amount_select == 'percentage':
            #print(self.amount_percentage_base)
            #inputs = localdict['inputs'].code
            #print(localdict)
            #print(inputs.code)
            try:
                return (float(safe_eval(self.amount_percentage_base, localdict)),
                        float(safe_eval(self.quantity, localdict)),
                        self.amount_percentage or 0.0)
            except Exception as e:
                self._raise_error(localdict, _("Wrong percentage base or quantity defined for:"), e)
        else:  # python code
            try:
                safe_eval(self.amount_python_compute or 0.0, localdict, mode='exec', nocopy=True)
                return float(localdict['result']), localdict.get('result_qty', 1.0), localdict.get('result_rate', 100.0)
            except Exception as e:
                self._raise_error(localdict, _("Wrong python code defined for:"), e)

