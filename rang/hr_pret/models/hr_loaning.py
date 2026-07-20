# -*- coding:utf-8 -*-

import time
from dateutil.relativedelta import relativedelta
from odoo import models, api, fields, _, exceptions
from odoo.tools.misc import format_date


class HrEmpruntLoaning(models.Model):
    _name = 'hr.emprunt.loaning'
    _description = 'Echeanciers de paiement'
    _rec_name = "name"

    name = fields.Char("Libellé de l'emprunt", store=True, compute="_onchange_employee_id")
    employee_id = fields.Many2one('hr.employee', 'Employé', required=True, ondelete='cascade')
    # job_id= fields.Many2one('hr.job', 'Poste', required=True)
    demande_id = fields.Many2one('hr.emprunt.demande', 'Demande', ondelete='cascade')
    echeance_ids = fields.One2many('hr.emprunt.loaning.line', 'loaning_id', 'Echéances')
    montant_emprunt = fields.Float("Montant du prêt", required=True)
    date_emprunt = fields.Date("Date d'emprunt", default=lambda self: fields.Date.today())
    date_debut_remboursement = fields.Date("Date d'échelonnement", required=True)
    date_echeance = fields.Date("Date d'échéance")
    statut_emprunt = fields.Boolean('Reglé')
    total_emprunt = fields.Float('Total à rembourser')
    remaining_emprunt = fields.Float(compte='_remaining_emprunt_percent', string='Taux remb. restant')
    taux = fields.Float("Taux d'emprunt", help="Taux d'intérêt de remboursement", default=0.0)
    option = fields.Selection([('lineaire', 'Linéaire')], 'Option échéance', readonly=False, required=False)
    nb_echeance = fields.Integer("Nombre d'échéance(s)")
    intervalle_echeance = fields.Selection([('week', 'Hebdomadaire'), ('month', 'Mensuel')], 'Intervalle',
                                           readonly=False, default='month')
    notes = fields.Text('Notes')
    state = fields.Selection(
        [
            ('draft', 'Brouillon'),
            ('confirmed', 'Confirmer'),
            ('cancel', 'Annuler')],
        'Status', default='draft')
    type_pret_id = fields.Many2one("hr.emprunt_loaning.rule", "Type prêt")
    company_id = fields.Many2one("res.company", "Entité", default=lambda self: self.env.company)

    @api.depends('employee_id')
    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for rec in self:
            if rec.employee_id:
                rec.name = "Fiche de prêt de %s " % rec.employee_id.name

    @api.onchange('montant_emprunt', 'taux')
    def compute_total_emprunt(self):
        if self.montant_emprunt != 0:
            self.total_emprunt = self.montant_emprunt + (self.montant_emprunt * (self.taux / 100))

    @api.onchange('employee_id', 'total_emprunt', 'option', 'date_debut_remboursement', 'nb_echeance')
    def compute_lineaire_mode(self):
        """
        La fonction qui permet de calculer les écheanciers de paiement en fonction de l'option choisie
        :return: echeance_ids : list
        """
        for rec in self:
            lines = []
            if len(rec.echeance_ids) != 0:
                rec.write(
                    {
                        'echeance_ids': [(5, 0, 0)]
                    })
            else:
                pass
            rec.echeance_ids = lines
            echeance = 0
            if rec.nb_echeance != 0:
                echeance = int(rec.total_emprunt / rec.nb_echeance)
            start = fields.Datetime.from_string(self.date_debut_remboursement)
            name = format_date(self.env, start, date_format="MMMM y")
            print(name)
            # vals = (begin.strftime('%b %Y'), end.strftime('%b %Y'))
            for i in range(rec.nb_echeance):
                value = {
                    # 'name': 'Remboursement de %s/%s' % (start.month, start.year),
                    'name': 'Remboursement de %s' % (start.strftime('%B %Y')),
                    'date_prevu': start,
                    'date_remboursement_echeance': False,
                    'statut_echeance': 'take',
                    'montant': echeance
                }
                lines += [value]
                # if rec.intervalle_echeance == 'month':
                start += relativedelta(months=+1)
                # else:
                #     start += relativedelta(weeks=+1)
            # else:
            #     pass
            print(lines)
            rec.echeance_ids = [(0, 0, d) for d in lines]

    # def echeance_print(self):
    #     """ Print the invoice and mark it as sent, so that we can see more
    #         easily the next step of the workflow
    #     """
    #     self.ensure_one()
    #     self.sent = True
    #     return self.env['report'].get_action(self, 'hr_emprunt.report_echeancier')

    def action_confirmed(self):
        for rec in self:
            rec.write({
                'state': 'confirmed'
            })

    def action_set_draft(self):
        for rec in self:
            rec.write({
                'state': 'draft'
            })

    def action_set_cancel(self):
        for rec in self:
            rec.write({
                'state': 'cancel'
            })


class HrEmpruntLoaningLine(models.Model):
    _name = 'hr.emprunt.loaning.line'
    _description = "Lignes d'echeanciers de paiement"

    def _get_solde_echeance(self):
        for rec in self:
            rec.montant_restant = rec.montant - rec.montant_paye

    def action_suspendre(self):
        email_obj = self.env['mail.template']
        response = email_obj.send_notification('hr_emprunt', self, 'emprunt_suspension_notif')
        if response:
            self.write({'statut_echeance': 'suspendu'})

    name = fields.Char('Nom', required=True)
    date_prevu = fields.Date('Date de prélèvement', required=True)
    date_remboursement_echeance = fields.Date('Date de paiement', required=False)
    montant = fields.Integer("Montant", required=True, default=0)
    montant_paye = fields.Integer('Montant payé', required=False, default=0)
    montant_restant = fields.Integer('Reste à payer', required=False, compute='_get_solde_echeance')
    statut_echeance = fields.Selection([('take', 'A prelever'), ('taked', 'Prélévé'), ('suspendu', 'Suspendu')],
                                       'Status')
    loaning_id = fields.Many2one('hr.emprunt.loaning', 'Écheancier', required=False)


class HrEmpruntLoaningRule(models.Model):
    _name = 'hr.emprunt_loaning.rule'

    name = fields.Char("Nom")
    code = fields.Char("Code")
    company_id = fields.Many2one("res.company", "Entité", default=lambda self: self.env.company)
