from odoo import models, fields, api


class CivoraWorkflowTemplate(models.Model):
    _name = "civora.workflow.template"
    _description = "Modele de workflow"
    _order = "sequence, name"

    name = fields.Char(string="Nom", required=True)
    description = fields.Text(string="Description")
    category = fields.Selection([
        ("vente", "Vente"),
        ("location", "Location"),
        ("gestion", "Gestion"),
        ("administratif", "Administratif"),
    ], string="Categorie", required=True, default="gestion")
    step_ids = fields.One2many(
        "civora.workflow.template.step", "template_id", string="Etapes",
    )
    step_count = fields.Integer(compute="_compute_step_count", string="Nb etapes")
    workflow_count = fields.Integer(compute="_compute_workflow_count", string="Workflows actifs")
    is_active = fields.Boolean(string="Actif", default=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        "res.company", string="Societe",
        default=lambda self: self.env.company,
    )

    trigger_type = fields.Selection([
        ("event", "Evenement"),
        ("schedule", "Planifie"),
        ("condition", "Condition IA"),
        ("manual", "Manuel"),
    ], string="Type de declencheur", default="event")
    trigger_description = fields.Char(string="Declencheur")
    execution_count = fields.Integer(string="Executions", default=0)
    time_saved_minutes = fields.Integer(string="Temps economise (min)", default=0)
    error_count = fields.Integer(string="Erreurs", default=0)

    @api.depends("step_ids")
    def _compute_step_count(self):
        for rec in self:
            rec.step_count = len(rec.step_ids)

    @api.depends()
    def _compute_workflow_count(self):
        data = self.env["civora.workflow"].read_group(
            [("template_id", "in", self.ids), ("state", "not in", ["termine", "annule"])],
            ["template_id"], ["template_id"],
        )
        mapped = {d["template_id"][0]: d["template_id_count"] for d in data}
        for rec in self:
            rec.workflow_count = mapped.get(rec.id, 0)

    def action_toggle_active(self):
        for rec in self:
            rec.is_active = not rec.is_active

    @api.model
    def get_automations_kpis(self):
        templates = self.search([("company_id", "=", self.env.company.id)])
        active_count = len(templates.filtered(lambda t: t.is_active))
        total_executions = sum(templates.mapped("execution_count"))
        total_time = sum(templates.mapped("time_saved_minutes"))
        total_errors = sum(templates.mapped("error_count"))
        sla = round((total_executions - total_errors) / total_executions * 100, 1) if total_executions else 100
        return {
            "active_count": active_count,
            "total_count": len(templates),
            "executions_30d": total_executions,
            "time_saved_hours": round(total_time / 60),
            "sla_percent": sla,
        }

    @api.model
    def get_automations_list(self):
        return self.search_read(
            [("company_id", "=", self.env.company.id)],
            ["name", "trigger_description", "trigger_type", "step_count",
             "execution_count", "is_active", "category", "error_count"],
            order="sequence, name",
        )

    @api.model
    def get_top_automation(self):
        top = self.search(
            [("company_id", "=", self.env.company.id), ("is_active", "=", True)],
            order="execution_count desc", limit=1,
        )
        if top:
            return {
                "name": top.name,
                "execution_count": top.execution_count,
                "error_count": top.error_count,
            }
        return {}

    @api.model
    def get_ia_suggestions(self):
        return {
            "count": 3,
            "title": "3 workflows suggeres par l'IA",
            "description": "Sur la base des actions repetees par votre equipe ces 30j, CIVORA AI suggere : 'Confirmation visite J-1', 'Pre-qualification lead WhatsApp', 'Relance compteurs eau/electricite'.",
        }


class CivoraWorkflowTemplateStep(models.Model):
    _name = "civora.workflow.template.step"
    _description = "Etape de modele de workflow"
    _order = "sequence, id"

    template_id = fields.Many2one(
        "civora.workflow.template", string="Modele", required=True, ondelete="cascade",
    )
    name = fields.Char(string="Nom", required=True)
    description = fields.Text(string="Description")
    sequence = fields.Integer(default=10)
    duration_days = fields.Integer(string="Duree estimee (jours)", default=1)
    is_required = fields.Boolean(string="Obligatoire", default=True)
    responsible_role = fields.Selection([
        ("agent", "Agent"),
        ("manager", "Manager"),
        ("admin", "Administrateur"),
        ("notaire", "Notaire"),
        ("externe", "Prestataire externe"),
    ], string="Responsable type", default="agent")
