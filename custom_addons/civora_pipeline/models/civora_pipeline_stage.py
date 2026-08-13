# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


DEFAULT_STAGES = [
    # (code, name, sequence, is_won, is_lost, fold)
    ('nouveau', "Nouveau", 10, False, False, False),
    ('qualifie', "Qualifié", 20, False, False, False),
    ('visite', "Visite", 30, False, False, False),
    ('offre', "Offre", 40, False, False, False),
    ('gagne', "Gagné", 50, True, False, False),
    ('perdu', "Perdu", 60, False, True, True),
]


class CivoraPipelineStage(models.Model):
    """Etape du pipeline commercial (colonnes du kanban). Parametrable par societe.

    Chaque societe possede son propre jeu d'etapes. Les 6 etapes par defaut sont
    creees automatiquement a l'installation du module et a la creation de toute
    nouvelle societe (cf. res.company._create_civora_pipeline_default_stages).
    """
    _name = 'civora.pipeline.stage'
    _description = "Etape de pipeline CIVORA"
    _order = 'sequence, id'

    name = fields.Char(string="Nom", required=True, translate=True)
    code = fields.Char(
        string="Code", required=True,
        help="Identifiant technique de l'etape (auto-genere depuis le nom).",
    )
    sequence = fields.Integer(string="Sequence", default=10, index=True)
    is_won = fields.Boolean(string="Gagnée", help="Etape finale marquant une affaire gagnée.")
    is_lost = fields.Boolean(string="Perdue", help="Etape finale marquant une affaire perdue.")
    fold = fields.Boolean(string="Repliée", help="Colonne repliée par defaut dans le kanban.")
    active = fields.Boolean(string="Actif", default=True)
    company_id = fields.Many2one(
        'res.company',
        string="Societe",
        required=True,
        index=True,
        default=lambda self: self.env.company,
        help="Societe proprietaire de l'etape (cloisonnement strict).",
    )
    opportunity_count = fields.Integer(
        string="Nombre d'opportunites",
        compute='_compute_opportunity_count',
    )

    _code_uniq = models.Constraint(
        'unique (code, company_id)',
        "Le code de l'etape doit etre unique par societe.",
    )

    _check_company_auto = True

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    def _compute_opportunity_count(self):
        if not self.ids:
            for s in self:
                s.opportunity_count = 0
            return
        Opp = self.env['civora.opportunity']
        for stage in self:
            stage.opportunity_count = Opp.search_count([('stage_id', '=', stage.id)])

    # ------------------------------------------------------------------
    # Contraintes metier
    # ------------------------------------------------------------------
    @api.constrains('is_won', 'is_lost')
    def _check_won_lost_exclusive(self):
        for stage in self:
            if stage.is_won and stage.is_lost:
                raise ValidationError(_(
                    "Une etape ne peut pas etre a la fois « Gagnée » et « Perdue » (« %s »).",
                ) % (stage.name or '',))

    @api.constrains('is_won', 'is_lost', 'active', 'company_id')
    def _check_at_least_one_won_and_lost(self):
        """Chaque societe doit conserver au moins une etape gagnée et une perdue."""
        for stage in self:
            if not stage.company_id:
                continue
            self._ensure_company_has_won_lost(stage.company_id)

    @api.model
    def _ensure_company_has_won_lost(self, company):
        Stage = self.sudo()
        won = Stage.search_count([
            ('company_id', '=', company.id), ('active', '=', True), ('is_won', '=', True),
        ])
        lost = Stage.search_count([
            ('company_id', '=', company.id), ('active', '=', True), ('is_lost', '=', True),
        ])
        if won < 1:
            raise ValidationError(_(
                "La societe « %s » doit conserver au moins une etape « Gagnée » active.",
            ) % (company.name,))
        if lost < 1:
            raise ValidationError(_(
                "La societe « %s » doit conserver au moins une etape « Perdue » active.",
            ) % (company.name,))

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code') and vals.get('name'):
                vals['code'] = self._slugify_code(vals['name'])
            if not vals.get('company_id'):
                vals['company_id'] = self.env.company.id
        return super().create(vals_list)

    def unlink(self):
        """Refuse la suppression tant qu'il reste des opportunites dans l'etape."""
        Opp = self.env['civora.opportunity']
        for stage in self:
            count = Opp.search_count([('stage_id', '=', stage.id)])
            if count:
                raise UserError(_(
                    "Impossible de supprimer l'etape « %(name)s » : "
                    "elle contient %(count)s opportunite(s). "
                    "Deplacez-les d'abord vers une autre etape.",
                    name=stage.name, count=count,
                ))
        companies = self.mapped('company_id')
        res = super().unlink()
        # Verifier apres suppression que chaque societe conserve won + lost.
        for company in companies:
            self._ensure_company_has_won_lost(company)
        return res

    # ------------------------------------------------------------------
    # Actions publiques (appelees depuis l'ecran OWL)
    # ------------------------------------------------------------------
    def action_move_up(self):
        """Echange la sequence avec l'etape precedente (meme societe)."""
        self.ensure_one()
        prev = self.search([
            ('company_id', '=', self.company_id.id),
            ('sequence', '<', self.sequence),
        ], order='sequence desc, id desc', limit=1)
        if not prev:
            # Deja en tete : rien a faire.
            return False
        return self._swap_sequence_with(prev)

    def action_move_down(self):
        """Echange la sequence avec l'etape suivante (meme societe)."""
        self.ensure_one()
        nxt = self.search([
            ('company_id', '=', self.company_id.id),
            ('sequence', '>', self.sequence),
        ], order='sequence asc, id asc', limit=1)
        if not nxt:
            return False
        return self._swap_sequence_with(nxt)

    def _swap_sequence_with(self, other):
        """Echange les sequences en garantissant des valeurs distinctes."""
        if self.sequence == other.sequence:
            # Cas rare : on decale d'abord pour eviter la collision sur l'index unique implicite.
            other.sequence = self.sequence + 1
        my_seq = self.sequence
        self.sequence = other.sequence
        other.sequence = my_seq
        return True

    def action_delete_with_reassign(self, target_stage_id=False):
        """Deplace toutes les opportunites vers target_stage_id puis supprime l'etape.

        Si target_stage_id est faux et que l'etape contient des opportunites,
        leve une erreur (le front doit imposer un choix).
        """
        self.ensure_one()
        Opp = self.env['civora.opportunity']
        opps = Opp.search([('stage_id', '=', self.id)])
        if opps:
            if not target_stage_id:
                raise UserError(_(
                    "Choisissez une etape cible pour deplacer les %s opportunite(s) "
                    "avant de supprimer « %s ».",
                ) % (len(opps), self.name))
            target = self.browse(int(target_stage_id))
            if not target.exists() or target.id == self.id:
                raise UserError(_("Etape cible invalide."))
            if target.company_id != self.company_id:
                raise UserError(_(
                    "L'etape cible doit appartenir a la meme societe.",
                ))
            opps.write({'stage_id': target.id})
        self.unlink()
        return True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @api.model
    def _slugify_code(self, name):
        """Genere un code technique unique par societe a partir d'un nom."""
        import re
        import unicodedata
        base = unicodedata.normalize('NFKD', name or '').encode('ascii', 'ignore').decode()
        base = re.sub(r'[^a-zA-Z0-9]+', '_', base).strip('_').lower() or 'etape'
        company_id = self.env.context.get('default_company_id') or self.env.company.id
        code = base
        i = 2
        while self.sudo().search_count([('code', '=', code), ('company_id', '=', company_id)]):
            code = "%s_%s" % (base, i)
            i += 1
        return code

    @api.model
    def civora_can_manage_stages(self):
        """L'utilisateur courant peut-il creer / renommer / supprimer une etape ?

        Les etapes structurent le pipeline de toute l'agence : un agent ne
        doit pas pouvoir en supprimer une. On expose le droit a l'ecran
        plutot que de laisser l'ORM lever une AccessError, qui produirait
        une fenetre d'erreur technique incomprehensible.
        """
        Stage = self.env['civora.pipeline.stage']
        # has_access() remplace check_access_rights() depuis Odoo 18. On
        # sonde defensivement : une methode inexistante ferait planter tout
        # le chargement de l'ecran Pipeline.
        try:
            return bool(Stage.has_access('write'))
        except AttributeError:
            try:
                return bool(Stage.check_access_rights('write', raise_exception=False))
            except Exception:  # noqa: BLE001
                return self.env.user.has_group('base.group_system')

    @api.model
    def _create_default_stages_for_company(self, company):
        """Cree les 6 etapes par defaut pour une societe (idempotent)."""
        company = company or self.env.company
        if not company:
            return self.browse()
        existing = self.sudo().with_context(active_test=False).search([
            ('company_id', '=', company.id),
        ])
        existing_codes = set(existing.mapped('code'))
        vals_list = []
        for code, name, sequence, is_won, is_lost, fold in DEFAULT_STAGES:
            if code in existing_codes:
                continue
            vals_list.append({
                'code': code, 'name': name, 'sequence': sequence,
                'is_won': is_won, 'is_lost': is_lost, 'fold': fold,
                'company_id': company.id,
            })
        if not vals_list:
            return self.browse()
        return self.sudo().create(vals_list)
