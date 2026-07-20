# -*- coding: utf-8 -*-

{
    'name': "Send Password Protected Payslips via mail.",
    'summary': """Send password protected Payslips to the employees via mail.""",
    'description': """
        Send password protected payslips to the employees via mail
        Secure odoo
        Secure Payslips
        Send payslip by mail
        Mail Payslip
        Employ
        Send Payslipee Payslip
        Password Protection
        Send Payslip
    """,
    'author': "Jean-Jonathan ARRA",
    'website': "http://www.jjarraodoo.com",
    'category': 'Human Resources',
    'version': '1.0',
    'depends': ['base', 'hr_payroll'],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_template.xml',
        'views/mail_payslip.xml',
        "views/res_company_view.xml",
        "views/hr_employee_view.xml",
        "wizards/mail_password_notification.xml",
    ],
    'images': [
        'static/description/mail_payslip_cover_odoo_by_turkesh_patel.jpg',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}