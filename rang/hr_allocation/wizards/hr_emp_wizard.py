# -*- coding:utf-8 -*-


from odoo import api, fields, models, exceptions


class HrEmpWizard(models.TransientModel):
    _name = 'hr.emp.wizard'

    date_retour_conge = fields.Date(string="Date de rétour congé")
    date_depart_conge = fields.Date(string="Date départ congé")

    def get_date_value(self):
        pass
