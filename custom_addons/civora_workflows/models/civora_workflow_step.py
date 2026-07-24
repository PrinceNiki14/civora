from odoo import models, fields


class CivoraWorkflowStep(models.Model):
    _name = "civora.workflow.step"
    _description = "Etape de workflow"
    _order = "sequence, id"

    workflow_id = fields.Many2one(
        "civora.workflow", string="Workflow", required=True, ondelete="cascade",
    )
    name = fields.Char(string="Nom", required=True)
    description = fields.Text(string="Description")
    sequence = fields.Integer(default=10)
    state = fields.Selection([
        ("a_faire", "A faire"),
        ("en_cours", "En cours"),
        ("termine", "Termine"),
        ("bloque", "Bloque"),
        ("annule", "Annule"),
    ], string="Statut", default="a_faire", required=True)
    assigned_to = fields.Many2one("res.users", string="Responsable")
    responsible_role = fields.Selection([
        ("agent", "Agent"),
        ("manager", "Manager"),
        ("admin", "Administrateur"),
        ("notaire", "Notaire"),
        ("externe", "Prestataire externe"),
    ], string="Role")
    deadline = fields.Date(string="Echeance")
    completed_date = fields.Date(string="Date de fin")
    is_required = fields.Boolean(string="Obligatoire", default=True)
    notes = fields.Text(string="Notes")
    company_id = fields.Many2one(
        "res.company", string="Societe",
        related="workflow_id.company_id", store=True,
    )

    def action_start(self):
        for rec in self:
            rec.state = "en_cours"

    def action_complete(self):
        for rec in self:
            rec.state = "termine"
            rec.completed_date = fields.Date.today()

    def action_block(self):
        for rec in self:
            rec.state = "bloque"

    def action_reset(self):
        for rec in self:
            rec.state = "a_faire"
            rec.completed_date = False
