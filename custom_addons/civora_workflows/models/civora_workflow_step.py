# -*- coding: utf-8 -*-
"""Etapes d'un workflow CIVORA.

Une etape n'est pas une "tache a cocher" : c'est un noeud du graphe
d'automatisation (declencheur, action, delai, condition, action IA,
notification). C'est ce modele qui alimente le builder cote front.
"""
from odoo import models, fields, api

STEP_KIND = [
    ("declencheur", "Déclencheur"),
    ("action", "Action"),
    ("delai", "Délai"),
    ("condition", "Condition"),
    ("action_ia", "Action IA"),
    ("notification", "Notification"),
]

# Icone FontAwesome 4 (Odoo n'embarque que FA4) par type d'etape.
STEP_ICON = {
    "declencheur": "fa-bolt",
    "action": "fa-cog",
    "delai": "fa-clock-o",
    "condition": "fa-code-fork",
    "action_ia": "fa-magic",
    "notification": "fa-bell-o",
}


class CivoraWorkflowStep(models.Model):
    _name = "civora.workflow.step"
    _description = "Etape de workflow"
    _order = "sequence, id"

    workflow_id = fields.Many2one(
        "civora.workflow", string="Workflow", required=True, ondelete="cascade",
        index=True,
    )
    name = fields.Char(string="Libellé", required=True)
    detail = fields.Char(string="Détail")
    kind = fields.Selection(
        STEP_KIND, string="Type", required=True, default="action",
    )
    sequence = fields.Integer(string="Ordre", default=10)
    company_id = fields.Many2one(
        "res.company", string="Société",
        related="workflow_id.company_id", store=True,
    )

    kind_label = fields.Char(string="Type (libellé)", compute="_compute_kind_label")
    icon = fields.Char(string="Icône", compute="_compute_kind_label")

    @api.depends("kind")
    def _compute_kind_label(self):
        labels = dict(STEP_KIND)
        for rec in self:
            rec.kind_label = labels.get(rec.kind, "")
            rec.icon = STEP_ICON.get(rec.kind, "fa-cog")

    def to_dict(self):
        self.ensure_one()
        return {
            "id": self.id,
            "kind": self.kind,
            "kind_label": self.kind_label,
            "icon": self.icon,
            "name": self.name or "",
            "detail": self.detail or "",
            "sequence": self.sequence,
        }


class CivoraWorkflowExecution(models.Model):
    """Historique d'execution d'un workflow.

    Chaque run (reel ou test) laisse une trace : c'est ce qui alimente
    "Dernieres executions", le taux de succes et la ligne "Derniere
    execution" du bloc TOP AUTOMATION.
    """

    _name = "civora.workflow.execution"
    _description = "Exécution de workflow"
    _order = "execution_date desc, id desc"

    workflow_id = fields.Many2one(
        "civora.workflow", string="Workflow", required=True, ondelete="cascade",
        index=True,
    )
    name = fields.Char(string="Message", required=True)
    execution_date = fields.Datetime(
        string="Date", required=True, default=lambda self: fields.Datetime.now(),
    )
    result = fields.Selection([
        ("succes", "Succès"),
        ("partiel", "Partiel"),
        ("echec", "Échec"),
    ], string="Résultat", default="succes", required=True)
    is_test = fields.Boolean(string="Exécution de test")
    steps_done = fields.Integer(string="Étapes exécutées")
    user_id = fields.Many2one(
        "res.users", string="Déclenché par", default=lambda self: self.env.user,
    )
    company_id = fields.Many2one(
        "res.company", string="Société",
        related="workflow_id.company_id", store=True,
    )
