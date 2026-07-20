# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import format_amount, format_date
from itertools import groupby


class RapportCnps(models.Model):
    _name = "hr.cnps"

    start_date = fields.Date("Date début", required=True)
    end_date = fields.Date("Date Fin", required=True)
    company_id = fields.Many2one("res.company", "Unité", default=lambda self: self.env.company.id, required=True)
    lot_id = fields.Many2one("hr.payslip.run", "Lot")
    # Nombre de salarier
    n_horaire_journalier_inferieur = fields.Integer("Nombre Horaire, Journalier inférieur")
    n_horaire_journalier_superieur = fields.Integer("Nombre Horaire, Journalier supérieur")
    n_mensuel_inferieur = fields.Integer("Mensuel Mensuel inférieur")
    n_mensuel_superieur1 = fields.Integer("Nombre Mensuel supérieur")
    n_mensuel_superieur2 = fields.Integer("Nombre Mensuel supérieur")
    # Regime retraite
    horaire_journalier_inferieur = fields.Integer("Horaire, Journalier inférieur")
    horaire_journalier_superieur = fields.Integer("Horaire, Journalier supérieur")
    mensuel_retraite_inferieur = fields.Integer("Mensuel inférieur")
    mensuel_retraite_superieur1 = fields.Integer("Mensuel supérieur")
    mensuel_retraite_superieur2 = fields.Integer("Mensuel supérieur")
    # Regime des prestation familiale
    regim_horaire_journalier_inferieur = fields.Integer("Regime Horaire, Journalier inférieur")
    regim_horaire_journalier_superieur = fields.Integer("Regime Horaire, Journalier supérieur")
    regim_mensuel_inferieur = fields.Integer("Regime Mensuel inférieur")
    regim_mensuel_superieur1 = fields.Integer("Regime Mensuel supérieur")
    regim_mensuel_superieur2 = fields.Integer("Regime Mensuel supérieur")

    @api.onchange("lot_id")
    @api.depends("lot_id")
    def onChangeLot(self):
        if self.lot_id:
            self.start_date = self.lot_id.date_start
            self.end_date = self.lot_id.date_end

    def _get_cnps_data(self):
        for rec in self:
            cnps_data_ids = self.env["hr.payslip"].search([('date_from', '>=', rec.start_date),
                                                           ('date_to', '<=', rec.end_date),
                                                           ('payslip_run_id', '=', self.lot_id.id),
                                                           ('company_id', '=', rec.company_id.id)]) if self.lot_id else \
                self.env["hr.payslip"].search([('date_from', '>=', rec.start_date),
                                               ('date_to', '<=', rec.end_date),
                                               ('company_id', '=', rec.company_id.id)])
            if cnps_data_ids:
                cnps_data_list = []
                employee_ids = cnps_data_ids.mapped('employee_id')
                print(employee_ids)
                # Nombre employer
                n_mensuel_inferieur = 0
                n_mensuel_superieur1 = 0
                n_mensuel_superieur2 = 0
                # Regime de retraite
                mensuel_retraite_inferieur = 0
                mensuel_retraite_superieur1 = 0
                mensuel_retraite_superieur2 = 0
                # Regime prestation
                regim_mensuel_inferieur = 0
                regim_mensuel_superieur1 = 0
                regim_mensuel_superieur2 = 0
                for employee_id in employee_ids:
                    if employee_id.type == 'm':
                        emp_data_ids = cnps_data_ids.filtered(lambda x: x.employee_id.id == employee_id.id)
                        for emp_data in emp_data_ids:
                            BASE_CNPS = 0
                            for line in emp_data.line_ids:
                                if line.code == 'BASE_CNPS':
                                    BASE_CNPS += line.amount
                            if BASE_CNPS <= 75000:
                                n_mensuel_inferieur += 1
                                mensuel_retraite_inferieur += BASE_CNPS
                                regim_mensuel_inferieur += 75000
                            if 75000 < BASE_CNPS <= 3375000:
                                n_mensuel_superieur1 += 1
                                mensuel_retraite_superieur1 += BASE_CNPS
                                regim_mensuel_superieur1 += 75000
                            if 3375000 < BASE_CNPS:
                                n_mensuel_superieur2 += 1
                                mensuel_retraite_superieur2 += BASE_CNPS
                                regim_mensuel_superieur2 += 75000
                return {
                    'n_mensuel_inferieur': n_mensuel_inferieur,
                    'n_mensuel_superieur1': n_mensuel_superieur1,
                    'n_mensuel_superieur2': n_mensuel_superieur2,
                    'total_emp': n_mensuel_inferieur + n_mensuel_superieur1 + n_mensuel_superieur2,
                    'mensuel_retraite_inferieur': mensuel_retraite_inferieur,
                    'mensuel_retraite_superieur1': mensuel_retraite_superieur1,
                    'mensuel_retraite_superieur2': mensuel_retraite_superieur2,
                    'total_retraite': mensuel_retraite_inferieur + mensuel_retraite_superieur1 + mensuel_retraite_superieur2,
                    'regim_mensuel_inferieur': regim_mensuel_inferieur,
                    'regim_mensuel_superieur1': regim_mensuel_superieur1,
                    'regim_mensuel_superieur2': regim_mensuel_superieur2,
                    'total_prestation': regim_mensuel_inferieur + regim_mensuel_superieur1 + regim_mensuel_superieur2,
                }
            else:
                return {
                    'n_mensuel_inferieur': 0,
                    'n_mensuel_superieur1': 0,
                    'n_mensuel_superieur2': 0,
                    'total_emp': 0,
                    'mensuel_retraite_inferieur': 0,
                    'mensuel_retraite_superieur1': 0,
                    'mensuel_retraite_superieur2': 0,
                    'total_retraite': 0,
                    'regim_mensuel_inferieur': 0,
                    'regim_mensuel_superieur1': 0,
                    'regim_mensuel_superieur2': 0,
                    'total_prestation': 0,
                }

    def _print_report(self, data):
        return self.env["ir.actions.report"].search([("report_name", "=", 'hr_cnps.report_hr_cnps')],
                                                    limit=1, ).report_action(self, data=data)

    def print_cnps(self):
        self.ensure_one()
        cnps_data = self._get_cnps_data()
        print(cnps_data)
        data = {'ids': self.id,
                'form': self.read(['company_id', 'start_date', 'end_date'])[0],
                'model': 'hr.cnps',
                'n_mensuel_inferieur': cnps_data['n_mensuel_inferieur'],
                'n_mensuel_superieur1': cnps_data['n_mensuel_superieur1'],
                'n_mensuel_superieur2': cnps_data['n_mensuel_superieur2'],
                'total_emp': cnps_data['total_emp'],
                'mensuel_retraite_inferieur': cnps_data['mensuel_retraite_inferieur'],
                'mensuel_retraite_superieur1': cnps_data['mensuel_retraite_superieur1'],
                'mensuel_retraite_superieur2': cnps_data['mensuel_retraite_superieur2'],
                'total_retraite': cnps_data['total_retraite'],
                'regim_mensuel_inferieur': cnps_data['regim_mensuel_inferieur'],
                'regim_mensuel_superieur1': cnps_data['regim_mensuel_superieur1'],
                'regim_mensuel_superieur2': cnps_data['regim_mensuel_superieur2'],
                'total_prestation': cnps_data['total_prestation'],
                'prestation_familiale': cnps_data['total_prestation'] * 5.75 / 100,
                'accident_travail': cnps_data['total_prestation'] * self.company_id.taux_accident_travail / 100,
                'regime_retraite': cnps_data['total_retraite'] * 14 / 100,
                }
        return self._print_report(data)
