# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase


class TestHrPayslipCustom(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env['hr.employee'].create({
            'name': 'John Doe',
        })
        cls.contract = cls.env['hr.contract'].create({
            'name': 'Contract John Doe',
            'employee_id': cls.employee.id,
            'wage': 5000,
            'state': 'open',
            'date_start': '2024-01-01',
        })

    def test_payslip_creation(self):
        payslip = self.env['hr.payslip'].create({
            'employee_id': self.employee.id,
            'date_from': '2024-01-01',
            'date_to': '2024-01-31',
            'contract_id': self.contract.id,
        })
        self.assertTrue(payslip.id, "Payslip should be created")
        self.assertEqual(payslip.employee_id.name, 'John Doe', "Employee name should match")

    def test_payslip_computation(self):
        payslip = self.env['hr.payslip'].create({
            'employee_id': self.employee.id,
            'date_from': '2024-01-01',
            'date_to': '2024-01-31',
            'contract_id': self.contract.id,
        })
        payslip.compute_sheet()
        self.assertTrue(payslip.line_ids, "Payslip should have computed lines")
