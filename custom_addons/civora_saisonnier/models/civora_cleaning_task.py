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
    task_type = fields.Selection([
        ('menage', 'Ménage'),
        ('maintenance', 'Maintenance'),
        ('inspection', 'Inspection'),
    ], string="Type", default='menage', required=True)
    priority = fields.Selection([
        ('basse', 'basse'),
        ('moyenne', 'moyenne'),
        ('haute', 'haute'),
    ], string="Priorité", default='moyenne', required=True)
    assigned_to = fields.Many2one(
        'res.partner', string="Assigné à")
    staff_id = fields.Many2one(
        'civora.cleaning.staff', string="Intervenant")
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


class CivoraCleaningStaff(models.Model):
    """Intervenant terrain (menage, maintenance, inspection)."""

    _name = 'civora.cleaning.staff'
    _description = "Intervenant terrain saisonnier"
    _order = 'sequence, name'

    name = fields.Char(string="Intervenant", required=True)
    speciality = fields.Char(string="Spécialité", default="Ménage")
    rating = fields.Float(string="Note", default=0.0)
    task_ids = fields.One2many('civora.cleaning.task', 'staff_id', string="Tâches")
    task_count = fields.Integer(string="Tâches", compute='_compute_task_count')
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        'res.company', string="Société", default=lambda self: self.env.company)

    def _compute_task_count(self):
        for rec in self:
            rec.task_count = len(rec.task_ids)


class CivoraSeasonalInventory(models.Model):
    """Consommables et linge suivis par bien / par agence."""

    _name = 'civora.seasonal.inventory'
    _description = "Inventaire & consommables saisonnier"
    _order = 'sequence, name'

    name = fields.Char(string="Article", required=True)
    quantity = fields.Integer(string="Quantité", default=0)
    threshold = fields.Integer(string="Seuil d'alerte", default=10)
    is_low = fields.Boolean(string="Sous le seuil", compute='_compute_is_low')
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        'res.company', string="Société", default=lambda self: self.env.company)

    def _compute_is_low(self):
        for rec in self:
            rec.is_low = rec.quantity <= rec.threshold
