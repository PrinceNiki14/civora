# -*- encoding: utf-8 -*-

##############################################################################
#
# Copyright (c) 2012 Veone - support.veone.net
# Author: Veone
#
# Fichier du module hr_emprunt
# ##############################################################################  -->
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from datetime import date
from odoo import fields, models, api, _


#Type_employee = [('h', 'Horaire'), ('j', 'Journalier'), ('m', 'Mensuel')]

class HrrEmployee(models.Model):
    _inherit = "hr.employee"

    first_name = fields.Char("Nom")
    last_name = fields.Char("Prénoms")
    #name = fields.Char("Name", compute="_get_name")

    """@api.onchange('first_name', 'last_name')
    def get_name(self):
        #Onchange function to combine name and last_name
        if self.first_name:
            if self.last_name:
                self.name = f"{self.first_name} {self.last_name}

    @api.onchange('first_name', 'last_name')
    @api.depends('first_name', 'last_name')
    def _get_name(self):
        #Onchange function to combine name and last_name
        if self.first_name and self.last_name:
            self.name = self.first_name + '' + self.last_name"""

    @api.depends('display_name')
    def name_get(self):
        return [(r.id, (r.display_name)) for r in self]

    @api.depends('name', 'identification_id')
    def _compute_name(self):
        for employee in self:
            names = [employee.identification_id, employee.name]
            employee.display_name = ' '.join(filter(None, names))

    def action_open_contract(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id('hr_contract.action_hr_contract')
        action['views'] = [(False, 'form')]
        if not self.contract_ids:
            action['context'] = {
                'default_employee_id': self.id,
                'default_date_start': self.start_date,
                'default_expatried': True if self.nature_employe == 'expat' else False
            }
            print(action)
            action['target'] = 'new'
            return action

        target_contract = self.contract_id
        if target_contract:
            action['res_id'] = target_contract.id
            return action

        target_contract = self.contract_ids.filtered(lambda c: c.state == 'draft')
        if target_contract:
            action['res_id'] = target_contract[0].id
            return action

        action['res_id'] = self.contract_ids[0].id
        return action


class hr_employee_degree(models.Model):
    _name = "hr.employee.degree"
    _description = "Degree of employee"

    name = fields.Char('Name', required=True, translate=True)
    sequence = fields.Integer('Sequence', help="Gives the sequence order when displaying a list of degrees.", default=1)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The name of the Degree of employee must be unique!')
    ]


class licence(models.Model):
    _name = "hr.licence"
    _description = "Licence employé"

    name = fields.Char('Libellé Licence', required=True, readonly=False)
    reference = fields.Char('Reférence', required=False, readonly=False)
    date_debut = fields.Date('Début validité')
    date_fin = fields.Date('Fin validité')
    employee_id = fields.Many2one('hr.employee', 'Employé', required=False)
    #branch_id = fields.Many2one("res.branch", string='Branch', default=lambda self: self.env.user.default_branch_id.id)


class domaine(models.Model):
    _name = "hr.diplomes.domaine"
    _description = "Domaine de diplome employe"
    _rec_name = 'libelle'

    libelle = fields.Char('Libellé Domaine', required=True, readonly=False)


class DiplomeEmploye(models.Model):
    _name = "hr.diplomes.employee"
    _description = "Diplome employe"

    name = fields.Char('Nom')
    diplome_id = fields.Many2one('hr.employee.degree', 'Niveau', required=True)
    domaine_id = fields.Many2one('hr.diplomes.domaine', 'Domaines', required=False, readonly=False)
    reference = fields.Char('Reférence', required=False, readonly=False)
    date_obtention = fields.Date("Date d'obtention")
    date_start = fields.Date("Date début")
    date_end = fields.Date("Date fin")
    type = fields.Selection([
        ('diplome', 'Diplôme'),
        ('certif', 'Certification')], string="Type")
    image = fields.Binary('Image')
    employee_id = fields.Many2one('hr.employee', 'Employé', required=False)
    #branch_id = fields.Many2one("res.branch", string='Branch', default=lambda self: self.env.user.default_branch_id.id)


class visa(models.Model):
    _name = "hr.visa"
    _description = "visa employé"

    name = fields.Char('Libellé visa', required=True, readonly=False)
    reference = fields.Char('N° Visa', required=True, readonly=False)
    pays_id = fields.Many2one('res.country', 'Pays', required=True)
    date_debut = fields.Datetime('Début validité')
    date_fin = fields.Datetime('Fin validité')
    employee_id = fields.Many2one('hr.employee', 'Employé', required=False)
    #branch_id = fields.Many2one("res.branch", string='Branch', default=lambda self: self.env.user.default_branch_id.id)


class carte_sejour(models.Model):
    _name = "hr.carte.sejour"
    _description = "Carte de séjour employé"

    # def _get_default_branch_id(self):
    #     if len(self.env.user.branch_ids) == 1:
    #         sp_company = self.company_id if self.company_id else self.env.company
    #         branch_ids = self.env.user.branch_ids
    #         branch = branch_ids.filtered(
    #             lambda branch: branch.company_id == sp_company)
    #         if branch:
    #             return branch
    #         else:
    #             return False
    #     return False

    name = fields.Char('Libellé visa', required=False, readonly=False)
    reference = fields.Char('N° Visa', required=False, readonly=False)
    pays_id = fields.Many2one('res.country', 'Pays', required=False)
    date_debut = fields.Datetime('Début validité')
    date_fin = fields.Datetime('Fin validité')
    employee_id = fields.Many2one('hr.employee', 'Employé', required=False)
    #branch_id = fields.Many2one("res.branch", string='Branch', default=lambda self: self.env.user.default_branch_id.id)


class enfants_employe(models.Model):
    _name = "hr.employee.enfant"
    _description = "Enfants de l'employé"

    @api.depends('date_naissance')
    def _get_age_child(self):
        this_date = fields.Datetime.now()
        for child in self:
            date_naissance = fields.Datetime.from_string(child.date_naissance)
            tmp = relativedelta(this_date, date_naissance)
            child.age = tmp.years

    # def _get_default_branch_id(self):
    #     if len(self.env.user.branch_ids) == 1:
    #         sp_company = self.company_id if self.company_id else self.env.company
    #         branch_ids = self.env.user.branch_ids
    #         branch = branch_ids.filtered(
    #             lambda branch: branch.company_id == sp_company)
    #         if branch:
    #             return branch
    #         else:
    #             return False
    #     return False

    name = fields.Char('Nom', required=True, readonly=False)
    date_naissance = fields.Date("Date de naissance", required=True)
    mobile = fields.Char('Portable', required=False, readonly=False)
    email = fields.Char('email', required=False, readonly=False)
    employee_id = fields.Many2one('hr.employee', 'Employé', required=False)
    age = fields.Integer('Âge', compute="_get_age_child")
    link = fields.Selection([
        ('enfant', 'Enfant'),
        ('frere', "Frère"),
        ('soeur', 'Soeur'),
        ('cousin', 'Cousin'),
        ('cousine', 'Cousine'),
        ('other', 'Autres')], 'Lien de parenté', readonly=False)


class HrParentEmployee(models.Model):
    _name = "hr.parent.employe"
    _description = "les parents de l'employee"

    name = fields.Char('Nom', required=True, readonly=False)
    date_naissance = fields.Date("Date de naissance")
    mobile = fields.Char('Portable', required=False, readonly=False)
    email = fields.Char('email', required=False, readonly=False)
    employee_id = fields.Many2one('hr.employee', 'Employé', required=False)
    link = fields.Selection([
        ('pere', "Père"),
        ('mere', "Mère"),
    ], 'Lien de parenté', readonly=False)
    state = fields.Selection([('grand_parent', 'Grand père/Grande mère'), ('parent', 'Père / Mère'),
                              ('conjoint', 'Conjoint(e)'), ('enfant', 'Enfant'), ('frere', 'Frère / Soeur'),
                              ('voisin', 'Voisin'),
                              ('oncle', 'Oncle/Tante'), ('cousin', 'Cousin / Cousine'), ('other', 'Autres')],
                             'Type de lien', readonly=False)


class HrPersonneContact(models.Model):
    _name = 'hr.personne.contacted'
    _description = 'Personnes a contacter'

    name = fields.Char("Name", required=True)
    email = fields.Char("Email")
    portable = fields.Char('Portable', required=True)
    state = fields.Selection([('grand_parent', 'Grand père/Grande mère'),('parent', 'Père / Mère'),
              ('conjoint', 'Conjoint(e)'), ('enfant', 'Enfant'), ('frere', 'Frère / Soeur'), ('voisin', 'Voisin'),
              ('oncle', 'Oncle/Tante'), ('cousin', 'Cousin / Cousine'), ('other', 'Autres')], 'Type de lien', readonly=False)
    Lien = fields.Char("Le lien")
    employee_id = fields.Many2one("hr.employee", 'Employé')
    #branch_id = fields.Many2one("res.branch", string='Branch', default=lambda self: self.env.user.default_branch_id.id)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.depends("children", "enfants_a_charge", "marital")
    @api.onchange("children", "enfants_a_charge", "marital")
    def _get_part_igr(self):
        for emp in self:
            result = 0
            if emp.marital:
                t1 = emp.marital
                B38 = t1[0]
                B39 = emp.children
                B40 = emp.enfants_a_charge

                if ((B38 == "s") or (B38 == "d")):
                    if (B39 == 0):
                        if (B40 != 0):
                            result = 1.5
                        else:
                            result = 1
                    else:
                        if ((1.5 + B39 * 0.5) > 5):
                            result = 5
                        else:
                            result = 1.5 + B39 * 0.5
                else:
                    if (B38 == "m"):
                        if (B39 == 0):
                            result = 2
                        else:
                            if ((2 + 0.5 * B39) > 5):
                                result = 5
                            else:
                                result = 2 + 0.5 * B39
                    else:
                        if (B38 == "w"):
                            if (B39 == 0):
                                if (B40 != 0):
                                    result = 1.5
                                else:
                                    result = 1
                            else:
                                if ((2 + B39 * 0.5) > 5):
                                    result = 5
                                else:
                                    result = 2 + 0.5 * B39
                        else:
                            result += 2 + 0.5 * B39
            emp.part_igr = result

    @api.depends("enfants_ids.age")
    @api.onchange("enfants_ids.age")
    def _compute_children(self):
        for emp in self:
            total_children = 0
            if emp.enfants_ids:
                total_children = len(emp.enfants_ids)
            children_in_charge = 0
            for child in emp.enfants_ids:
                if child.age <= emp.company_id.max_age_child:
                    children_in_charge += 1
            emp.children = children_in_charge
            emp.enfants_a_charge = children_in_charge
            emp.total_children = total_children

    @api.depends("children")
    @api.onchange("children")
    def _compute_children(self):
        for emp in self:
            emp.enfants_a_charge = emp.children
            emp.total_children = emp.children

    @api.depends('birthday')
    def _get_age_employee(self):
        this_date = fields.Datetime.now()
        for emp in self:
            date_naissance = fields.Datetime.from_string(emp.birthday)
            tmp = relativedelta(this_date, date_naissance)
            emp.age = tmp.years

    @api.depends('start_date', 'end_date')
    def _get_seniority(self):
        today = fields.Datetime.now()
        for emp in self:
            start_date = fields.Datetime.from_string(emp.start_date)
            print("La date de fin est %s" % emp.end_date)
            if emp.end_date:
                end_date = fields.Datetime.from_string(emp.end_date)
                this_date = min(today, end_date)
            else:
                this_date = today
            tmp = relativedelta(this_date, start_date)
            emp.seniority_employee = tmp.years

    # def name_get(self):
    #     result = []
    #     for emp in self:
    #         if emp.first_name:
    #             name = emp.name + ' ' + emp.first_name
    #         else:
    #             name = emp.name
    #         result.append((emp.id, name))
    #     return result

    first_name = fields.Char("Prénoms", required=False)
    category_id = fields.Many2one('hr.contract.category', 'Classement', required=False)
    type = fields.Selection([('m', 'Mensuel'), ('j', 'Journalier'), ('h', 'Horaire')], 'Type', required=False, default=False)
    type_employee = fields.Selection([('F', 'Fonctionnaire'), ('NF', 'Non Fonctionnaire')], "Type d'agent")
    matricule_cnps = fields.Char('Numéro CNPS', size=64)
    enfants_a_charge = fields.Integer("Nombre d'enfants à charge", required=False)
    part_igr = fields.Float(compute=_get_part_igr, string='Part IGR')
    start_date = fields.Date("Date d'embauche", required=True)
    seniority_employee = fields.Integer("Anciennété", compute="_get_seniority")
    end_date = fields.Date("Date de depart", required=False)
    age = fields.Integer('Âge employé', compute='_get_age_employee')
    total_children = fields.Integer('Nombre enfant total', compute='_compute_children')
    #total_children = fields.Integer('Nombre enfant total')
    #cmu_employe = fields.Integer(string='CMU employé', store=True, readonly=True)
    #cmu_employeur = fields.Integer(store=True, readonly=True, string='CMU employeur')
    enfants_ids = fields.One2many('hr.employee.enfant', 'employee_id', 'Enfants', required=False)
    licence_ids = fields.One2many('hr.licence', 'employee_id', 'Licences des employés')
    diplome_ids = fields.One2many('hr.diplomes.employee', 'employee_id', 'Diplôme des employés')
    visa_ids = fields.One2many('hr.visa', 'employee_id', 'Visas des employés')
    carte_sejour_ids = fields.One2many('hr.carte.sejour', 'employee_id', 'Carte de séjour des employés')
    #children = fields.Integer("Nombre d'enfant", compute="_compute_children")
    children = fields.Integer("Nombre d'enfant")
    date_entree = fields.Date("Date d'entrée")
    presonnes_contacted_ids = fields.One2many('hr.personne.contacted', 'employee_id', 'Personnes à contacter')
    parent_employee_ids = fields.One2many("hr.parent.employe", 'employee_id', 'Les parents')
    recruitment_degree_id = fields.Many2one('hr.employee.degree', "Niveau d'étude")
    # direction_generale_id = fields.Many2one('hr.department', 'Direction Générale', required=False, domain="[('type', '=', 'dg')]")
    # direction_id = fields.Many2one('hr.department', 'Direction', required=False,
    #                                domain="[('type', '=', 'direction'),('parent_id', '=', direction_generale_id)]")
    # department_id = fields.Many2one('hr.department', 'Departement', required=False,
    #                                 domain="[('type', '=', 'department'),('parent_id', '=', direction_id)]")
    # service_id = fields.Many2one('hr.department', 'Service', required=False,
    #                              domain="[('type', '=', 'service'),('parent_id', '=', department_id)]")
    # cellule_id = fields.Many2one('hr.department', 'Cellule', required=False,
    #                              domain="[('type', '=', 'cellule'),('parent_id', '=', service_id)]")
    conjoint_complete_name = fields.Char(string="Nom complet du conjoint(e)", groups="hr.group_hr_user")
    conjoint_birthdate = fields.Date(string="Date de naissance du conjoint", groups="hr.group_hr_user")
    nature_employe = fields.Selection([('local', 'Local'), ('expat', 'Expatrié')], "Nature de l'employé",
                                      default=False)
    num_cmu_conjoint = fields.Char('N° CMU conjoint', required=False)
    mode_paiement = fields.Selection([
        ('cheque', 'Chèque'),
        ('espece', 'Espèce'),
        ('virement', 'Virement'),
    ], 'Moyens de paiement')
    #num_compte_bancaire = fields.Char("numéro de compte bancaire")
    banque_id = fields.Many2one("res.bank","Banque")
    code_banque = fields.Char("Code Banque")
    code_guichet = fields.Char("Code guichet")
    num_compte_bancaire = fields.Char("Compte")
    cle_rib = fields.Char("Clé RIB")
    num_secu_sociale = fields.Char("N° CMU")
    piece_identite_id = fields.Many2one("hr.identity_card", "Pièce d'identité")
    num_piece = fields.Char("Numéro de la pièce",
                            help="Renseignez le numéro de la pièce que vous avez sélectionné plus haut")


nature_identity_card = [('attestion', "Attestation d'indentité"), ("carte_sejour", "Carte de séjour"),
                                     ("cni", "CNI"), ("passeport", "Passeport")]


class IdentityCard(models.Model):
    _name = "hr.identity_card"
    _description = "Pièce d'identité"

    name = fields.Char("Numéro de la pièce", size=128, help="Numéro de la pièce d'identité")
    nature_piece = fields.Selection(nature_identity_card, string="Nature")
    date_etablissement = fields.Date("Date d'établissement")
    autorite = fields.Char("Autorité", size=128, help="L'autorité qui a délivrée la pièce d'identité")
