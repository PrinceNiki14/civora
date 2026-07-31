from odoo import models, fields, api


class CivoraTeamMember(models.Model):
    _name = "civora.team.member"
    _description = "Membre de l'equipe"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence, name"
    _rec_name = "name"

    user_id = fields.Many2one(
        "res.users", string="Utilisateur", required=True, tracking=True,
    )
    name = fields.Char(
        string="Nom complet", compute="_compute_name", store=True,
    )
    role_id = fields.Many2one(
        "civora.agent.role", string="Fonction",
    )
    department = fields.Selection([
        ("direction", "Direction"),
        ("commercial", "Commercial"),
        ("gestion", "Gestion locative"),
        ("support", "Support"),
    ], string="Departement", default="commercial", tracking=True)
    status = fields.Selection([
        ("actif", "Actif"),
        ("conge", "En conge"),
        ("inactif", "Inactif"),
    ], string="Statut", default="actif", tracking=True)
    presence = fields.Selection([
        ("present", "Present"),
        ("en_visite", "En visite"),
        ("conge", "Conge"),
        ("absent", "Absent"),
    ], string="Presence", default="present")
    hire_date = fields.Date(string="Date d'embauche")
    phone = fields.Char(string="Telephone")
    email = fields.Char(
        string="Email", compute="_compute_email", store=True,
    )
    location = fields.Char(string="Localisation", default="Plateau HQ")
    bio = fields.Text(string="Bio")
    avatar = fields.Binary(
        string="Photo", related="user_id.image_128", readonly=True,
    )
    sequence = fields.Integer(string="Sequence", default=10)
    company_id = fields.Many2one(
        "res.company", string="Societe", required=True,
        default=lambda self: self.env.company,
    )
    deal_count = fields.Integer(string="Deals")
    commission_amount = fields.Float(string="Commissions")
    performance = fields.Integer(string="Performance %", default=0)
    rating = fields.Float(string="Note /5", default=0.0)

    property_count = fields.Integer(
        string="Biens", compute="_compute_stats",
    )
    lead_count = fields.Integer(
        string="Pistes", compute="_compute_stats",
    )
    sale_count = fields.Integer(
        string="Ventes", compute="_compute_stats",
    )
    location_count = fields.Integer(
        string="Locations", compute="_compute_stats",
    )
    workflow_count = fields.Integer(
        string="Workflows", compute="_compute_stats",
    )
    event_count = fields.Integer(
        string="Evenements", compute="_compute_stats",
    )

    _user_company_uniq = models.Constraint(
        "UNIQUE(user_id, company_id)",
        "Ce membre est deja dans l'equipe pour cette societe.",
    )

    @api.depends("user_id", "user_id.name")
    def _compute_name(self):
        for rec in self:
            rec.name = rec.user_id.name or ""

    @api.depends("user_id", "user_id.email")
    def _compute_email(self):
        for rec in self:
            rec.email = rec.user_id.email or ""

    def _safe_count(self, model_name, domain):
        if model_name in self.env:
            return self.env[model_name].search_count(domain)
        return 0

    @api.depends("user_id")
    def _compute_stats(self):
        for rec in self:
            uid = rec.user_id.id
            rec.property_count = rec._safe_count(
                "civora.property", [("agent_id", "=", uid)])
            rec.lead_count = rec._safe_count(
                "civora.lead", [("agent_id", "=", uid)])
            rec.sale_count = rec._safe_count(
                "civora.sale", [("agent_id", "=", uid)])
            rec.location_count = rec._safe_count(
                "civora.location", [("agent_id", "=", uid)])
            rec.workflow_count = rec._safe_count(
                "civora.workflow", [("assigned_to", "=", uid)])
            rec.event_count = rec._safe_count(
                "civora.event", [("agent_id", "=", uid)])

    @api.model
    def get_team_kpis(self):
        company_id = self.env.company.id
        domain = [("company_id", "=", company_id)]
        members = self.search(domain)
        total = len(members)
        actifs = len(members.filtered(lambda m: m.status == "actif"))
        commerciaux = len(members.filtered(lambda m: m.department == "commercial"))
        total_deals = sum(members.mapped("deal_count"))
        total_commission = sum(members.mapped("commission_amount"))
        perfs = [m.performance for m in members if m.performance > 0]
        avg_perf = round(sum(perfs) / len(perfs)) if perfs else 0
        en_conge = len(members.filtered(lambda m: m.status == "conge"))
        return {
            "total": total,
            "actifs": actifs,
            "en_conge": en_conge,
            "inactifs": total - actifs - en_conge,
            "commerciaux": commerciaux,
            "total_deals": total_deals,
            "total_commission": total_commission,
            "avg_performance": avg_perf,
        }

    @api.model
    def get_members_list(self):
        domain = [("company_id", "=", self.env.company.id)]
        members = self.search(domain, order="sequence, name")
        result = []
        for m in members:
            hire_year = m.hire_date.year if m.hire_date else ""
            initials = ""
            if m.name:
                parts = m.name.strip().split()
                initials = "".join(p[0].upper() for p in parts[:2])
            result.append({
                "id": m.id,
                "name": m.name or "",
                "initials": initials,
                "role": m.role_id.name if m.role_id else "",
                "department": m.department or "",
                "status": m.status or "actif",
                "presence": m.presence or "present",
                "location": m.location or "",
                "phone": m.phone or "",
                "email": m.email or "",
                "hire_year": hire_year,
                "deal_count": m.deal_count or 0,
                "commission_amount": m.commission_amount or 0,
                "performance": m.performance or 0,
                "rating": m.rating or 0,
            })
        return result

    @api.model
    def get_member_stats(self, member_id):
        member = self.browse(member_id)
        if not member.exists():
            return {}
        uid = member.user_id.id
        stats = {
            "properties": [],
            "sales": [],
            "leads": [],
            "workflows": [],
            "events": [],
        }
        if "civora.property" in self.env:
            stats["properties"] = self.env["civora.property"].search_read(
                [("agent_id", "=", uid)],
                ["name", "city", "property_type_id", "status", "price"],
                limit=10, order="create_date desc",
            )
        if "civora.sale" in self.env:
            stats["sales"] = self.env["civora.sale"].search_read(
                [("agent_id", "=", uid)],
                ["name", "property_id", "state", "asking_price", "sale_amount"],
                limit=10, order="create_date desc",
            )
        if "civora.lead" in self.env:
            stats["leads"] = self.env["civora.lead"].search_read(
                [("agent_id", "=", uid)],
                ["name", "partner_id", "status", "score"],
                limit=10, order="create_date desc",
            )
        if "civora.workflow" in self.env:
            stats["workflows"] = self.env["civora.workflow"].search_read(
                [("assigned_to", "=", uid)],
                ["name", "title", "state", "progress"],
                limit=10, order="create_date desc",
            )
        if "civora.event" in self.env:
            stats["events"] = self.env["civora.event"].search_read(
                [("agent_id", "=", uid)],
                ["name", "event_type", "start", "status"],
                limit=10, order="start desc",
            )
        return stats
