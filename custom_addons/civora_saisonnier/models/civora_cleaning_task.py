# -*- coding: utf-8 -*-
from odoo import models, fields


class CivoraCleaningTask(models.Model):
    _name = 'civora.cleaning.task'
    _description = 'Tâche de ménage'
    _order = 'date asc, id desc'
    _check_company_auto = True

    reservation_id = fields.Many2one(
        'civora.reservation', string="Réservation", ondelete='cascade')
    property_id = fields.Many2one(
        'civora.property', string="Bien", required=True, check_company=True)
    date = fields.Date(string="Date", required=True)
    time_slot = fields.Selection([
        ('matin', 'Matin (8h-12h)'),
        ('apres_midi', 'Après-midi (13h-17h)'),
    ], string="Créneau", default='matin')
    assigned_to = fields.Many2one(
        'res.partner', string="Assigné à")
    state = fields.Selection([
        ('a_planifier', 'À planifier'),
        ('planifie', 'Planifié'),
        ('en_cours', 'En cours'),
        ('termine', 'Terminé'),
    ], string="Statut", default='a_planifier', required=True)
    checklist_done = fields.Boolean(string="Checklist validée")
    notes = fields.Text(string="Notes")
    company_id = fields.Many2one(
        'res.company', string="Société",
        default=lambda self: self.env.company, required=True)

    def action_start(self):
        self.write({'state': 'en_cours'})

    def action_done(self):
        self.write({'state': 'termine', 'checklist_done': True})
