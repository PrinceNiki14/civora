import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from datetime import date
from odoo import fields, models, api, _


class HrEmployeeDegree(models.Model):
    _name = "hr.employee.degree"
    _description = "Degree of employee"

    name = fields.Char('Name', required=True, translate=True)
    sequence = fields.Integer('Sequence', help="Gives the sequence order when displaying a list of degrees.", default=1)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The name of the Degree of employee must be unique!')
    ]


class Licence(models.Model):
    _name = "hr.licence"
    _description = "Licence employé"

    name = fields.Char('Libellé Licence', required=True, readonly=False)
    reference = fields.Char('Référence', required=False, readonly=False)
    date_debut = fields.Date('Début validité')
    date_fin = fields.Date('Fin validité')
    employee_id = fields.Many2one('hr.employee', 'Employé', required=False)


class Domaine(models.Model):
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
    reference = fields.Char('Référence', required=False, readonly=False)
    date_obtention = fields.Date("Date d'obtention")
    date_start = fields.Date("Date début")
    date_end = fields.Date("Date fin")
    type = fields.Selection([
        ('diplome', 'Diplôme'),
        ('certif', 'Certification')], string="Type")
    image = fields.Binary('Image')
    employee_id = fields.Many2one('hr.employee', 'Employé', required=False)


class Visa(models.Model):
    _name = "hr.visa"
    _description = "visa employé"

    name = fields.Char('Libellé visa', required=True, readonly=False)
    reference = fields.Char('N° Visa', required=True, readonly=False)
    pays_id = fields.Many2one('res.country', 'Pays', required=True)
    date_debut = fields.Datetime('Début validité')
    date_fin = fields.Datetime('Fin validité')
    employee_id = fields.Many2one('hr.employee', 'Employé', required=False)


class CarteSejour(models.Model):
    _name = "hr.carte.sejour"
    _description = "Carte de séjour employé"

    name = fields.Char('Libellé visa', required=False, readonly=False)
    reference = fields.Char('N° Visa', required=False, readonly=False)
    pays_id = fields.Many2one('res.country', 'Pays', required=False)
    date_debut = fields.Datetime('Début validité')
    date_fin = fields.Datetime('Fin validité')
    employee_id = fields.Many2one('hr.employee', 'Employé', required=False)


class EnfantsEmploye(models.Model):
    _name = "hr.employee.enfant"
    _description = "Enfants de l'employé"

    @api.depends('date_naissance')
    def _get_age_child(self):
        this_date = fields.Datetime.now()
        for child in self:
            if child.date_naissance:
                date_naissance = fields.Datetime.from_string(child.date_naissance)
                tmp = relativedelta(this_date, date_naissance)
                child.age = tmp.years
            else:
                child.age = 0

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
    state = fields.Selection([
        ('grand_parent', 'Grand père/Grande mère'),
        ('parent', 'Père / Mère'),
        ('conjoint', 'Conjoint(e)'),
        ('enfant', 'Enfant'),
        ('frere', 'Frère / Soeur'),
        ('voisin', 'Voisin'),
        ('oncle', 'Oncle/Tante'),
        ('cousin', 'Cousin / Cousine'),
        ('other', 'Autres')
    ], 'Type de lien', readonly=False)


class HrPersonneContact(models.Model):
    _name = 'hr.personne.contacted'
    _description = 'Personnes a contacter'

    name = fields.Char("Name", required=True)
    email = fields.Char("Email")
    portable = fields.Char('Portable', required=True)
    state = fields.Selection([
        ('grand_parent', 'Grand père/Grande mère'),
        ('parent', 'Père / Mère'),
        ('conjoint', 'Conjoint(e)'),
        ('enfant', 'Enfant'),
        ('frere', 'Frère / Soeur'),
        ('voisin', 'Voisin'),
        ('oncle', 'Oncle/Tante'),
        ('cousin', 'Cousin / Cousine'),
        ('other', 'Autres')
    ], 'Type de lien', readonly=False)
    Lien = fields.Char("Le lien")
    employee_id = fields.Many2one("hr.employee", 'Employé')


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.depends("children", "enfants_a_charge")
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

    def _compute_children(self):
        for emp in self:
            if emp.enfants_ids:
                number_cmu = 1
                for enfant in emp.enfants_ids:
                    date_ref = datetime.now().strftime('%Y-%m-%d')
                    date_naiss = enfant.date_naissance
                    if date_naiss:
                        temp1 = datetime.strptime(date_ref, '%Y-%m-%d')
                        temp2 = datetime.strptime(str(date_naiss), '%Y-%m-%d')
                        age = abs(relativedelta(temp2, temp1).years)
                        if 0 < age <= 21:
                            number_cmu += 1
                cmu = 1000 * number_cmu
                cmu_employe = (cmu * 50) / 100
                cmu_employeur = (cmu * 50) / 100
                emp.cmu_employe = cmu_employe
                emp.cmu_employeur = cmu_employeur
            else:
                cmu = 1000
                cmu_employe = (cmu * 50) / 100
                cmu_employeur = (cmu * 50) / 100
                emp.cmu_employe = cmu_employe
                emp.cmu_employeur = cmu_employeur

            total_children = 0
            if emp.enfants_ids:
                total_children = len(emp.enfants_ids)
            
            children_in_charge = 0
            for child in emp.enfants_ids:
                if child.age <= emp.company_id.max_age_child:
                    children_in_charge += 1

    @api.depends('birthday')
    def _get_age_employee(self):
        this_date = fields.Datetime.now()
        for emp in self:
            if emp.birthday:
                date_naissance = fields.Datetime.from_string(emp.birthday)
                tmp = relativedelta(this_date, date_naissance)
                emp.age = tmp.years
            else:
                emp.age = 0

    @api.depends('start_date', 'end_date')
    def _get_seniority(self):
        today = fields.Datetime.now()
        for emp in self:
            if emp.start_date:
                start_date = fields.Datetime.from_string(emp.start_date)
                if emp.end_date:
                    end_date = fields.Datetime.from_string(emp.end_date)
                    this_date = min(today, end_date)
                else:
                    this_date = today
                tmp = relativedelta(this_date, start_date)
                emp.seniority_employee = tmp.years
            else:
                emp.seniority_employee = 0

    def name_get(self):
        result = []
        for emp in self:
            if emp.first_name:
                name = emp.name + ' ' + emp.first_name
            else:
                name = emp.name
            result.append((emp.id, name))
        return result

    first_name = fields.Char("Prénoms", required=False)
    category_id = fields.Many2one('hr.contract.category', 'Catégorie', required=False)
    type = fields.Selection([
        ('h', 'Horaire'),
        ('j', 'Journalier'),
        ('m', 'Mensuel')
    ], 'Type', required=False, default=False)
    matricule_cnps = fields.Char('N° CNPS', size=64)
    enfants_a_charge = fields.Integer("Nombre d'enfants à charge", default=0)
    part_igr = fields.Float(compute='_get_part_igr', string='Part IGR', store=True)
    start_date = fields.Date("Date d'ancienneté")
    seniority_employee = fields.Integer("Ancienneté", compute="_get_seniority", store=True)
    end_date = fields.Date("Date de depart", required=False)
    age = fields.Integer('Âge employé', compute='_get_age_employee', store=True)
    total_children = fields.Integer('Nombre enfant total')
    cmu_employe = fields.Integer(string='CMU employé', store=True, readonly=True)
    cmu_employeur = fields.Integer(store=True, readonly=True, string='CMU employeur')
    enfants_ids = fields.One2many('hr.employee.enfant', 'employee_id', 'Enfants', required=False)
    licence_ids = fields.One2many('hr.licence', 'employee_id', 'Licences des employés')
    diplome_ids = fields.One2many('hr.diplomes.employee', 'employee_id', 'Diplôme des employés')
    visa_ids = fields.One2many('hr.visa', 'employee_id', 'Visas des employés')
    carte_sejour_ids = fields.One2many('hr.carte.sejour', 'employee_id', 'Carte de séjour des employés')
    children = fields.Integer("Nombre d'enfant")
    date_entree = fields.Date("Date d'entrée")
    presonnes_contacted_ids = fields.One2many('hr.personne.contacted', 'employee_id', 'Personnes à contacter')
    parent_employee_ids = fields.One2many("hr.parent.employe", 'employee_id', 'Les parents')
    recruitment_degree_id = fields.Many2one('hr.employee.degree', "Niveau d'étude")
    direction_id = fields.Many2one('hr.department', 'Direction', required=False, domain="[('type', '=', 'direction')]")
    department_id = fields.Many2one('hr.department', 'Departement', required=False, domain="[('type', '=', 'department')]")
    service_id = fields.Many2one('hr.department', 'Service', required=False, domain="[('type', '=', 'service')]")
    conjoint_complete_name = fields.Char(string="Nom complet du conjoint(e)", groups="hr.group_hr_user")
    conjoint_birthdate = fields.Date(string="Date de naissance du conjoint", groups="hr.group_hr_user")
    nature_employe = fields.Selection([
        ('local', 'Local'),
        ('expat', 'Expatrié')
    ], "Nature de l'employé", default=False)
    num_cmu_conjoint = fields.Char('N° CMU conjoint', required=False)
    mode_paiement = fields.Selection([
        ('cheque', 'Chèque'),
        ('espece', 'Espèce'),
        ('virement', 'Virement'),
    ], 'Moyens de paiement')
    num_compte_bancaire = fields.Char("numéro de compte bancaire")
    num_secu_sociale = fields.Char("numéro de Sécurité Sociale")
