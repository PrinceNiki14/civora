# -*- coding: utf-8 -*-
"""Bibliotheque de modeles de workflows CIVORA.

Un modele est une definition prete a l'emploi : on le "deploie" pour creer
un vrai workflow (avec ses etapes) que l'agence peut ensuite modifier.
"""
from odoo import models, fields, api
from odoo.exceptions import UserError

from .civora_workflow import WORKFLOW_CATEGORY, TRIGGER_TYPE
from .civora_workflow_step import STEP_KIND, STEP_ICON


class CivoraWorkflowTemplate(models.Model):
    _name = "civora.workflow.template"
    _description = "Modèle de workflow"
    _order = "sequence, name"

    name = fields.Char(string="Nom", required=True)
    description = fields.Text(string="Description")
    category = fields.Selection(
        WORKFLOW_CATEGORY, string="Catégorie", required=True, default="locatif",
    )
    trigger_description = fields.Char(string="Déclencheur")
    trigger_type = fields.Selection(TRIGGER_TYPE, string="Type de déclencheur", default="event")
    step_ids = fields.One2many(
        "civora.workflow.template.step", "template_id", string="Étapes",
    )
    step_count = fields.Integer(string="Nb étapes", compute="_compute_counts", store=True)
    deployed_count = fields.Integer(
        string="Workflows déployés", compute="_compute_deployed_count",
    )
    is_active = fields.Boolean(string="Disponible", default=True)
    sequence = fields.Integer(default=10)
    time_saved_hours = fields.Integer(
        string="Temps économisé estimé (h)", default=0,
        help="Valeur pre-remplie sur le workflow cree a partir de ce modele.",
    )
    company_id = fields.Many2one("res.company", string="Société")

    @api.depends("step_ids")
    def _compute_counts(self):
        for rec in self:
            rec.step_count = len(rec.step_ids)

    def _compute_deployed_count(self):
        # formatted_read_group remplace read_group (supprime en Odoo 19).
        groups = self.env["civora.workflow"].formatted_read_group(
            [("template_id", "in", self.ids)], groupby=["template_id"], aggregates=["__count"],
        )
        mapped = {
            (g["template_id"][0] if g["template_id"] else False): g["__count"]
            for g in groups
        }
        for rec in self:
            rec.deployed_count = mapped.get(rec.id, 0)

    def action_toggle_active(self):
        for rec in self:
            rec.is_active = not rec.is_active
        return True

    # ------------------------------------------------------------------
    @api.model
    def get_template_library(self):
        categories = dict(WORKFLOW_CATEGORY)
        templates = self.search([("is_active", "=", True)])
        deployed = set(self.env["civora.workflow"].search([]).mapped("template_id").ids)
        return [{
            "id": t.id,
            "name": t.name,
            "description": t.description or "",
            "category": t.category,
            "category_label": categories.get(t.category, ""),
            "trigger_description": t.trigger_description or "",
            "step_count": t.step_count,
            "time_saved_hours": t.time_saved_hours,
            "deployed": t.id in deployed,
            "steps": [{
                "kind": s.kind,
                "kind_label": dict(STEP_KIND).get(s.kind, ""),
                "icon": STEP_ICON.get(s.kind, "fa-cog"),
                "name": s.name,
                "detail": s.detail or "",
                "sequence": s.sequence,
            } for s in t.step_ids.sorted(lambda s: (s.sequence, s.id))],
        } for t in templates]

    def action_deploy(self, activate=True):
        """Cree un workflow reel a partir du modele et renvoie son id."""
        self.ensure_one()
        Workflow = self.env["civora.workflow"]
        title = self.name
        suffix = 2
        while Workflow.search_count([
            ("title", "=", title),
            ("company_id", "=", self.env.company.id),
        ]):
            title = "%s (%s)" % (self.name, suffix)
            suffix += 1
        workflow = Workflow.create({
            "title": title,
            "description": self.description,
            "category": self.category,
            "trigger_description": self.trigger_description,
            "trigger_type": self.trigger_type,
            "time_saved_hours": self.time_saved_hours,
            "template_id": self.id,
            "status": "brouillon",
        })
        for step in self.step_ids.sorted(lambda s: (s.sequence, s.id)):
            self.env["civora.workflow.step"].create({
                "workflow_id": workflow.id,
                "kind": step.kind,
                "name": step.name,
                "detail": step.detail,
                "sequence": step.sequence,
            })
        if activate:
            if not workflow.step_ids.filtered(lambda s: s.kind == "declencheur"):
                raise UserError(
                    "Le modèle « %s » ne définit pas de déclencheur." % self.name
                )
            workflow.status = "actif"
        return workflow.id


class CivoraWorkflowTemplateStep(models.Model):
    _name = "civora.workflow.template.step"
    _description = "Étape de modèle de workflow"
    _order = "sequence, id"

    template_id = fields.Many2one(
        "civora.workflow.template", string="Modèle", required=True, ondelete="cascade",
    )
    name = fields.Char(string="Libellé", required=True)
    detail = fields.Char(string="Détail")
    kind = fields.Selection(STEP_KIND, string="Type", required=True, default="action")
    sequence = fields.Integer(default=10)
