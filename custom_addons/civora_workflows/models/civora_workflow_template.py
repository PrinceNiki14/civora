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
