# -*- coding:utf-8 -*-


from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    nom = fields.Char("Nom", required=True)
    prenom = fields.Char("Prénom", required=True)

    def name_get(self):
        result = []
        for emp in self:
            if emp.nom and emp.prenom:
                name = emp.nom + ' ' + emp.prenom
                result.append((emp.id, name))
        return result
