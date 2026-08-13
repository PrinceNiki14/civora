# -*- coding: utf-8 -*-
"""Workflow CIVORA = automatisation metier.

Choix d'architecture (volontairement different de la V1 du module) :
la V1 modelisait un workflow comme une liste de taches a cocher, avec un
cycle de vie brouillon/en cours/termine. Ce n'est pas ce que fait un moteur
d'automatisation : un workflow n'est jamais "termine", il est actif ou en
pause, et ce sont ses *executions* qui ont un resultat. On modelise donc :

    civora.workflow            -> l'automatisation (definition + statistiques)
    civora.workflow.step       -> un noeud du graphe (declencheur/action/...)
    civora.workflow.execution  -> une execution horodatee avec son resultat

C'est aussi ce qui permet de calculer honnetement le taux de succes et le
temps economise au lieu de les saisir a la main.
"""
import re
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

WORKFLOW_CATEGORY = [
    ("locatif", "Locatif"),
    ("ventes_crm", "Ventes & CRM"),
    ("saisonnier", "Saisonnier"),
    ("comptabilite", "Comptabilité"),
    ("maintenance", "Maintenance"),
    ("reporting", "Reporting"),
]

WORKFLOW_STATUS = [
    ("actif", "Actif"),
    ("pause", "Pause"),
    ("brouillon", "Brouillon"),
]

TRIGGER_TYPE = [
    ("event", "Événement métier"),
    ("schedule", "Planification récurrente"),
    ("condition", "Condition / score IA"),
    ("manual", "Déclenchement manuel"),
]


def slugify(value):
    value = (value or "").lower()
    replacements = {
        "à": "a", "â": "a", "ä": "a", "é": "e", "è": "e", "ê": "e", "ë": "e",
        "î": "i", "ï": "i", "ô": "o", "ö": "o", "ù": "u", "û": "u", "ü": "u",
        "ç": "c", "→": "-", "'": "-", "’": "-",
    }
    for src, dst in replacements.items():
        value = value.replace(src, dst)
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return re.sub(r"-{2,}", "-", value).strip("-")


class CivoraWorkflow(models.Model):
    _name = "civora.workflow"
    _description = "Workflow / automatisation"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id"
    _rec_name = "title"

    name = fields.Char(
        string="Référence", readonly=True, copy=False, default="/", index=True,
    )
    title = fields.Char(string="Nom", required=True, tracking=True)
    slug = fields.Char(string="Slug", compute="_compute_slug", store=True)
    description = fields.Text(string="Description")
    category = fields.Selection(
        WORKFLOW_CATEGORY, string="Catégorie", required=True,
        default="locatif", tracking=True,
    )
    trigger_description = fields.Char(string="Déclencheur", tracking=True)
    trigger_type = fields.Selection(
        TRIGGER_TYPE, string="Type de déclencheur", default="event",
    )
    status = fields.Selection(
        WORKFLOW_STATUS, string="Statut", required=True,
        default="brouillon", tracking=True,
    )
    template_id = fields.Many2one(
        "civora.workflow.template", string="Créé depuis le modèle", ondelete="set null",
    )

    step_ids = fields.One2many("civora.workflow.step", "workflow_id", string="Étapes")
    execution_ids = fields.One2many(
        "civora.workflow.execution", "workflow_id", string="Exécutions",
    )

    # Le responsable garde le nom technique historique (assigned_to) car
    # civora_equipe compte les workflows par responsable sur ce champ.
    assigned_to = fields.Many2one(
        "res.users", string="Responsable", tracking=True,
        default=lambda self: self.env.user,
    )
    time_saved_hours = fields.Integer(
        string="Temps économisé (h)", default=0,
        help="Estimation du temps humain economise depuis la mise en service.",
    )

    # Les compteurs cumules sont stockes et non recalcules a partir du journal :
    # une agence conserve rarement 100 % de l'historique d'execution en base
    # (purge, reprise de donnees). Le journal (execution_ids) sert a afficher
    # les dernieres executions ; les compteurs portent le cumul depuis la mise
    # en service. Les deux sont maintenus ensemble par _log_execution().
    run_count = fields.Integer(string="Exécutions", default=0, readonly=True, copy=False)
    success_count = fields.Integer(string="Succès", default=0, readonly=True, copy=False)
    error_count = fields.Integer(string="Échecs", default=0, readonly=True, copy=False)

    step_count = fields.Integer(string="Nb étapes", compute="_compute_step_count", store=True)
    success_rate = fields.Integer(
        string="Taux de succès (%)", compute="_compute_success_rate", store=True,
    )
    last_execution_date = fields.Datetime(
        string="Dernière exécution", compute="_compute_last_execution", store=True,
    )

    company_id = fields.Many2one(
        "res.company", string="Société", required=True,
        default=lambda self: self.env.company,
    )

    # Pas de contrainte SQL d'unicite sur le titre : lors d'une montee de
    # version, l'ancien jeu de donnees et le nouveau coexistent le temps de la
    # transaction. L'unicite est assuree au niveau applicatif (action_deploy
    # suffixe automatiquement) et par _check_title_unique ci-dessous.

    @api.constrains("title", "company_id")
    def _check_title_unique(self):
        for rec in self:
            if not rec.title:
                continue
            twin = self.search_count([
                ("id", "!=", rec.id),
                ("title", "=", rec.title),
                ("company_id", "=", rec.company_id.id),
            ])
            if twin:
                raise ValidationError(
                    "Un workflow nommé « %s » existe déjà pour cette société." % rec.title
                )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends("title")
    def _compute_slug(self):
        for rec in self:
            rec.slug = slugify(rec.title)

    @api.depends("step_ids")
    def _compute_step_count(self):
        for rec in self:
            rec.step_count = len(rec.step_ids)

    @api.depends("run_count", "success_count")
    def _compute_success_rate(self):
        for rec in self:
            rec.success_rate = (
                round(rec.success_count * 100.0 / rec.run_count) if rec.run_count else 100
            )

    @api.depends("execution_ids", "execution_ids.execution_date")
    def _compute_last_execution(self):
        for rec in self:
            execs = rec.execution_ids.sorted(lambda e: e.execution_date or fields.Datetime.now(), reverse=True)
            rec.last_execution_date = execs[0].execution_date if execs else False

    # ------------------------------------------------------------------
    def _log_execution(self, message, result="succes", is_test=False, steps_done=0):
        """Journalise une execution ET met a jour les compteurs cumules."""
        self.ensure_one()
        execution = self.env["civora.workflow.execution"].create({
            "workflow_id": self.id,
            "name": message,
            "result": result,
            "is_test": is_test,
            "steps_done": steps_done,
        })
        self.run_count += 1
        if result == "succes":
            self.success_count += 1
        elif result == "echec":
            self.error_count += 1
        return execution

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code("civora.workflow") or "/"
        return super().create(vals_list)

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        for rec, vals in zip(self, vals_list):
            vals.setdefault("title", "%s (copie)" % rec.title)
            vals["name"] = "/"
            vals["status"] = "brouillon"
        return vals_list

    # ------------------------------------------------------------------
    # Actions metier
    # ------------------------------------------------------------------
    def action_toggle_status(self):
        """Actif <-> Pause. Un brouillon passe directement en actif."""
        for rec in self:
            if rec.status == "actif":
                rec.status = "pause"
            else:
                if not rec.step_ids:
                    raise UserError(
                        "Ajoutez au moins une étape avant d'activer « %s »." % rec.title
                    )
                if not rec.step_ids.filtered(lambda s: s.kind == "declencheur"):
                    raise UserError(
                        "Le workflow « %s » n'a pas de déclencheur : il ne pourrait "
                        "jamais se lancer." % rec.title
                    )
                rec.status = "actif"
        return True

    def action_run_test(self):
        """Simulation pas a pas.

        Aucune donnee metier n'est modifiee : on execute la definition et on
        journalise l'execution comme un test. Le front rejoue le retour etape
        par etape pour l'animation.
        """
        self.ensure_one()
        if not self.step_ids:
            raise UserError("Ce workflow n'a aucune étape à simuler.")
        steps = self.step_ids.sorted(lambda s: (s.sequence, s.id))
        done = len(steps)
        self._log_execution(
            "Test manuel — %s étapes exécutées" % done,
            result="succes", is_test=True, steps_done=done,
        )
        self.message_post(body="Test manuel du workflow : %s étapes simulées." % done)
        return {
            "workflow_id": self.id,
            "title": self.title,
            "steps": [s.to_dict() for s in steps],
            "run_count": self.run_count,
            "success_rate": self.success_rate,
        }

    def action_duplicate(self):
        self.ensure_one()
        new = self.copy()
        for step in self.step_ids.sorted(lambda s: (s.sequence, s.id)):
            step.copy({"workflow_id": new.id})
        return new.id

    # ------------------------------------------------------------------
    # Helpers de presentation
    # ------------------------------------------------------------------
    @api.model
    def _humanize_delta(self, dt):
        if not dt:
            return ""
        delta = fields.Datetime.now() - dt
        minutes = int(delta.total_seconds() // 60)
        if minutes < 1:
            return "à l'instant"
        if minutes < 60:
            return "il y a %s min" % minutes
        hours = minutes // 60
        if hours < 24:
            return "il y a %s h" % hours
        days = hours // 24
        if days == 1:
            return "hier"
        if days < 30:
            return "il y a %s jours" % days
        return fields.Datetime.to_string(dt)[:10]

    def to_dict(self, with_steps=True, with_history=True):
        self.ensure_one()
        categories = dict(WORKFLOW_CATEGORY)
        statuses = dict(WORKFLOW_STATUS)
        data = {
            "id": self.id,
            "ref": self.name or "",
            "title": self.title or "",
            "slug": self.slug or "",
            "description": self.description or "",
            "category": self.category or "",
            "category_label": categories.get(self.category, ""),
            "trigger_description": self.trigger_description or "",
            "trigger_type": self.trigger_type or "event",
            "status": self.status or "brouillon",
            "status_label": statuses.get(self.status, ""),
            "step_count": self.step_count,
            "run_count": self.run_count,
            "success_rate": self.success_rate,
            "time_saved_hours": self.time_saved_hours,
            "owner": self.assigned_to.name or "",
            "owner_id": self.assigned_to.id or False,
            "last_run_label": self._humanize_delta(self.last_execution_date),
        }
        if with_steps:
            data["steps"] = [s.to_dict() for s in self.step_ids.sorted(lambda s: (s.sequence, s.id))]
        if with_history:
            data["history"] = [{
                "id": e.id,
                "message": e.name,
                "result": e.result,
                "result_label": dict(e._fields["result"].selection).get(e.result, ""),
                "is_test": e.is_test,
                "date": fields.Datetime.to_string(e.execution_date),
                "date_label": self._format_run_date(e.execution_date),
                "ago": self._humanize_delta(e.execution_date),
            } for e in self.execution_ids[:8]]
        return data

    @api.model
    def _format_run_date(self, dt):
        if not dt:
            return ""
        months = ["janv.", "févr.", "mars", "avril", "mai", "juin", "juil.",
                  "août", "sept.", "oct.", "nov.", "déc."]
        local = fields.Datetime.context_timestamp(self, dt)
        return "%s %s, %02d:%02d" % (local.day, months[local.month - 1], local.hour, local.minute)

    # ------------------------------------------------------------------
    # API ecran (un seul aller-retour RPC)
    # ------------------------------------------------------------------
    @api.model
    def get_screen_data(self):
        workflows = self.search([("company_id", "in", self.env.companies.ids)])
        records = [w.to_dict() for w in workflows]

        total = len(workflows)
        active = len(workflows.filtered(lambda w: w.status == "actif"))
        runs = sum(workflows.mapped("run_count"))
        hours = sum(workflows.mapped("time_saved_hours"))
        rates = [w.success_rate for w in workflows if w.run_count]
        avg_rate = round(sum(rates) / len(rates)) if rates else 100

        top = False
        if workflows:
            top = max(workflows, key=lambda w: w.run_count)
        last_exec = self.env["civora.workflow.execution"].search(
            [("workflow_id", "in", workflows.ids)], order="execution_date desc", limit=1,
        )

        return {
            "kpis": {
                "active_count": active,
                "total_count": total,
                "runs": runs,
                "time_saved_hours": hours,
                "success_rate": avg_rate,
            },
            "workflows": records,
            "templates": self.env["civora.workflow.template"].get_template_library(),
            "categories": [{"value": v, "label": l} for v, l in WORKFLOW_CATEGORY],
            "statuses": [{"value": v, "label": l} for v, l in WORKFLOW_STATUS],
            "step_kinds": self.env["civora.workflow.step"]._fields["kind"].selection,
            "top": {
                "id": top.id if top else False,
                "title": top.title if top else "",
                "run_count": top.run_count if top else 0,
                "success_rate": top.success_rate if top else 0,
                "last_run": (
                    "%s — %s" % (self._humanize_delta(last_exec.execution_date), last_exec.name)
                    if last_exec else "Aucune exécution enregistrée"
                ),
            } if top else {},
            "insight": self.get_ai_suggestions(),
        }

    @api.model
    def get_detail(self, workflow_id):
        wf = self.browse(int(workflow_id))
        if not wf.exists():
            return {"workflow": False, "history": []}
        data = wf.to_dict(with_steps=True, with_history=False)
        data["trigger_type_label"] = dict(TRIGGER_TYPE).get(wf.trigger_type, "")
        data["success_count"] = wf.success_count
        data["error_count"] = wf.error_count
        data["created"] = fields.Datetime.to_string(wf.create_date)[:10] if wf.create_date else ""
        data["template_name"] = wf.template_id.name or ""
        history = [{
            "id": e.id,
            "message": e.name,
            "result": e.result,
            "result_label": dict(e._fields["result"].selection).get(e.result, ""),
            "is_test": e.is_test,
            "steps_done": e.steps_done,
            "user": e.user_id.name or "",
            "date_label": self._format_run_date(e.execution_date),
            "ago": self._humanize_delta(e.execution_date),
        } for e in wf.execution_ids[:50]]
        return {"workflow": data, "history": history}

    @api.model
    def get_ai_suggestions(self):
        """Suggestions calculees a partir des modeles non encore deployes.

        La demo affiche un texte fige. Ici on le derive du catalogue : un
        modele de la bibliotheque qui n'a pas encore de workflow correspondant
        est une suggestion legitime. Si tout est deploye, on le dit.
        """
        templates = self.env["civora.workflow.template"].search([("is_active", "=", True)])
        deployed = set(self.search([]).mapped("title"))
        missing = [t for t in templates if t.name not in deployed]
        names = ", ".join("« %s »" % t.name for t in missing[:3])
        if not missing:
            return {
                "count": 0,
                "title": "Tous les modèles sont déployés",
                "description": (
                    "Les %s modèles de la bibliothèque CIVORA sont déjà en service "
                    "dans votre agence. CIVORA AI n'a pas de nouvelle automatisation "
                    "à proposer sur les 30 derniers jours." % len(templates)
                ),
                "template_ids": [],
            }
        return {
            "count": len(missing),
            "title": "%s workflow%s suggéré%s par l'IA" % (
                len(missing), "s" if len(missing) > 1 else "", "s" if len(missing) > 1 else "",
            ),
            "description": (
                "Sur la base des actions répétées par votre équipe ces 30j, "
                "CIVORA AI suggère : %s." % names
            ),
            "template_ids": [t.id for t in missing[:3]],
        }

    # ------------------------------------------------------------------
    # Ecriture depuis le builder
    # ------------------------------------------------------------------
    @api.model
    def save_workflow(self, workflow_id, vals, steps):
        """Cree ou met a jour un workflow et remplace ses etapes.

        `steps` est la liste ordonnee produite par le builder :
        [{kind, name, detail}, ...]
        """
        clean = {k: v for k, v in (vals or {}).items() if k in (
            "title", "description", "category", "trigger_description",
            "trigger_type", "status", "time_saved_hours", "assigned_to",
        )}
        if not clean.get("title"):
            raise UserError("Le nom du workflow est obligatoire.")
        if workflow_id:
            wf = self.browse(int(workflow_id))
            wf.write(clean)
        else:
            wf = self.create(clean)
        wf.step_ids.unlink()
        Step = self.env["civora.workflow.step"]
        for idx, step in enumerate(steps or []):
            if not (step.get("name") or "").strip():
                continue
            Step.create({
                "workflow_id": wf.id,
                "kind": step.get("kind") or "action",
                "name": step["name"].strip(),
                "detail": (step.get("detail") or "").strip(),
                "sequence": (idx + 1) * 10,
            })
        if wf.status == "actif" and not wf.step_ids.filtered(lambda s: s.kind == "declencheur"):
            raise UserError(
                "Un workflow actif doit comporter au moins une étape « Déclencheur »."
            )
        return wf.id

    @api.model
    def create_from_template(self, template_id, activate=True):
        template = self.env["civora.workflow.template"].browse(int(template_id))
        if not template.exists():
            raise UserError("Modèle introuvable.")
        return template.action_deploy(activate=activate)
