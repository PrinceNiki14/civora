from odoo import models, fields, api
from odoo.exceptions import UserError


class CivoraWorkflow(models.Model):
    _name = "civora.workflow"
    _description = "Workflow"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(string="Reference", readonly=True, copy=False, default="/")
    title = fields.Char(string="Titre", required=True, tracking=True)
    template_id = fields.Many2one(
        "civora.workflow.template", string="Modele", tracking=True,
    )
    state = fields.Selection([
        ("brouillon", "Brouillon"),
        ("en_cours", "En cours"),
        ("en_pause", "En pause"),
        ("termine", "Termine"),
        ("annule", "Annule"),
    ], string="Statut", default="brouillon", required=True, tracking=True)
    category = fields.Selection([
        ("vente", "Vente"),
        ("location", "Location"),
        ("gestion", "Gestion"),
        ("administratif", "Administratif"),
    ], string="Categorie", required=True, default="gestion", tracking=True)
    priority = fields.Selection([
        ("normal", "Normal"),
        ("urgent", "Urgent"),
        ("critique", "Critique"),
    ], string="Priorite", default="normal", tracking=True)

    assigned_to = fields.Many2one("res.users", string="Responsable", tracking=True)
    start_date = fields.Date(string="Date de debut")
    deadline = fields.Date(string="Echeance", tracking=True)
    completed_date = fields.Date(string="Date de fin")

    step_ids = fields.One2many(
        "civora.workflow.step", "workflow_id", string="Etapes",
    )
    step_count = fields.Integer(compute="_compute_progress", string="Nb etapes")
    completed_steps = fields.Integer(compute="_compute_progress", string="Etapes terminees")
    progress = fields.Float(compute="_compute_progress", string="Progression (%)")

    reference = fields.Char(string="Reference externe")
    notes = fields.Text(string="Notes")
    company_id = fields.Many2one(
        "res.company", string="Societe",
        default=lambda self: self.env.company,
    )

    @api.depends("step_ids.state")
    def _compute_progress(self):
        for rec in self:
            steps = rec.step_ids
            total = len(steps)
            done = len(steps.filtered(lambda s: s.state == "termine"))
            rec.step_count = total
            rec.completed_steps = done
            rec.progress = (done / total * 100) if total else 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code("civora.workflow") or "/"
        return super().create(vals_list)

    def action_start(self):
        for rec in self:
            if not rec.step_ids:
                raise UserError("Ajoutez au moins une etape avant de demarrer le workflow.")
            rec.state = "en_cours"
            if not rec.start_date:
                rec.start_date = fields.Date.today()

    def action_pause(self):
        for rec in self:
            rec.state = "en_pause"

    def action_resume(self):
        for rec in self:
            rec.state = "en_cours"

    def action_complete(self):
        for rec in self:
            pending = rec.step_ids.filtered(
                lambda s: s.is_required and s.state != "termine"
            )
            if pending:
                raise UserError(
                    "Les etapes obligatoires suivantes ne sont pas terminees : "
                    + ", ".join(pending.mapped("name"))
                )
            rec.state = "termine"
            rec.completed_date = fields.Date.today()

    def action_cancel(self):
        for rec in self:
            rec.state = "annule"

    def action_reset(self):
        for rec in self:
            rec.state = "brouillon"
            rec.completed_date = False

    def apply_template(self):
        for rec in self:
            if not rec.template_id:
                continue
            rec.step_ids.unlink()
            rec.category = rec.template_id.category
            base_date = rec.start_date or fields.Date.today()
            cumulative = 0
            for ts in rec.template_id.step_ids.sorted("sequence"):
                cumulative += ts.duration_days
                self.env["civora.workflow.step"].create({
                    "workflow_id": rec.id,
                    "name": ts.name,
                    "description": ts.description,
                    "sequence": ts.sequence,
                    "is_required": ts.is_required,
                    "responsible_role": ts.responsible_role,
                    "deadline": fields.Date.add(base_date, days=cumulative),
                })

    @api.model
    def get_workflows_kpis(self):
        today = fields.Date.today()
        all_wf = self.search([])
        active = all_wf.filtered(lambda w: w.state == "en_cours")
        overdue = active.filtered(lambda w: w.deadline and w.deadline < today)
        month_start = today.replace(day=1)
        completed_month = all_wf.filtered(
            lambda w: w.state == "termine" and w.completed_date and w.completed_date >= month_start
        )
        avg_progress = 0
        if active:
            avg_progress = round(sum(active.mapped("progress")) / len(active), 1)
        return {
            "active": len(active),
            "overdue": len(overdue),
            "completed_month": len(completed_month),
            "avg_progress": avg_progress,
            "total": len(all_wf.filtered(lambda w: w.state not in ["annule"])),
        }
