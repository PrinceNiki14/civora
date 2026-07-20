# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime
from dateutil.relativedelta import relativedelta


class HrTypePiece(models.Model):
    _name = "hr.type.piece"
    _description = "Type de pièce d'identité"

    name = fields.Char("Désignation", required=True)
    description = fields.Text("Description")


class HrPieceIdentity(models.Model):
    _name = "hr.piece.identite"
    _rec_name = "numero_piece"
    _description = "Pièce d'identité"

    numero_piece = fields.Char("Numéro de la pièce", required=True)
    nature_piece = fields.Selection([('attestion', "Attestation d'indentité"), ("carte_sejour", "Carte de séjour"),
                                     ("cni", "CNI"), ("passeport", "Passeport")], string="Nature", required=True)
    date_etablissement = fields.Date("Date d'établissement", required=True)
    autorite = fields.Char("Autorité", size=128)


class HrContract(models.Model):
    _inherit = 'hr.contract'
    _description = 'Employee Contract'

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.job_id = self.employee_id.job_id
            self.department_id = self.employee_id.department_id
            self.date_start = self.employee_id.start_date

    def calcul_anciennete_actuel(self):
        anciennete = {}
        self.ensure_one()
        this_date = today = datetime.today()
        start_date = fields.Datetime.from_string(self.employee_id.start_date)
        if self.date_end:
            end_date = fields.Datetime.from_string(self.date_end)
            this_date = min(today, end_date)
        tmp = relativedelta(this_date, start_date) + relativedelta(months=+self.mois_report, years=+self.an_report)
        anciennete = {
            'year_old': tmp.years,
            'month_old': tmp.months,
        }
        return anciennete

    @api.depends('employee_id', 'date_start', 'date_end', 'an_report', 'mois_report')
    def _compute_anciennete(self):
        for ct in self:
            anciennete = ct.calcul_anciennete_actuel()
            if anciennete:
                ct.an_anciennete = anciennete['year_old']
                ct.mois_anciennete = anciennete['month_old']

    name = fields.Char('Nature du contrat', required=True)
    expatried = fields.Boolean('Expatrié', default=False)
    an_report = fields.Integer('Année')
    mois_report = fields.Integer('Mois report')
    an_anciennete = fields.Integer("Nombre d'année", compute='_compute_anciennete', store=True)
    mois_anciennete = fields.Integer('Nombre de mois', compute='_compute_anciennete', store=True)
    anne_anc = fields.Integer('Année')
    sursalaire = fields.Integer('Sursalaire', required=False)
    hr_convention_id = fields.Many2one('hr.convention', "Convention", required=False)
    hr_secteur_id = fields.Many2one('hr.secteur.activite', "Secteur d'activité", required=False)
    categorie_salariale_id = fields.Many2one('hr.categorie.salariale', 'Catégorie salariale', required=False)
    hr_payroll_prime_ids = fields.One2many("hr.payroll.prime.montant", 'contract_id', "Primes")
    type_ended = fields.Selection([('licenced', 'Licencement'), ('hard_licenced', 'Licencement faute grave'),
                                   ('ended', 'Fin de contract'), ], 'Type de clôture')
    description_cloture = fields.Text("Motif de Clôture")
    wage = fields.Monetary('Salaire de base', required=True, compute='_compute_wage', store=True, readonly=False)

    @api.depends('categorie_salariale_id')
    def _compute_wage(self):
        for record in self:
            if record.categorie_salariale_id:
                record.wage = record.categorie_salariale_id.salaire_base

    def validate_contract(self):
        for ct in self:
            ct.write({'state': 'open'})

    def closing_contract(self):
        view_id = self.env['ir.model.data']._xmlid_to_res_id('hr_contract_extension.hr_contract_closed_form_view')
        return {
            'name': _("Clôture de contrat"),
            'view_mode': 'form',
            'view_id': view_id,
            'res_model': 'hr.contract.closed',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': self._context,
        }

    def action_cancel(self):
        for ct in self:
            ct.write({'state': 'cancel'})

    @api.onchange("hr_convention_id")
    def on_change_convention_id(self):
        if self.hr_convention_id:
            return {'domain': {'hr_secteur_id': [('hr_convention_id', '=', self.hr_convention_id.id)]}}
        else:
            return {'domain': {'hr_secteur_id': [('hr_convention_id', '=', False)]}}

    @api.onchange("hr_secteur_id")
    def on_change_secteur_id(self):
        if self.hr_secteur_id:
            return {'domain': {'categorie_salariale_id': [('hr_secteur_activite_id', '=', self.hr_secteur_id.id)]}}
        else:
            return {'domain': {'categorie_salariale_id': [('hr_secteur_activite_id', '=', False)]}}

    @api.onchange('categorie_salariale_id')
    def on_change_categorie_salariale_id(self):
        if self.categorie_salariale_id:
            self.wage = self.categorie_salariale_id.salaire_base

    def get_inputs_payslip(self):
        res = []
        if self.employee_id:
            cmu_part = self.employee_id.cmu_part
            cotisation_mugef_ci = self.employee_id.cotisation_mugef_ci
            if cotisation_mugef_ci != 'yes':
                type_line = self.env['hr.payslip.input.type'].search([('code', '=', 'CMU')], limit=1)
                if cmu_part:
                    val = {
                        'input_type_id': type_line.id,
                        'amount': cmu_part,
                        'contract_id': self.id,
                    }
                    res.append(val)
        
        if self.wage:
            type_line = self.env['hr.payslip.input.type'].search([('code', '=', 'WAGE')], limit=1)
            val = {
                'input_type_id': type_line.id,
                'amount': self.wage,
                'contract_id': self.id,
            }
            res.append(val)
        else:
            type_line = self.env['hr.payslip.input.type'].search([('code', '=', 'WAGE')], limit=1)
            val = {
                'input_type_id': type_line.id,
                'amount': 0,
                'contract_id': self.id,
            }
            res.append(val)
        
        if self.sursalaire:
            type_line = self.env['hr.payslip.input.type'].search([('code', '=', 'SURSA')], limit=1)
            val = {
                'input_type_id': type_line.id,
                'amount': self.sursalaire,
                'contract_id': self.id,
            }
            res.append(val)
        else:
            type_line = self.env['hr.payslip.input.type'].search([('code', '=', 'SURSA')], limit=1)
            val = {
                'input_type_id': type_line.id,
                'amount': 0,
                'contract_id': self.id,
            }
            res.append(val)
        
        if self.hr_payroll_prime_ids:
            for prime in self.hr_payroll_prime_ids:
                if self.env.company.id in (2, 7, 8):
                    if prime.code != "TRSP":
                        type_line = self.env['hr.payslip.input.type'].search([('code', '=', prime.code)], limit=1)
                        if type_line:
                            val = {
                                'input_type_id': type_line.id,
                                'amount': prime.montant_prime,
                                'contract_id': self.id,
                            }
                            res.append(val)
                    if prime.code == "TRSP":
                        type_line = self.env['hr.payslip.input.type'].search([('code', '=', prime.code)], limit=1)
                        val = {
                            'input_type_id': type_line.id,
                            'amount': prime.montant_prime,
                            'contract_id': self.id,
                        }
                        res.append(val)
                elif self.env.company.id == 5:
                    if prime.code != "TRSP":
                        type_line = self.env['hr.payslip.input.type'].search([('code', '=', prime.code)], limit=1)
                        if type_line:
                            val = {
                                'input_type_id': type_line.id,
                                'amount': prime.montant_prime,
                                'contract_id': self.id,
                            }
                            res.append(val)
                    if prime.code == "TRSP":
                        if prime.montant_prime <= 25000:
                            type_line = self.env['hr.payslip.input.type'].search([('code', '=', prime.code)], limit=1)
                            val = {
                                'input_type_id': type_line.id,
                                'amount': prime.montant_prime,
                                'contract_id': self.id,
                            }
                            res.append(val)
                        if prime.montant_prime > 25000:
                            type_line1 = self.env['hr.payslip.input.type'].search([('code', '=', prime.code)], limit=1)
                            val1 = {
                                'input_type_id': type_line1.id,
                                'amount': 25000,
                                'contract_id': self.id,
                            }
                            type_line = self.env['hr.payslip.input.type'].search([('code', '=', 'TRSP_IMP')], limit=1)
                            val = {
                                'input_type_id': type_line.id,
                                'amount': prime.montant_prime - 25000,
                                'contract_id': self.id,
                            }
                            res.append(val1)
                            res.append(val)
                else:
                    if prime.code != "TRSP":
                        type_line = self.env['hr.payslip.input.type'].search([('code', '=', prime.code)], limit=1)
                        if type_line:
                            val = {
                                'input_type_id': type_line.id,
                                'amount': prime.montant_prime,
                                'contract_id': self.id,
                            }
                            res.append(val)
                    if prime.code == "TRSP":
                        if prime.montant_prime <= 30000:
                            type_line = self.env['hr.payslip.input.type'].search([('code', '=', prime.code)], limit=1)
                            val = {
                                'input_type_id': type_line.id,
                                'amount': prime.montant_prime,
                                'contract_id': self.id,
                            }
                            res.append(val)
                        if prime.montant_prime > 30000:
                            type_line1 = self.env['hr.payslip.input.type'].search([('code', '=', prime.code)], limit=1)
                            val1 = {
                                'input_type_id': type_line1.id,
                                'amount': 30000,
                                'contract_id': self.id,
                            }
                            type_line = self.env['hr.payslip.input.type'].search([('code', '=', 'TRSP_IMP')], limit=1)
                            val = {
                                'input_type_id': type_line.id,
                                'amount': prime.montant_prime - 30000,
                                'contract_id': self.id,
                            }
                            res.append(val1)
                            res.append(val)
        return res


class HrPayrollPrime(models.Model):
    _name = "hr.payroll.prime"
    _description = "prime"

    name = fields.Char('name', required=True)
    code = fields.Char('Code', required=True)
    description = fields.Text('Description')
    active = fields.Boolean('Active', default=True, readonly=False)


class HrCategorieSalarialePrime(models.Model):
    _name = "hr.categorie.salariale.prime"
    _description = "Gestion des primes de salaires catégoriels"

    prime_id = fields.Many2one("hr.payroll.prime", "Prime", required=True)
    amount = fields.Float("Montant", required=True)
    categorie_id = fields.Many2one("hr.contract.category", "Catégorie Salariale")


class HrPayrollPrimeMontant(models.Model):
    _name = "hr.payroll.prime.montant"
    _description = "Gestion des primes sur les contrats"

    @api.depends('prime_id')
    def _compute_code_prime(self):
        for ct in self:
            if ct.prime_id:
                ct.code = ct.prime_id.code
            else:
                ct.code = False

    prime_id = fields.Many2one('hr.payroll.prime', 'prime', required=True)
    code = fields.Char("Code", compute='_compute_code_prime', store=True)
    contract_id = fields.Many2one('hr.contract', 'Contract')
    montant_prime = fields.Integer('Montant', required=True)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    cni_number = fields.Char("N° carte d'identité", required=False)


class HrConvention(models.Model):
    _name = "hr.convention"
    _description = "Convention"

    name = fields.Char("Name", required=True)
    description = fields.Text("Description")
    secteurs_ids = fields.One2many("hr.secteur.activite", "hr_convention_id", "Secteurs d'activités")


class HrSecteurActivity(models.Model):
    _name = "hr.secteur.activite"
    _description = "Secteur d'activite"

    name = fields.Char("Nom", required=True)
    description = fields.Text("Description")
    hr_convention_id = fields.Many2one("hr.convention", "Convention", required=True)
    salaire_ids = fields.One2many("hr.categorie.salariale", "hr_secteur_activite_id", "Catégories salariales")
    category_employee_ids = fields.One2many("hr.contract.category", "hr_secteur_activite_id", "Catégorie d'employés")


class HrContractCategory(models.Model):
    _inherit = "hr.contract.category"

    prime_ids = fields.One2many("hr.categorie.salariale.prime", 'categorie_id', "Primes")
    categorie_salariale_ids = fields.One2many("hr.categorie.salariale", "categorie_employee_id", "Salaires catégoriels")
    hr_secteur_activite_id = fields.Many2one('hr.secteur.activite', "Secteur d'activité", required=True)


class HrCategorieSalariale(models.Model):
    _name = "hr.categorie.salariale"
    _description = "Categorie salariale"

    name = fields.Char('Libellé', required=False)
    salaire_base = fields.Integer("Salaire de base")
    description = fields.Text('Description')
    hr_secteur_activite_id = fields.Many2one('hr.secteur.activite', "Secteur d'activité")
    categorie_employee_id = fields.Many2one("hr.contract.category", "Catégorie de l'employé")
    active = fields.Boolean('Active', default=True, readonly=False)
