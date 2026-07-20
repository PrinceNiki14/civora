# -*- coding:utf-8 -*-

from odoo import models, api


class PayslipDetailsReport(models.AbstractModel):
    _name = 'report.hr_payroll_ci.report_payslipdetails'
    _description = 'Payslip Details Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        payslips = self.env['hr.payslip'].browse(docids)
        
        return {
            'doc_ids': docids,
            'doc_model': 'hr.payslip',
            'docs': payslips,
            'data': data,
            'get_details_by_rule_category': self._get_details_by_rule_category,
            'get_lines_by_contribution_register': self._get_lines_by_contribution_register,
        }

    def _get_details_by_rule_category(self, payslip_lines):
        """Group payslip lines by rule category with hierarchy"""
        
        def get_recursive_parent(rule_categories):
            """Get all parent categories recursively"""
            if not rule_categories:
                return []
            if rule_categories[0].parent_id:
                rule_categories.insert(0, rule_categories[0].parent_id)
                get_recursive_parent(rule_categories)
            return rule_categories

        res = []
        result = {}
        ids = [line.id for line in payslip_lines]
        
        if ids:
            self.env.cr.execute('''
                SELECT pl.id, pl.category_id 
                FROM hr_payslip_line AS pl
                LEFT JOIN hr_salary_rule_category AS rc ON (pl.category_id = rc.id)
                WHERE pl.id IN %s
                GROUP BY rc.parent_id, pl.sequence, pl.id, pl.category_id
                ORDER BY pl.sequence, rc.parent_id
            ''', (tuple(ids),))
            
            for x in self.env.cr.fetchall():
                result.setdefault(x[1], [])
                result[x[1]].append(x[0])
            
            for key, value in result.items():
                if key:
                    rule_categories = self.env['hr.salary.rule.category'].browse([key])
                    parents = get_recursive_parent(rule_categories)
                    
                    lines = self.env['hr.payslip.line'].browse(value)
                    category_total = sum(line.total for line in lines)
                    
                    level = 0
                    for parent in parents:
                        res.append({
                            'rule_category': parent.name,
                            'name': parent.name,
                            'code': parent.code,
                            'level': level,
                            'total': category_total,
                        })
                        level += 1
                    
                    for line in lines:
                        res.append({
                            'rule_category': line.name,
                            'name': line.name,
                            'code': line.code,
                            'total': line.total,
                            'level': level
                        })
        
        return res

    def _get_lines_by_contribution_register(self, payslip_lines):
        """Group payslip lines by contribution register"""
        result = {}
        res = []
        
        for line in payslip_lines:
            if line.register_id:
                register_name = line.register_id.name
                result.setdefault(register_name, [])
                result[register_name].append(line.id)
        
        for key, value in result.items():
            lines = self.env['hr.payslip.line'].browse(value)
            register_total = sum(line.total for line in lines)
            
            res.append({
                'register_name': key,
                'total': register_total,
            })
            
            for line in lines:
                res.append({
                    'name': line.name,
                    'code': line.code,
                    'quantity': line.quantity,
                    'amount': line.amount,
                    'total': line.total,
                })
        
        return res
